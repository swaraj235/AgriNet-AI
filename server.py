"""
AgriNet AI — Flask Backend Server
REST API with JWT auth, rate limiting, security headers, and ML proxy.
"""

import os
import re
import time
import json
import secrets
import functools
from collections import defaultdict

try:
    import urllib.request as urllib_request
    import urllib.error as urllib_error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

from flask import Flask, request, jsonify, send_from_directory, send_file
import jwt

from database import init_db, create_user, authenticate_user, get_user_by_id, \
    log_crop_query, log_transport_pool, get_user_history

# ML Service URL (FastAPI on port 8000)
ML_SERVICE_URL = os.environ.get('ML_SERVICE_URL', 'http://localhost:8000')

# ===== App Config =====
app = Flask(__name__, static_folder='.', static_url_path='')

SECRET_KEY = os.environ.get('AGRINET_SECRET', secrets.token_hex(32))
JWT_EXPIRY = 86400  # 24 hours

# ===== Rate Limiter (in-memory) =====
rate_limits = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = {
    'login': 5,
    'signup': 3,
    'api': 30
}


def check_rate_limit(category, identifier):
    """Returns True if rate limit exceeded."""
    now = time.time()
    key = f"{category}:{identifier}"
    # Clean old entries
    rate_limits[key] = [t for t in rate_limits[key] if now - t < RATE_LIMIT_WINDOW]
    max_requests = RATE_LIMIT_MAX.get(category, 30)
    if len(rate_limits[key]) >= max_requests:
        return True
    rate_limits[key].append(now)
    return False


# ===== Security Middleware =====
@app.after_request
def add_security_headers(response):
    # CORS — allow mobile app and ML service requests
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response


@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        resp = app.make_default_options_response()
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return resp


# ===== Input Validation =====
def sanitize(text, max_len=200):
    """Sanitize user input — strip, limit length, remove control chars."""
    if not isinstance(text, str):
        return ''
    text = text.strip()[:max_len]
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def validate_email(email):
    """Basic email format validation."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password(password):
    """Password must be at least 6 characters."""
    return isinstance(password, str) and len(password) >= 6


# ===== JWT Helpers =====
def create_token(user):
    """Create a JWT for the given user dict."""
    payload = {
        'user_id': user['id'],
        'name': user['name'],
        'email': user['email'],
        'exp': time.time() + JWT_EXPIRY,
        'iat': time.time()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')


def require_auth(f):
    """Decorator to require a valid JWT on an endpoint."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization required'}), 401

        token = auth_header[7:]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'],
                                 options={'require': ['exp', 'user_id']})
            # Check expiry manually (PyJWT checks it, but be explicit)
            if payload.get('exp', 0) < time.time():
                return jsonify({'error': 'Token expired'}), 401
            request.user_id = payload['user_id']
            request.user_name = payload.get('name', '')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return wrapper


# ===== Static File Serving =====
@app.route('/')
def serve_index():
    return send_file('login.html')


@app.route('/app')
def serve_app():
    return send_file('index.html')


@app.route('/login.html')
def serve_login():
    return send_file('login.html')


@app.route('/index.html')
def serve_main():
    return send_file('index.html')


@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('css', path)


@app.route('/js/<path:path>')
def serve_js(path):
    return send_from_directory('js', path)


@app.route('/api/translations.js')
def serve_translations_js():
    return send_file('api/translations.js')


@app.route('/api/processor.js')
def serve_processor_js():
    return send_file('api/processor.js')


# ===== AUTH API =====

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    ip = request.remote_addr
    if check_rate_limit('signup', ip):
        return jsonify({'error': 'Too many attempts. Try again later.'}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    name = sanitize(data.get('name', ''), 100)
    email = sanitize(data.get('email', ''), 150)
    password = data.get('password', '')
    phone = sanitize(data.get('phone', ''), 15)
    language = sanitize(data.get('language', 'en'), 5)

    # Validation
    errors = []
    if not name or len(name) < 2:
        errors.append('Name must be at least 2 characters.')
    if not validate_email(email):
        errors.append('Enter a valid email address.')
    if not validate_password(password):
        errors.append('Password must be at least 6 characters.')

    if errors:
        return jsonify({'error': ' '.join(errors)}), 400

    user = create_user(name, email, password, phone, language)
    if user is None:
        return jsonify({'error': 'An account with this email already exists.'}), 409

    token = create_token(user)
    return jsonify({
        'token': token,
        'user': user
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    ip = request.remote_addr
    if check_rate_limit('login', ip):
        return jsonify({'error': 'Too many login attempts. Wait 60 seconds.'}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400

    email = sanitize(data.get('email', ''), 150)
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = authenticate_user(email, password)
    if user is None:
        return jsonify({'error': 'Invalid email or password.'}), 401

    token = create_token(user)
    return jsonify({
        'token': token,
        'user': user
    })


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_me():
    user = get_user_by_id(request.user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user})


# ===== TRANSLATIONS API =====

TRANSLATIONS = {}

def load_translations():
    """Load translations from the JS file as a Python dict."""
    global TRANSLATIONS
    # We parse the JS object directly
    TRANSLATIONS = {
        "en": {
            "app_title": "AgriNet AI",
            "app_tagline": "Smart crop & supply network",
            "nav_dashboard": "Dashboard",
            "nav_crop": "Crop AI",
            "nav_transport": "Transport Pool",
            "nav_spoilage": "Spoilage AI",
            "nav_blockchain": "Blockchain",
            "nav_voice": "Voice AI",
            "demand_signal": "Demand signal — Pune",
            "farmers_connected": "Farmers connected",
            "profit_increase": "Avg profit increase",
            "spoilage_prevented": "Spoilage prevented",
            "forecast": "Live demand forecast — next 30 days",
            "forecast_sub": "Sources: mandi price API · weather API · Diwali festival demand model",
            "supply_map": "Supply balance map — Maharashtra",
            "supply_sub": "AI distributes crops across villages to prevent overproduction",
            "crop_ai_title": "Crop recommendation AI",
            "farmer_profile": "Farmer profile",
            "soil_type": "Soil type",
            "water_avail": "Water availability",
            "land_acres": "Land (acres)",
            "run_ai_btn": "Run AI recommendation",
            "validation_error": "Please select all parameters before running the AI.",
            "pool_title": "Farmers in your pool area",
            "pool_sub": "Click farmers to add to transport pool",
            "calc_pool_btn": "Calculate shared transport",
            "pool_error": "Please select at least one farmer to form a pool.",
            "spoilage_title": "Spoilage risk prediction",
            "spoilage_sub": "Current shipments en route — AI monitors temperature & humidity",
            "spoilage_intervention": "AI intervention — brinjal shipment",
            "spoilage_alert_title": "High spoilage risk detected",
            "spoilage_suggestions": "AI suggestions",
            "spoilage_s1_title": "Reroute to Pimpri-Chinchwad mandi",
            "spoilage_s2_title": "Alert nearby buyer: Raj Wholesale",
            "spoilage_s3_title": "Cold storage option nearby",
            "bc_trace": "Supply chain — blockchain trace",
            "bc_shipment": "Shipment #TN-2024-8821 · Tomato · Nashik → Pune",
            "bc_fraud": "Fraud prevention alerts",
            "voice_title": "Voice AI — rural farmer interface",
            "voice_sub": "Farmer asks in Hindi/Marathi — AI responds in local language",
            "impact_title": "Impact — before vs after AgriNet",
            "chat_placeholder": "Type your question in any language…",
            "login_title": "Welcome to AgriNet AI",
            "login_subtitle": "Smart farming intelligence for Indian farmers",
            "login_tab": "Login",
            "signup_tab": "Create Account",
            "email_label": "Email address",
            "password_label": "Password",
            "name_label": "Full name",
            "phone_label": "Phone (optional)",
            "login_btn": "Sign In",
            "signup_btn": "Create Account",
            "logout": "Logout",
            "welcome_back": "Welcome back"
        },
        "hi": {
            "app_title": "एग्रीनेट एआई",
            "app_tagline": "स्मार्ट फसल और आपूर्ति नेटवर्क",
            "nav_dashboard": "डैशबोर्ड",
            "nav_crop": "फसल एआई",
            "nav_transport": "परिवहन पूल",
            "nav_spoilage": "खराबी एआई",
            "nav_blockchain": "ब्लॉकचेन",
            "nav_voice": "आवाज़ एआई",
            "demand_signal": "मांग संकेत — पुणे",
            "farmers_connected": "जुड़े हुए किसान",
            "profit_increase": "औसत लाभ वृद्धि",
            "spoilage_prevented": "खराबी रोकी गई",
            "forecast": "लाइव मांग पूर्वानुमान — अगले 30 दिन",
            "forecast_sub": "स्रोत: मंडी मूल्य एपीआई · मौसम एपीआई · दिवाली त्योहार मांग मॉडल",
            "supply_map": "आपूर्ति संतुलन मानचित्र — महाराष्ट्र",
            "supply_sub": "अतिउत्पादन को रोकने के लिए एआई गांवों में फसलों का वितरण करता है",
            "crop_ai_title": "फसल सिफारिश एआई",
            "farmer_profile": "किसान प्रोफ़ाइल",
            "soil_type": "मिट्टी का प्रकार",
            "water_avail": "पानी की उपलब्धता",
            "land_acres": "जमीन (एकड़)",
            "run_ai_btn": "एआई सिफारिश चलाएं",
            "validation_error": "एआई चलाने से पहले कृपया सभी पैरामीटर चुनें।",
            "pool_title": "आपके पूल क्षेत्र में किसान",
            "pool_sub": "परिवहन पूल में जोड़ने के लिए किसानों पर क्लिक करें",
            "calc_pool_btn": "साझा परिवहन की गणना करें",
            "pool_error": "कृपया कम से कम एक किसान चुनें।",
            "spoilage_title": "खराबी जोखिम भविष्यवाणी",
            "spoilage_sub": "रास्ते में वर्तमान शिपमेंट — एआई तापमान और आर्द्रता की निगरानी करता है",
            "spoilage_intervention": "एआई हस्तक्षेप — बैंगन शिपमेंट",
            "spoilage_alert_title": "उच्च खराबी जोखिम का पता चला",
            "spoilage_suggestions": "एआई सुझाव",
            "spoilage_s1_title": "पिंपरी-चिंचवाड मंडी में रीरूट करें",
            "spoilage_s2_title": "पास के खरीदार को सूचित करें: राज होलसेल",
            "spoilage_s3_title": "पास में कोल्ड स्टोरेज उपलब्ध",
            "bc_trace": "आपूर्ति श्रृंखला — ब्लॉकचेन ट्रेस",
            "bc_shipment": "शिपमेंट #TN-2024-8821 · टमाटर · नासिक → पुणे",
            "bc_fraud": "धोखाधड़ी रोकथाम अलर्ट",
            "voice_title": "आवाज़ एआई — ग्रामीण किसान इंटरफ़ेस",
            "voice_sub": "किसान हिंदी/मराठी में पूछता है — एआई स्थानीय भाषा में जवाब देता है",
            "impact_title": "प्रभाव — एग्रीनेट से पहले बनाम बाद में",
            "chat_placeholder": "किसी भी भाषा में अपना सवाल लिखें…",
            "login_title": "एग्रीनेट एआई में आपका स्वागत है",
            "login_subtitle": "भारतीय किसानों के लिए स्मार्ट खेती बुद्धिमत्ता",
            "login_tab": "लॉगिन",
            "signup_tab": "खाता बनाएं",
            "email_label": "ईमेल पता",
            "password_label": "पासवर्ड",
            "name_label": "पूरा नाम",
            "phone_label": "फोन (वैकल्पिक)",
            "login_btn": "साइन इन करें",
            "signup_btn": "खाता बनाएं",
            "logout": "लॉगआउट",
            "welcome_back": "वापस स्वागत है"
        },
        "mr": {
            "app_title": "अॅग्रीनेट एआय",
            "app_tagline": "स्मार्ट पीक आणि पुरवठा नेटवर्क",
            "nav_dashboard": "डॅशबोर्ड",
            "nav_crop": "पीक एआय",
            "nav_transport": "वाहतूक पूल",
            "nav_spoilage": "नासाडी एआय",
            "nav_blockchain": "ब्लॉकचेन",
            "nav_voice": "आवाज एआय",
            "demand_signal": "मागणी संकेत — पुणे",
            "farmers_connected": "जोडलेले शेतकरी",
            "profit_increase": "सरासरी नफा वाढ",
            "spoilage_prevented": "नासाडी रोखली",
            "forecast": "थेट मागणी अंदाज — पुढील 30 दिवस",
            "forecast_sub": "स्रोत: मंडी भाव एपीआय · हवामान एपीआय · दिवाळी सण मागणी मॉडेल",
            "supply_map": "पुरवठा संतुलन नकाशा — महाराष्ट्र",
            "supply_sub": "अतिरिक्त उत्पादन टाळण्यासाठी एआय गावांमध्ये पिकांचे वितरण करते",
            "crop_ai_title": "पीक शिफारस एआय",
            "farmer_profile": "शेतकरी प्रोफाइल",
            "soil_type": "मातीचा प्रकार",
            "water_avail": "पाण्याची उपलब्धता",
            "land_acres": "जमीन (एकर)",
            "run_ai_btn": "एआय शिफारस चालवा",
            "validation_error": "एआय चालवण्यापूर्वी कृपया सर्व मापदंड निवडा.",
            "pool_title": "तुमच्या पूल क्षेत्रातील शेतकरी",
            "pool_sub": "वाहतूक पूलमध्ये जोडण्यासाठी शेतकऱ्यांवर क्लिक करा",
            "calc_pool_btn": "सामायिक वाहतूक गणना करा",
            "pool_error": "पूल तयार करण्यासाठी कृपया किमान एक शेतकरी निवडा.",
            "spoilage_title": "नासाडी धोका अंदाज",
            "spoilage_sub": "मार्गावरील सध्याच्या शिपमेंट — एआय तापमान आणि आर्द्रतेवर लक्ष ठेवतो",
            "spoilage_intervention": "एआय हस्तक्षेप — वांगी शिपमेंट",
            "spoilage_alert_title": "उच्च नासाडीचा धोका आढळला",
            "spoilage_suggestions": "एआय सूचना",
            "spoilage_s1_title": "पिंपरी-चिंचवड मंडीकडे मार्ग बदला",
            "spoilage_s2_title": "जवळच्या खरेदीदाराला कळवा: राज होलसेल",
            "spoilage_s3_title": "जवळ कोल्ड स्टोरेज उपलब्ध",
            "bc_trace": "पुरवठा साखळी — ब्लॉकचेन ट्रेस",
            "bc_shipment": "शिपमेंट #TN-2024-8821 · टोमॅटो · नाशिक → पुणे",
            "bc_fraud": "फसवणूक प्रतिबंध अलर्ट",
            "voice_title": "आवाज एआय — ग्रामीण शेतकरी इंटरफेस",
            "voice_sub": "शेतकरी हिंदी/मराठीत विचारतो — एआय स्थानिक भाषेत उत्तर देतो",
            "impact_title": "प्रभाव — अॅग्रीनेट आधी विरुद्ध नंतर",
            "chat_placeholder": "कोणत्याही भाषेत तुमचा प्रश्न लिहा…",
            "login_title": "अॅग्रीनेट एआय मध्ये आपले स्वागत आहे",
            "login_subtitle": "भारतीय शेतकऱ्यांसाठी स्मार्ट शेती बुद्धिमत्ता",
            "login_tab": "लॉगिन",
            "signup_tab": "खाते तयार करा",
            "email_label": "ईमेल पत्ता",
            "password_label": "पासवर्ड",
            "name_label": "पूर्ण नाव",
            "phone_label": "फोन (पर्यायी)",
            "login_btn": "साइन इन करा",
            "signup_btn": "खाते तयार करा",
            "logout": "लॉगआउट",
            "welcome_back": "परत स्वागत आहे"
        }
    }


@app.route('/api/translations/<lang>', methods=['GET'])
def get_translations(lang):
    lang = sanitize(lang, 5)
    if lang not in TRANSLATIONS:
        lang = 'en'
    return jsonify(TRANSLATIONS[lang])


# ===== CROP AI API =====

CROP_DB = {
    'black': [
        {'crop': 'Tomato', 'score': 9.6, 'match': 'Excellent', 'profit': '₹61,000', 'reason': 'High demand in Pune · ideal for black cotton soil · festival season boost'},
        {'crop': 'Onion', 'score': 7.2, 'match': 'Good', 'profit': '₹41,000', 'reason': 'Stable prices, moderate competition in region'},
        {'crop': 'Wheat', 'score': 5.5, 'match': 'Average', 'profit': '₹28,000', 'reason': 'Low demand growth, traditional crop'}
    ],
    'red': [
        {'crop': 'Brinjal', 'score': 8.8, 'match': 'Excellent', 'profit': '₹48,000', 'reason': 'Thrives in red laterite · export demand rising'},
        {'crop': 'Potato', 'score': 6.5, 'match': 'Medium', 'profit': '₹31,000', 'reason': 'Average yield expected in this soil type'},
        {'crop': 'Onion', 'score': 5.8, 'match': 'Average', 'profit': '₹35,000', 'reason': 'Adequate yield, competitive market'}
    ],
    'alluvial': [
        {'crop': 'Potato', 'score': 9.1, 'match': 'Excellent', 'profit': '₹52,000', 'reason': 'Best yield in alluvial soil · cold storage nearby'},
        {'crop': 'Wheat', 'score': 7.8, 'match': 'Good', 'profit': '₹35,000', 'reason': 'Consistent local demand, reliable crop'},
        {'crop': 'Onion', 'score': 6.2, 'match': 'Good', 'profit': '₹38,000', 'reason': 'Moderate fit in this soil type'}
    ]
}


@app.route('/api/crop-predict', methods=['POST'])
@require_auth
def crop_predict():
    ip = request.remote_addr
    if check_rate_limit('api', ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    soil = sanitize(data.get('soil', ''), 20)
    water = sanitize(data.get('water', ''), 20)
    land = sanitize(data.get('land', ''), 20)

    if not soil or not water or not land:
        return jsonify({'error': 'All fields are required: soil, water, land'}), 400

    if soil not in CROP_DB:
        return jsonify({'error': 'Invalid soil type'}), 400

    results = [dict(c) for c in CROP_DB[soil]]

    # Adjust for water scarcity
    if water == 'low':
        for c in results:
            c['score'] = round(c['score'] - 1.5, 1)
        results.append({
            'crop': 'Millet (Bajra)',
            'score': 9.5,
            'match': 'Excellent',
            'profit': '₹38,000',
            'reason': 'Highly drought resistant, ideal for rainfed conditions'
        })

    results.sort(key=lambda x: x['score'], reverse=True)

    # Log query
    top = results[0] if results else None
    if top:
        log_crop_query(request.user_id, soil, water, land, top['crop'], top['score'])

    return jsonify({'results': results})


# ===== TRANSPORT POOL API =====

@app.route('/api/pool-calculate', methods=['POST'])
@require_auth
def pool_calculate():
    ip = request.remote_addr
    if check_rate_limit('api', ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    farmer_count = data.get('farmer_count', 0)
    if not isinstance(farmer_count, int) or farmer_count < 1 or farmer_count > 20:
        return jsonify({'error': 'Select between 1 and 20 farmers'}), 400

    base_cost = 4200
    route_overhead = 800
    per_stop_cost = 250
    total_cost = base_cost + route_overhead + (farmer_count * per_stop_cost)
    cost_per_farmer = round(total_cost / (farmer_count + 1))
    savings = base_cost - cost_per_farmer

    log_transport_pool(request.user_id, farmer_count, base_cost, cost_per_farmer, savings)

    return jsonify({
        'base_cost': base_cost,
        'pooled_cost': cost_per_farmer,
        'savings': savings,
        'total_farmers': farmer_count + 1
    })


# ===== USER HISTORY =====

@app.route('/api/history', methods=['GET'])
@require_auth
def history():
    records = get_user_history(request.user_id)
    return jsonify({'history': records})


# ===== ML SERVICE PROXY =====

def _proxy_to_ml(path, method='GET', body=None):
    """Forward a request to the FastAPI ML service and return the JSON response."""
    url = f"{ML_SERVICE_URL}/{path}"
    try:
        if body:
            data = json.dumps(body).encode('utf-8')
            req = urllib_request.Request(url, data=data,
                                         headers={'Content-Type': 'application/json'},
                                         method=method)
        else:
            req = urllib_request.Request(url, method=method)
        with urllib_request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()), resp.status
    except Exception as e:
        return {'error': f'ML service unavailable: {str(e)}'}, 503


@app.route('/api/ml/crop-recommend', methods=['POST'])
@require_auth
def ml_crop_recommend():
    data = request.get_json(silent=True) or {}
    result, status = _proxy_to_ml('api/ml/crop-recommend', 'POST', data)
    return jsonify(result), status


@app.route('/api/ml/demand-forecast', methods=['POST'])
@require_auth
def ml_demand_forecast():
    data = request.get_json(silent=True) or {}
    result, status = _proxy_to_ml('api/ml/demand-forecast', 'POST', data)
    return jsonify(result), status


@app.route('/api/ml/supply-balance', methods=['POST'])
@require_auth
def ml_supply_balance():
    data = request.get_json(silent=True) or {}
    result, status = _proxy_to_ml('api/ml/supply-balance', 'POST', data)
    return jsonify(result), status


@app.route('/api/ml/mandi-prices', methods=['GET'])
def ml_mandi_prices():
    market = request.args.get('market', 'Pune APMC')
    result, status = _proxy_to_ml(f'api/ml/mandi-prices?market={market}')
    return jsonify(result), status


@app.route('/api/ml/spoilage-risk', methods=['POST'])
@require_auth
def ml_spoilage_risk():
    data = request.get_json(silent=True) or {}
    result, status = _proxy_to_ml('api/ml/spoilage-risk', 'POST', data)
    return jsonify(result), status


@app.route('/api/ml/health', methods=['GET'])
def ml_health():
    result, status = _proxy_to_ml('health')
    return jsonify(result), status


# ===== MOBILE APP =====

@app.route('/mobile')
@app.route('/mobile.html')
def serve_mobile():
    return send_file('mobile_app.html')


# ===== Run =====
if __name__ == '__main__':
    init_db()
    load_translations()
    print("\n  🌱 AgriNet AI  → http://localhost:5000")
    print("  📱 Mobile UI   → http://localhost:5000/mobile")
    print("  🤖 ML Service  → run: cd ml_service && python main.py\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
