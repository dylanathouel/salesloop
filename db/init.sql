-- ============================================
-- SalesLoop AI — Schéma de base de données
-- Phase 0 — Modèle de données
-- ============================================

-- Extension pour générer des UUID automatiquement
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. TENANT (l'entreprise cliente)
-- C'est ta frontière d'isolation : TOUT appartient à un tenant
-- ============================================
CREATE TABLE tenant (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,                    -- "Pharma-Corp", "Assurance-Plus"
    plan        TEXT NOT NULL DEFAULT 'trial',    -- trial, starter, pro, enterprise
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================
-- 2. USER (commercial, manager, ou direction)
-- Un user appartient TOUJOURS à un tenant
-- Un commercial a un manager_id qui pointe vers un autre user
-- ============================================
CREATE TABLE "user" (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id   UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    manager_id  UUID REFERENCES "user"(id) ON DELETE SET NULL,  -- NULL si direction/pas de manager
    email       TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    phone       TEXT,                             -- pour WhatsApp
    role        TEXT NOT NULL CHECK (role IN ('commercial', 'manager', 'direction')),
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Un email est unique PAR tenant (deux tenants peuvent avoir le même email)
    UNIQUE (tenant_id, email)
);

-- Index pour les requêtes fréquentes
CREATE INDEX idx_user_tenant ON "user"(tenant_id);
CREATE INDEX idx_user_manager ON "user"(manager_id);
CREATE INDEX idx_user_role ON "user"(tenant_id, role);

-- ============================================
-- 3. CONVERSATION (une session de discussion avec un agent)
-- Le commercial parle avec l'agent collecteur OU l'agent formation
-- ============================================
CREATE TABLE conversation (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    agent_type      TEXT NOT NULL CHECK (agent_type IN ('collector', 'trainer')),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed')),
    
    -- Les données structurées extraites par l'agent (objections, sentiment, etc.)
    -- C'est le JSONB flexible dont on a parlé
    extracted_data  JSONB DEFAULT '{}',
    
    -- Compteur de tokens pour tracker les coûts LLM
    total_tokens    INTEGER NOT NULL DEFAULT 0,
    
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,                  -- NULL tant que la conversation est active

    -- Sécurité : un user ne peut discuter que dans son propre tenant
    CONSTRAINT fk_conversation_tenant CHECK (tenant_id IS NOT NULL)
);

CREATE INDEX idx_conversation_tenant ON conversation(tenant_id);
CREATE INDEX idx_conversation_user ON conversation(user_id);
CREATE INDEX idx_conversation_agent ON conversation(tenant_id, agent_type);
CREATE INDEX idx_conversation_date ON conversation(tenant_id, started_at DESC);
-- Index GIN pour chercher DANS le JSONB (ex: toutes les conversations où sentiment = 'frustrated')
CREATE INDEX idx_conversation_extracted ON conversation USING GIN (extracted_data);

-- ============================================
-- 4. MESSAGE (chaque message dans une conversation)
-- sender = 'user' (le commercial parle) ou 'agent' (l'IA répond)
-- ============================================
CREATE TABLE message (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    sender          TEXT NOT NULL CHECK (sender IN ('user', 'agent')),
    content         TEXT NOT NULL,
    token_count     INTEGER NOT NULL DEFAULT 0,   -- coût de CE message
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_message_conversation ON message(conversation_id);
CREATE INDEX idx_message_date ON message(conversation_id, created_at);

-- ============================================
-- 5. REPORT (synthèse générée par l'agent synthèse)
-- Agrège les conversations d'une période pour un tenant
-- ============================================
CREATE TABLE report (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    period_type     TEXT NOT NULL CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    
    -- Le résumé en texte lisible (ce que la direction lit en premier)
    summary         TEXT,
    
    -- Les insights structurés (top objections, alertes, tendances)
    -- JSONB = flexible, chaque client peut avoir ses propres insights
    insights        JSONB DEFAULT '{}',
    
    -- Les métriques chiffrées (nombre de conversations, sentiment moyen, etc.)
    -- Pareil, JSONB = facile à enrichir par client
    metrics         JSONB DEFAULT '{}',
    
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- On ne veut pas deux rapports pour la même période
    UNIQUE (tenant_id, period_type, period_start)
);

CREATE INDEX idx_report_tenant ON report(tenant_id);
CREATE INDEX idx_report_period ON report(tenant_id, period_start DESC);
CREATE INDEX idx_report_insights ON report USING GIN (insights);

-- ============================================
-- 6. REPORT_CONVERSATION (table de liaison many-to-many)
-- Un rapport agrège N conversations
-- Une conversation peut apparaître dans le rapport daily ET weekly
-- ============================================
CREATE TABLE report_conversation (
    report_id       UUID NOT NULL REFERENCES report(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    PRIMARY KEY (report_id, conversation_id)
);

-- ============================================
-- 7. DIRECTIVE (décision de la direction)
-- La direction crée une directive après avoir lu un rapport
-- L'agent formation utilise ces directives pour coacher
-- ============================================
CREATE TABLE directive (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES "user"(id),  -- qui dans la direction l'a créée
    content         TEXT NOT NULL,                         -- "Former sur l'argumentaire prix"
    priority        TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'completed', 'archived')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_directive_tenant ON directive(tenant_id);
CREATE INDEX idx_directive_status ON directive(tenant_id, status);

-- ============================================
-- 8. TRAINING_CONTENT (documents source pour le RAG)
-- Docs produit, FAQ, techniques de vente uploadés par le client
-- L'agent formation cherche dedans pour répondre aux commerciaux
-- ============================================
CREATE TABLE training_content (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,                         -- "Catalogue produit 2026"
    raw_content     TEXT NOT NULL,                         -- le texte brut du document
    content_type    TEXT NOT NULL CHECK (content_type IN ('product_doc', 'faq', 'sales_technique', 'directive_based')),
    
    -- Métadonnées sur le découpage en chunks (pour le RAG, Phase 5)
    chunk_metadata  JSONB DEFAULT '{}',
    is_embedded     BOOLEAN NOT NULL DEFAULT false,        -- true quand les embeddings sont créés
    
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_tenant ON training_content(tenant_id);
CREATE INDEX idx_training_embedded ON training_content(tenant_id, is_embedded);

-- ============================================
-- FONCTION UTILITAIRE : mise à jour automatique de updated_at
-- Quand tu modifies une ligne, updated_at se met à jour tout seul
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- On applique le trigger sur les tables qui ont updated_at
CREATE TRIGGER tr_tenant_updated BEFORE UPDATE ON tenant
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_user_updated BEFORE UPDATE ON "user"
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER tr_directive_updated BEFORE UPDATE ON directive
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
