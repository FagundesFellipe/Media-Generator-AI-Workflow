-- 1. content_generation_submissions — "What did I send to generate content?"
-- The package you submit to start a generation: your guidance, the source
-- document and the target platforms, plus the summary the ingest node extracts.
CREATE TABLE content_generation_submissions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_type  TEXT NOT NULL
                          CHECK (source_document_type IN ('transcript', 'markdown')),
    target_platforms      TEXT[] NOT NULL
                          CHECK (cardinality(target_platforms) > 0
                                 AND target_platforms <@ ARRAY['youtube', 'linkedin', 'x']),
    user_guidance         TEXT NOT NULL,           -- what you tell the agents: goal, angle, audience
    source_document_text  TEXT NOT NULL,           -- full transcript or .md
    ingest_summary        JSONB,                   -- ContentBrief, filled by the ingest_context node
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- YouTube only makes sense from a video transcript
    CHECK (source_document_type = 'transcript' OR NOT ('youtube' = ANY (target_platforms)))
);


-- 2. runs — "When did it run, how long did it take, how much did it cost?"
-- One execution of a graph. 1 run = 1 LangGraph thread.
-- Regeneration reuses the same run (same thread).
CREATE TABLE runs (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_submission_id  UUID REFERENCES content_generation_submissions(id),  -- NULL for learning runs
    run_type                  TEXT NOT NULL
                              CHECK (run_type IN ('content_generation', 'feedback_learning')),
    langgraph_thread_id       TEXT NOT NULL UNIQUE,
    execution_status          TEXT NOT NULL DEFAULT 'running'
                              CHECK (execution_status IN ('running', 'awaiting_human', 'completed', 'failed')),
    total_cost_usd            NUMERIC(12, 6) NOT NULL DEFAULT 0,  -- sum of steps.cost_usd
    total_tokens              INTEGER NOT NULL DEFAULT 0,
    failure_message           TEXT,                               -- why the run failed
    started_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at               TIMESTAMPTZ,
    -- Computed by Postgres; NULL while the run has not finished.
    -- Includes time spent waiting for your HITL decisions.
    duration_seconds          NUMERIC GENERATED ALWAYS AS
                              (EXTRACT(EPOCH FROM (finished_at - started_at))) STORED
);

CREATE INDEX runs_generation_submission_id_idx ON runs (generation_submission_id);


-- 3. steps — "What did each graph node do?"
-- One row per node execution (written by @traced).
-- LLM/token/cost columns are NULL for nodes without an LLM call (e.g. finalize).
CREATE TABLE steps (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id           UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    graph_node_name  TEXT NOT NULL,                -- e.g. 'li_post'
    llm_model        TEXT,
    tokens_input     INTEGER,
    tokens_output    INTEGER,
    cost_usd         NUMERIC(12, 6),
    latency_ms       INTEGER,
    node_output      JSONB,                        -- what the node returned (structured output for LLM nodes)
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX steps_run_id_idx ON steps (run_id, created_at);


-- 4. generated_contents — "What content did the system generate?"
-- One piece of content from a run (e.g. the LinkedIn post).
-- UNIQUE (run_id, generated_content_type) lets a node write again without
-- duplicating (nodes that interrupt re-run from the top on resume).
CREATE TABLE generated_contents (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                  UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    platform                TEXT NOT NULL CHECK (platform IN ('youtube', 'linkedin', 'x')),
    generated_content_type  TEXT NOT NULL CHECK (generated_content_type IN (
                                'youtube_titles',       -- 3 titles with distinct angles
                                'youtube_thumbnails',   -- 2 thumbnails 16:9
                                'youtube_seo',          -- SEO description + 15+ hashtags
                                'linkedin_post',
                                'linkedin_article',     -- article + cover
                                'linkedin_carousel',    -- slides + copy + 5 hashtags
                                'x_post',
                                'x_thread',
                                'x_visual'
                            )),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- The type must belong to its platform (e.g. 'linkedin_post' -> 'linkedin')
    CHECK (generated_content_type LIKE platform || '\_%'),
    UNIQUE (run_id, generated_content_type)
);


-- 5. generated_content_versions — "Each attempt, and what I thought of it"
-- v1 is the first generation; each rejection produces the next version.
-- Your review lives on the version itself (each version is reviewed once).
CREATE TABLE generated_content_versions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_content_id  UUID NOT NULL REFERENCES generated_contents(id) ON DELETE CASCADE,
    version_number        INTEGER NOT NULL CHECK (version_number >= 1),
    generated_payload     JSONB NOT NULL,                -- the generated content itself, structured
    rendered_image_paths  TEXT[] NOT NULL DEFAULT '{}',  -- PNG/JPG under artifacts/
    produced_by_step_id   UUID REFERENCES steps(id) ON DELETE SET NULL,
    review_status         TEXT NOT NULL DEFAULT 'pending'
                          CHECK (review_status IN ('pending', 'approved', 'rejected')),
    user_rejection_reason TEXT,                          -- the "why" when you reject this version
    reviewed_at           TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (generated_content_id, version_number)
);


-- 6. publication_feedback — "How did it perform after publishing?"  [step 2]
-- Points to the exact version you published.
CREATE TABLE publication_feedback (
    id                            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generated_content_version_id  UUID NOT NULL REFERENCES generated_content_versions(id),
    user_performance_report       TEXT NOT NULL,   -- your free-text metrics and impressions
    published_at                  TIMESTAMPTZ,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX publication_feedback_version_idx ON publication_feedback (generated_content_version_id);
