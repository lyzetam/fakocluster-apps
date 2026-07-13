-- Supabase Memory Tables for Oura Agent
-- Run these migrations in your Supabase project

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- User Profiles (Semantic Memory)
-- ============================================================================
-- Stores goals, baselines, preferences, learned state about each user

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL UNIQUE,  -- Discord user ID

  -- Semantic memory (goals, baselines, preferences)
  goals JSONB DEFAULT '{}'::jsonb,  -- {"sleep_hours": 8, "steps": 10000}
  baselines JSONB DEFAULT '{}'::jsonb,  -- {"hrv_ms": 42, "resting_hr": 58}
  preferences JSONB DEFAULT '{}'::jsonb,  -- {"preferred_specialists": [...]}

  -- Procedural memory (learned behaviors, state)
  agent_state JSONB DEFAULT '{}'::jsonb,  -- {"last_sleep_alert": "2026-07-13", ...}

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE INDEX ON user_profiles(user_id);

-- ============================================================================
-- Conversations (Episodic Memory)
-- ============================================================================
-- Stores all query/response pairs for context and recall

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,  -- Discord user ID
  channel_id TEXT NOT NULL,  -- Discord channel ID

  -- The interaction
  query TEXT NOT NULL,
  response TEXT NOT NULL,
  specialists TEXT[] DEFAULT '{}',  -- ["sleep_analyst", "readiness_advisor"]

  -- For semantic search (populated by embedding function)
  embedding vector(768),  -- 768-dim embeddings from Ollama nomic-embed-text

  created_at TIMESTAMP DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

CREATE INDEX ON conversations(user_id);
CREATE INDEX ON conversations(created_at DESC);
-- Vector search index (for similarity)
CREATE INDEX ON conversations USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- Alerts History (Procedural Memory - Deduplication)
-- ============================================================================
-- Tracks what alerts have been sent to avoid repeating them

CREATE TABLE IF NOT EXISTS alerts_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,  -- Discord user ID

  -- Alert metadata
  alert_type TEXT NOT NULL,  -- "sync", "fatigue", "recovery", "overtraining"
  context JSONB NOT NULL,  -- {"hrv_drop_percent": 20, "days_old": 3}

  created_at TIMESTAMP DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

CREATE INDEX ON alerts_history(user_id, alert_type, created_at DESC);

-- ============================================================================
-- Agent Decisions (Procedural Memory - Learning)
-- ============================================================================
-- Tracks agent decisions to learn patterns

CREATE TABLE IF NOT EXISTS agent_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,

  -- Decision metadata
  decision_type TEXT NOT NULL,  -- "recommended_rest_day", "suggested_training_focus", etc.
  context JSONB NOT NULL,  -- Full context of decision
  outcome JSONB,  -- What happened after the recommendation (populated later)

  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

CREATE INDEX ON agent_decisions(user_id, decision_type, created_at DESC);

-- ============================================================================
-- Agent Learning (Procedural Memory - Improvement)
-- ============================================================================
-- Tracks what the agent has learned about each user

CREATE TABLE IF NOT EXISTS agent_learning (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL UNIQUE,

  -- Learning data
  learned_patterns JSONB DEFAULT '{}'::jsonb,  -- {"high_stress_correlates_with": [...]}
  specialist_effectiveness JSONB DEFAULT '{}'::jsonb,  -- {"sleep_analyst": 0.92, ...}
  user_response_patterns JSONB DEFAULT '{}'::jsonb,  -- {"prefers_concise": true, ...}

  total_interactions INT DEFAULT 0,
  last_updated TIMESTAMP DEFAULT now(),
  FOREIGN KEY (user_id) REFERENCES user_profiles(user_id) ON DELETE CASCADE
);

-- ============================================================================
-- RLS (Row-Level Security)
-- ============================================================================
-- Ensure users can only access their own data

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_learning ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own data
CREATE POLICY user_data_policy ON user_profiles
  FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY conversation_data_policy ON conversations
  FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY alert_data_policy ON alerts_history
  FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY decision_data_policy ON agent_decisions
  FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

CREATE POLICY learning_data_policy ON agent_learning
  FOR SELECT USING (user_id = current_setting('app.current_user_id', true));

-- ============================================================================
-- Views (for easier queries)
-- ============================================================================

-- Recent alerts (for deduplication check)
CREATE VIEW recent_alerts_by_type AS
SELECT
  user_id,
  alert_type,
  COUNT(*) as count,
  MAX(created_at) as last_alert,
  EXTRACT(HOUR FROM NOW() - MAX(created_at)) as hours_since_last
FROM alerts_history
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY user_id, alert_type;

-- User interaction summary
CREATE VIEW user_interaction_stats AS
SELECT
  user_id,
  COUNT(*) as total_conversations,
  COUNT(DISTINCT DATE(created_at)) as days_active,
  ARRAY_AGG(DISTINCT UNNEST(specialists)) as specialists_used,
  MAX(created_at) as last_interaction
FROM conversations
GROUP BY user_id;

-- ============================================================================
-- Triggers (for automation)
-- ============================================================================

-- Auto-update updated_at on user_profiles
CREATE OR REPLACE FUNCTION update_user_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_user_profiles_timestamp
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_user_profiles_updated_at();

-- Auto-update agent_learning on conversation insert
CREATE OR REPLACE FUNCTION update_agent_learning_on_conversation()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO agent_learning (user_id, total_interactions, last_updated)
  VALUES (NEW.user_id, 1, NOW())
  ON CONFLICT (user_id) DO UPDATE
  SET
    total_interactions = agent_learning.total_interactions + 1,
    last_updated = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_learning_on_conversation
  AFTER INSERT ON conversations
  FOR EACH ROW
  EXECUTE FUNCTION update_agent_learning_on_conversation();

-- ============================================================================
-- Indexes (for performance)
-- ============================================================================

CREATE INDEX ON conversations(user_id, created_at DESC);
CREATE INDEX ON alerts_history(user_id, alert_type, created_at DESC);
CREATE INDEX ON agent_decisions(user_id, outcome IS NOT NULL);  -- Decisions with outcomes
CREATE INDEX ON user_profiles(updated_at DESC);  -- Find recently active users
