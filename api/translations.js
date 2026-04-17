// ===== AgriNet AI — Multilingual Translation API =====
// Simulates a REST API endpoint returning translations
// Supports: English (en), Hindi (hi), Marathi (mr)

const translateDB = {
  "en": {
    "app_title": "AgriNet AI",
    "app_tagline": "Smart crop & supply network",
    "nav_dashboard": "Dashboard",
    "nav_crop": "Crop AI",
    "nav_transport": "Transport Pool",
    "nav_spoilage": "Spoilage AI",
    "nav_blockchain": "Blockchain",
    "nav_voice": "Voice AI",

    // Dashboard
    "demand_signal": "Demand signal — Pune",
    "farmers_connected": "Farmers connected",
    "profit_increase": "Avg profit increase",
    "spoilage_prevented": "Spoilage prevented",
    "forecast": "Live demand forecast — next 30 days",
    "forecast_sub": "Sources: mandi price API · weather API · Diwali festival demand model",
    "supply_map": "Supply balance map — Maharashtra",
    "supply_sub": "AI distributes crops across villages to prevent overproduction",

    // Crop AI
    "crop_ai_title": "Crop recommendation AI",
    "farmer_profile": "Farmer profile",
    "soil_type": "Soil type",
    "water_avail": "Water availability",
    "land_acres": "Land (acres)",
    "run_ai_btn": "Run AI recommendation",
    "validation_error": "Please select all parameters before running the AI.",

    // Transport
    "pool_title": "Farmers in your pool area",
    "pool_sub": "Click farmers to add to transport pool",
    "calc_pool_btn": "Calculate shared transport",
    "pool_error": "Please select at least one farmer to form a pool.",

    // Spoilage
    "spoilage_title": "Spoilage risk prediction",
    "spoilage_sub": "Current shipments en route — AI monitors temperature & humidity",
    "spoilage_intervention": "AI intervention — brinjal shipment",
    "spoilage_alert_title": "High spoilage risk detected",
    "spoilage_suggestions": "AI suggestions",
    "spoilage_s1_title": "Reroute to Pimpri-Chinchwad mandi",
    "spoilage_s2_title": "Alert nearby buyer: Raj Wholesale",
    "spoilage_s3_title": "Cold storage option nearby",

    // Blockchain
    "bc_trace": "Supply chain — blockchain trace",
    "bc_shipment": "Shipment #TN-2024-8821 · Tomato · Nashik → Pune",
    "bc_fraud": "Fraud prevention alerts",

    // Voice AI
    "voice_title": "Voice AI — rural farmer interface",
    "voice_sub": "Farmer asks in Hindi/Marathi — AI responds in local language",
    "impact_title": "Impact — before vs after AgriNet",
    "chat_placeholder": "Type your question in any language…"
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
    "chat_placeholder": "किसी भी भाषा में अपना सवाल लिखें…"
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
    "chat_placeholder": "कोणत्याही भाषेत तुमचा प्रश्न लिहा…"
  }
};

window.i18nAPI = function(lang = 'en') {
  return new Promise((resolve) => {
    // Simulate API latency
    setTimeout(() => resolve(translateDB[lang] || translateDB['en']), 100);
  });
};
