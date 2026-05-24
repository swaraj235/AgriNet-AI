-- ================================================================
-- AgriNet AI — Supabase PostgreSQL Schema
-- Project: bkgvvwbukgfijamnkzsp
-- Run this in: Supabase Dashboard → SQL Editor → New query → Run
-- ================================================================

-- ────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for fuzzy text search


-- ────────────────────────────────────────────────────────────────
-- 1. PROFILES
-- Mirrors Supabase auth.users. Created automatically on signup
-- via the trigger below.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL DEFAULT '',
    email       TEXT        UNIQUE NOT NULL,
    phone       TEXT        DEFAULT '',
    language    TEXT        DEFAULT 'en',
    region      TEXT        DEFAULT '',
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    avatar_url  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    last_login  TIMESTAMPTZ
);

-- Auto-create profile row when a new user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.profiles (id, name, email)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
        NEW.email
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- Update last_login on sign-in
CREATE OR REPLACE FUNCTION public.handle_user_login()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE public.profiles SET last_login = NOW() WHERE id = NEW.id;
    RETURN NEW;
END;
$$;


-- ────────────────────────────────────────────────────────────────
-- 2. CROP QUERIES
-- Every time a farmer runs the Crop AI, we log it here.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.crop_queries (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    soil_type       TEXT,
    water_level     TEXT,
    land_size       TEXT,
    temperature     DOUBLE PRECISION,
    humidity        DOUBLE PRECISION,
    ph              DOUBLE PRECISION,
    rainfall        DOUBLE PRECISION,
    result_crop     TEXT,
    result_score    DOUBLE PRECISION,
    all_results     JSONB,      -- full ranked list from ML model
    location        TEXT,
    queried_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crop_queries_user    ON public.crop_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_crop_queries_crop    ON public.crop_queries(result_crop);
CREATE INDEX IF NOT EXISTS idx_crop_queries_time    ON public.crop_queries(queried_at DESC);


-- ────────────────────────────────────────────────────────────────
-- 3. TRANSPORT POOLS
-- Records each pooled transport calculation.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.transport_pools (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_by      UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    farmer_ids      UUID[]      DEFAULT '{}',   -- array of participating farmer IDs
    farmer_count    INTEGER     DEFAULT 0,
    base_cost       NUMERIC(10,2),              -- individual cost (without pooling)
    pooled_cost     NUMERIC(10,2),              -- cost per farmer with pooling
    total_savings   NUMERIC(10,2),
    route           TEXT,
    destination     TEXT,
    status          TEXT        DEFAULT 'pending', -- pending | active | completed
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transport_creator  ON public.transport_pools(created_by);
CREATE INDEX IF NOT EXISTS idx_transport_status   ON public.transport_pools(status);


-- ────────────────────────────────────────────────────────────────
-- 4. SHIPMENTS (Blockchain Traceability)
-- Each farm-to-market shipment with an immutable hash chain.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.shipments (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_ref    TEXT        UNIQUE NOT NULL, -- e.g. TN-2024-8821
    farmer_id       UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
    crop            TEXT        NOT NULL,
    quantity_kg     NUMERIC(10,2),
    grade           TEXT        DEFAULT 'A',
    origin          TEXT,       -- village/district
    destination     TEXT,       -- mandi name
    transport_id    UUID        REFERENCES public.transport_pools(id) ON DELETE SET NULL,
    final_price_kg  NUMERIC(8,2),
    status          TEXT        DEFAULT 'farm_recorded',
    -- status values: farm_recorded | weighed | dispatched | arrived | sold
    fraud_flagged   BOOLEAN     DEFAULT FALSE,
    fraud_reason    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shipments_farmer   ON public.shipments(farmer_id);
CREATE INDEX IF NOT EXISTS idx_shipments_status   ON public.shipments(status);
CREATE INDEX IF NOT EXISTS idx_shipments_ref      ON public.shipments(shipment_ref);


-- ────────────────────────────────────────────────────────────────
-- 5. BLOCKCHAIN EVENTS
-- Append-only log of all supply chain events per shipment.
-- Each row has a hash for tamper detection.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.blockchain_events (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id     UUID        NOT NULL REFERENCES public.shipments(id) ON DELETE CASCADE,
    event_type      TEXT        NOT NULL,   -- farm_recorded | weighed | dispatched | arrived | sold
    event_data      JSONB       DEFAULT '{}',
    prev_hash       TEXT,       -- hash of the previous event (chain)
    event_hash      TEXT        UNIQUE,     -- SHA256 of (shipment_id+event_type+event_data+prev_hash)
    recorded_by     UUID        REFERENCES public.profiles(id) ON DELETE SET NULL,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bc_shipment  ON public.blockchain_events(shipment_id);
CREATE INDEX IF NOT EXISTS idx_bc_time      ON public.blockchain_events(recorded_at DESC);


-- ────────────────────────────────────────────────────────────────
-- 6. SPOILAGE ALERTS
-- AI-detected spoilage risks on active shipments.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.spoilage_alerts (
    id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    shipment_id     UUID        REFERENCES public.shipments(id) ON DELETE CASCADE,
    farmer_id       UUID        REFERENCES public.profiles(id) ON DELETE CASCADE,
    crop            TEXT,
    risk_pct        INTEGER,    -- 0–100 spoilage risk
    risk_level      TEXT,       -- low | medium | high | critical
    temperature_c   NUMERIC(5,2),
    humidity_pct    NUMERIC(5,2),
    transit_hours   NUMERIC(5,1),
    suggestions     JSONB       DEFAULT '[]', -- array of AI suggestion strings
    resolved        BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spoilage_farmer   ON public.spoilage_alerts(farmer_id);
CREATE INDEX IF NOT EXISTS idx_spoilage_risk     ON public.spoilage_alerts(risk_level);
CREATE INDEX IF NOT EXISTS idx_spoilage_resolved ON public.spoilage_alerts(resolved);


-- ────────────────────────────────────────────────────────────────
-- 7. WEATHER CACHE
-- Caches weather API responses to avoid hitting rate limits.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.weather_cache (
    cache_key   TEXT        PRIMARY KEY,
    data        JSONB       NOT NULL,
    cached_at   TIMESTAMPTZ DEFAULT NOW()
);


-- ────────────────────────────────────────────────────────────────
-- 8. CHAT SESSIONS
-- Stores Voice AI / chatbot conversation history per user.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID        NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    messages    JSONB       NOT NULL DEFAULT '[]',
    language    TEXT        DEFAULT 'en',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_user  ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_time  ON public.chat_sessions(updated_at DESC);


-- ────────────────────────────────────────────────────────────────
-- 9. DEMAND FORECASTS (cached ML results)
-- Stores the output of the demand forecasting model so we don't
-- rerun it every page load.
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.demand_forecasts (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    crop        TEXT        NOT NULL,
    region      TEXT        NOT NULL DEFAULT 'Maharashtra',
    forecast    JSONB       NOT NULL DEFAULT '[]', -- [{day: 1, demand: 87}, ...]
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until  TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '6 hours')
);

CREATE INDEX IF NOT EXISTS idx_forecast_crop    ON public.demand_forecasts(crop);
CREATE INDEX IF NOT EXISTS idx_forecast_valid   ON public.demand_forecasts(valid_until);


-- ────────────────────────────────────────────────────────────────
-- 10. MANDI PRICES (cached market feed)
-- ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.mandi_prices (
    id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    crop        TEXT        NOT NULL,
    mandi       TEXT        NOT NULL,
    price_kg    NUMERIC(8,2),
    unit        TEXT        DEFAULT 'kg',
    source      TEXT        DEFAULT 'agmarknet',
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mandi_prices_unique_daily ON public.mandi_prices(crop, mandi, ((fetched_at AT TIME ZONE 'UTC')::DATE));
CREATE INDEX IF NOT EXISTS idx_mandi_crop   ON public.mandi_prices(crop);
CREATE INDEX IF NOT EXISTS idx_mandi_time   ON public.mandi_prices(fetched_at DESC);


-- ================================================================
-- ROW LEVEL SECURITY (RLS)
-- Users can only see their own data. Admins can see everything.
-- ================================================================
ALTER TABLE public.profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crop_queries    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transport_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.shipments       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.blockchain_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.spoilage_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_sessions   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.demand_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mandi_prices    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.weather_cache   ENABLE ROW LEVEL SECURITY;

-- Profiles: read own, update own
CREATE POLICY "profiles_select_own" ON public.profiles FOR SELECT USING (auth.uid() = id);
CREATE POLICY "profiles_update_own" ON public.profiles FOR UPDATE USING (auth.uid() = id);

-- Crop queries: CRUD own rows
CREATE POLICY "crop_own" ON public.crop_queries FOR ALL USING (auth.uid() = user_id);

-- Transport pools: own rows
CREATE POLICY "transport_own" ON public.transport_pools FOR ALL USING (auth.uid() = created_by);

-- Shipments: read own, insert own
CREATE POLICY "shipments_own" ON public.shipments FOR ALL USING (auth.uid() = farmer_id);

-- Blockchain events: read all (public supply chain transparency), insert own
CREATE POLICY "bc_read_all"  ON public.blockchain_events FOR SELECT USING (TRUE);
CREATE POLICY "bc_insert_own" ON public.blockchain_events FOR INSERT WITH CHECK (auth.uid() = recorded_by);

-- Spoilage: own rows
CREATE POLICY "spoilage_own" ON public.spoilage_alerts FOR ALL USING (auth.uid() = farmer_id);

-- Chat: own sessions
CREATE POLICY "chat_own" ON public.chat_sessions FOR ALL USING (auth.uid() = user_id);

-- Demand forecasts + mandi prices + weather: public read (market data)
CREATE POLICY "forecast_read_all" ON public.demand_forecasts FOR SELECT USING (TRUE);
CREATE POLICY "mandi_read_all"    ON public.mandi_prices    FOR SELECT USING (TRUE);
CREATE POLICY "weather_read_all"  ON public.weather_cache   FOR SELECT USING (TRUE);

-- Service role can insert/update market data tables (backend only)
CREATE POLICY "forecast_service_write" ON public.demand_forecasts FOR INSERT WITH CHECK (TRUE);
CREATE POLICY "mandi_service_write"    ON public.mandi_prices    FOR INSERT WITH CHECK (TRUE);
CREATE POLICY "weather_service_write"  ON public.weather_cache   FOR ALL   USING (TRUE);


-- ================================================================
-- REALTIME
-- Enable live subscriptions for key tables so the dashboard
-- updates automatically without page refresh.
-- ================================================================
ALTER PUBLICATION supabase_realtime ADD TABLE public.spoilage_alerts;
ALTER PUBLICATION supabase_realtime ADD TABLE public.mandi_prices;
ALTER PUBLICATION supabase_realtime ADD TABLE public.shipments;
ALTER PUBLICATION supabase_realtime ADD TABLE public.demand_forecasts;


-- ================================================================
-- SAMPLE DATA (optional — comment out in production)
-- ================================================================
INSERT INTO public.mandi_prices (crop, mandi, price_kg) VALUES
    ('Tomato',  'Pune APMC',          22.50),
    ('Tomato',  'Nashik APMC',        21.00),
    ('Onion',   'Pune APMC',          18.00),
    ('Onion',   'Lasalgaon APMC',     19.50),
    ('Potato',  'Kolhapur APMC',      15.00),
    ('Wheat',   'Solapur APMC',       24.00),
    ('Brinjal', 'Nashik APMC',        12.00)
ON CONFLICT DO NOTHING;

-- ================================================================
-- DONE — Run this entire file in Supabase SQL Editor
-- ================================================================
