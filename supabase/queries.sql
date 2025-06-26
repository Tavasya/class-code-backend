-- FlowTracer - Useful Queries for Analyzing Your Data Flows

-- 1. Get all flows for a specific endpoint
SELECT 
    f.request_id,
    f.started_at,
    f.duration_ms,
    COUNT(fs.id) as total_steps,
    COUNT(CASE WHEN fs.error IS NOT NULL THEN 1 END) as errors
FROM flows f
LEFT JOIN flow_steps fs ON f.id = fs.flow_id
WHERE f.endpoint = '/api/your-endpoint'
GROUP BY f.id, f.request_id, f.started_at, f.duration_ms
ORDER BY f.started_at DESC;

-- 2. Get the complete flow tree for a specific request
SELECT 
    step_id,
    REPEAT('  ', level) || display_name as indented_name,
    function_name,
    duration_ms,
    error,
    thread_id
FROM get_flow_tree('your-flow-id-here')
ORDER BY started_at;

-- 3. Find slowest functions across all flows
SELECT 
    function_name,
    display_name,
    COUNT(*) as call_count,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    MIN(duration_ms) as min_duration_ms
FROM flow_steps
WHERE completed_at IS NOT NULL
GROUP BY function_name, display_name
ORDER BY avg_duration_ms DESC
LIMIT 20;

-- 4. Identify functions that often fail
SELECT 
    function_name,
    display_name,
    COUNT(*) as total_calls,
    COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as error_calls,
    ROUND(
        COUNT(CASE WHEN error IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 
        2
    ) as error_rate_percent
FROM flow_steps
GROUP BY function_name, display_name
HAVING COUNT(*) > 5  -- Only functions called more than 5 times
ORDER BY error_rate_percent DESC;

-- 5. Analyze concurrency patterns - see which functions run in parallel
SELECT 
    f.request_id,
    fs.thread_id,
    COUNT(*) as functions_in_thread,
    STRING_AGG(fs.display_name, ' → ' ORDER BY fs.started_at) as execution_path
FROM flows f
JOIN flow_steps fs ON f.id = fs.flow_id
WHERE f.id = 'your-flow-id-here'
GROUP BY f.request_id, fs.thread_id
ORDER BY fs.thread_id;

-- 6. Get recent flows with their status
SELECT 
    f.request_id,
    f.endpoint,
    f.started_at,
    f.duration_ms,
    CASE 
        WHEN f.completed_at IS NULL THEN 'In Progress'
        WHEN EXISTS(SELECT 1 FROM flow_steps WHERE flow_id = f.id AND error IS NOT NULL) THEN 'Has Errors'
        ELSE 'Completed'
    END as status,
    (SELECT COUNT(*) FROM flow_steps WHERE flow_id = f.id) as total_steps
FROM flows f
ORDER BY f.started_at DESC
LIMIT 50;

-- 7. Performance analysis - find bottlenecks in your data flow
WITH step_performance AS (
    SELECT 
        fs.function_name,
        fs.display_name,
        fs.duration_ms,
        f.endpoint,
        RANK() OVER (PARTITION BY f.id ORDER BY fs.duration_ms DESC) as duration_rank
    FROM flow_steps fs
    JOIN flows f ON fs.flow_id = f.id
    WHERE fs.duration_ms IS NOT NULL
)
SELECT 
    endpoint,
    function_name,
    display_name,
    AVG(duration_ms) as avg_duration_ms,
    COUNT(*) as occurrences
FROM step_performance
WHERE duration_rank <= 3  -- Top 3 slowest steps per flow
GROUP BY endpoint, function_name, display_name
ORDER BY avg_duration_ms DESC;

-- 8. Real-time monitoring - currently running flows
SELECT 
    f.request_id,
    f.endpoint,
    f.started_at,
    NOW() - f.started_at as running_for,
    (SELECT COUNT(*) FROM flow_steps WHERE flow_id = f.id AND completed_at IS NOT NULL) as completed_steps,
    (SELECT COUNT(*) FROM flow_steps WHERE flow_id = f.id) as total_steps
FROM flows f
WHERE f.completed_at IS NULL
ORDER BY f.started_at DESC;

-- 9. Data flow patterns - see common execution paths
SELECT 
    STRING_AGG(fs.display_name, ' → ' ORDER BY fs.started_at) as execution_path,
    COUNT(*) as frequency,
    AVG(f.duration_ms) as avg_total_duration
FROM flows f
JOIN flow_steps fs ON f.id = fs.flow_id
WHERE fs.parent_step_id IS NULL  -- Only root-level steps for simplicity
GROUP BY f.endpoint
HAVING COUNT(*) > 1
ORDER BY frequency DESC;

-- 10. Function dependency analysis - see which functions call which
SELECT 
    parent.display_name as caller,
    child.display_name as called,
    COUNT(*) as call_frequency,
    AVG(child.duration_ms) as avg_duration
FROM flow_steps parent
JOIN flow_steps child ON parent.id = child.parent_step_id
GROUP BY parent.display_name, child.display_name
ORDER BY call_frequency DESC;