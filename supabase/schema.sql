-- FlowTracer Database Schema
-- Run this in your Supabase SQL Editor

-- Enable realtime for live updates
DROP PUBLICATION IF EXISTS supabase_realtime;
CREATE PUBLICATION supabase_realtime;

-- Flows table - tracks each API request/session
CREATE TABLE flows (
    id UUID PRIMARY KEY,
    request_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN completed_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
            ELSE NULL 
        END
    ) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Flow steps table - individual function calls within a flow
CREATE TABLE flow_steps (
    id UUID PRIMARY KEY,
    flow_id UUID REFERENCES flows(id) ON DELETE CASCADE,
    function_name TEXT NOT NULL,
    display_name TEXT,
    parent_step_id UUID REFERENCES flow_steps(id) ON DELETE CASCADE,
    thread_id BIGINT,
    task_id BIGINT, -- for async tasks
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER GENERATED ALWAYS AS (
        CASE 
            WHEN completed_at IS NOT NULL 
            THEN EXTRACT(EPOCH FROM (completed_at - started_at)) * 1000
            ELSE NULL 
        END
    ) STORED,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optional: Flow data table for storing data snapshots
CREATE TABLE flow_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id UUID REFERENCES flow_steps(id) ON DELETE CASCADE,
    data_type TEXT NOT NULL, -- 'input', 'output', 'error'
    data_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_flows_request_id ON flows(request_id);
CREATE INDEX idx_flows_endpoint ON flows(endpoint);
CREATE INDEX idx_flows_started_at ON flows(started_at DESC);

CREATE INDEX idx_flow_steps_flow_id ON flow_steps(flow_id);
CREATE INDEX idx_flow_steps_parent_id ON flow_steps(parent_step_id);
CREATE INDEX idx_flow_steps_function_name ON flow_steps(function_name);
CREATE INDEX idx_flow_steps_started_at ON flow_steps(started_at DESC);

CREATE INDEX idx_flow_data_step_id ON flow_data(step_id);

-- Enable realtime for live flow tracking
ALTER PUBLICATION supabase_realtime ADD TABLE flows;
ALTER PUBLICATION supabase_realtime ADD TABLE flow_steps;

-- Row Level Security (RLS) - basic setup
ALTER TABLE flows ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE flow_data ENABLE ROW LEVEL SECURITY;

-- Basic policy - adjust based on your auth requirements
CREATE POLICY "Enable all operations for authenticated users" ON flows
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all operations for authenticated users" ON flow_steps
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Enable all operations for authenticated users" ON flow_data
    FOR ALL USING (auth.role() = 'authenticated');

-- Views for easier querying
CREATE VIEW flow_summary AS
SELECT 
    f.id,
    f.request_id,
    f.endpoint,
    f.started_at,
    f.completed_at,
    f.duration_ms,
    COUNT(fs.id) as total_steps,
    COUNT(CASE WHEN fs.error IS NOT NULL THEN 1 END) as error_steps,
    MAX(fs.completed_at) as last_step_completed
FROM flows f
LEFT JOIN flow_steps fs ON f.id = fs.flow_id
GROUP BY f.id, f.request_id, f.endpoint, f.started_at, f.completed_at, f.duration_ms;

-- Function to get flow tree structure
CREATE OR REPLACE FUNCTION get_flow_tree(flow_uuid UUID)
RETURNS TABLE (
    step_id UUID,
    function_name TEXT,
    display_name TEXT,
    parent_step_id UUID,
    level INTEGER,
    duration_ms INTEGER,
    error TEXT,
    thread_id BIGINT,
    started_at TIMESTAMP WITH TIME ZONE
) AS $$
WITH RECURSIVE flow_tree AS (
    -- Base case: root steps (no parent)
    SELECT 
        fs.id as step_id,
        fs.function_name,
        fs.display_name,
        fs.parent_step_id,
        0 as level,
        fs.duration_ms,
        fs.error,
        fs.thread_id,
        fs.started_at
    FROM flow_steps fs
    WHERE fs.flow_id = flow_uuid AND fs.parent_step_id IS NULL
    
    UNION ALL
    
    -- Recursive case: child steps
    SELECT 
        fs.id as step_id,
        fs.function_name,
        fs.display_name,
        fs.parent_step_id,
        ft.level + 1,
        fs.duration_ms,
        fs.error,
        fs.thread_id,
        fs.started_at
    FROM flow_steps fs
    JOIN flow_tree ft ON fs.parent_step_id = ft.step_id
    WHERE fs.flow_id = flow_uuid
)
SELECT * FROM flow_tree
ORDER BY started_at;
$$ LANGUAGE SQL;