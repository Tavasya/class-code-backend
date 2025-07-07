-- Practice Session Database Triggers (Updated for Edge Functions)
-- These triggers automatically call Supabase Edge Functions when database changes occur
-- Run these in your Supabase SQL Editor

-- ====================================================================================
-- TRIGGER 1: Auto-Improve Transcript
-- When a practice session is inserted with audio_url, automatically start transcript improvement
-- ====================================================================================

CREATE OR REPLACE FUNCTION trigger_improve_transcript()
RETURNS TRIGGER AS $$
BEGIN
  -- Only trigger if we have an audio URL and no status is set (new session)
  IF NEW.original_audio_url IS NOT NULL AND (NEW.status IS NULL OR NEW.status = '') THEN
    -- Call the practice-improve-transcript edge function
    PERFORM supabase_url.functions.invoke(
      'practice-improve-transcript',
      json_build_object('session_id', NEW.id::text)::jsonb
    );
    
    -- Update status to indicate processing started (optional - edge function will do this too)
    UPDATE practice_sessions 
    SET status = 'transcript_processing' 
    WHERE id = NEW.id;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER practice_session_auto_improve_trigger
  AFTER INSERT ON practice_sessions
  FOR EACH ROW
  EXECUTE FUNCTION trigger_improve_transcript();

-- ====================================================================================
-- TRIGGER 2: Auto-Start Practice Flow
-- When status is updated to 'start_practice', automatically call start-practice endpoint
-- ====================================================================================

CREATE OR REPLACE FUNCTION trigger_start_practice()
RETURNS TRIGGER AS $$
BEGIN
  -- Only trigger when status changes to 'start_practice'
  IF NEW.status = 'start_practice' AND (OLD.status IS NULL OR OLD.status != 'start_practice') THEN
    -- Call the practice-start-practice edge function
    PERFORM supabase_url.functions.invoke(
      'practice-start-practice',
      json_build_object('session_id', NEW.id::text)::jsonb
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER practice_session_auto_start_trigger
  AFTER UPDATE ON practice_sessions
  FOR EACH ROW
  EXECUTE FUNCTION trigger_start_practice();

-- ====================================================================================
-- TRIGGER 3: Auto-Submit Recordings for Analysis
-- When practice_attempts are inserted, automatically submit for pronunciation analysis
-- ====================================================================================

CREATE OR REPLACE FUNCTION trigger_submit_recording()
RETURNS TRIGGER AS $$
DECLARE
  payload jsonb;
BEGIN
  -- Build payload for edge function based on attempt type
  IF NEW.attempt_type = 'sentence' THEN
    payload := json_build_object(
      'session_id', NEW.session_id::text,
      'attempt_type', 'sentence',
      'sentence_index', COALESCE(NEW.sentence_index, 0),
      'audio_url', NEW.audio_url
    )::jsonb;
    
  ELSIF NEW.attempt_type = 'word' THEN
    payload := json_build_object(
      'session_id', NEW.session_id::text,
      'attempt_type', 'word',
      'word', NEW.content,
      'audio_url', NEW.audio_url
    )::jsonb;
    
  ELSIF NEW.attempt_type = 'full_transcript' THEN
    payload := json_build_object(
      'session_id', NEW.session_id::text,
      'attempt_type', 'full_transcript',
      'audio_url', NEW.audio_url
    )::jsonb;
  ELSE
    -- Unknown attempt type, skip
    RETURN NEW;
  END IF;
  
  -- Call the practice-submit-recording edge function
  PERFORM supabase_url.functions.invoke(
    'practice-submit-recording',
    payload
  );
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER practice_attempts_auto_submit_trigger
  AFTER INSERT ON practice_attempts
  FOR EACH ROW
  EXECUTE FUNCTION trigger_submit_recording();

-- ====================================================================================
-- UTILITY FUNCTIONS
-- ====================================================================================

-- Function to disable triggers temporarily (useful for bulk operations)
CREATE OR REPLACE FUNCTION disable_practice_triggers()
RETURNS void AS $$
BEGIN
  ALTER TABLE practice_sessions DISABLE TRIGGER practice_session_auto_improve_trigger;
  ALTER TABLE practice_sessions DISABLE TRIGGER practice_session_auto_start_trigger;
  ALTER TABLE practice_attempts DISABLE TRIGGER practice_attempts_auto_submit_trigger;
END;
$$ LANGUAGE plpgsql;

-- Function to re-enable triggers
CREATE OR REPLACE FUNCTION enable_practice_triggers()
RETURNS void AS $$
BEGIN
  ALTER TABLE practice_sessions ENABLE TRIGGER practice_session_auto_improve_trigger;
  ALTER TABLE practice_sessions ENABLE TRIGGER practice_session_auto_start_trigger;
  ALTER TABLE practice_attempts ENABLE TRIGGER practice_attempts_auto_submit_trigger;
END;
$$ LANGUAGE plpgsql;

-- ====================================================================================
-- SETUP INSTRUCTIONS
-- ====================================================================================

/*
SETUP INSTRUCTIONS (UPDATED FOR EDGE FUNCTIONS):

1. Deploy the edge functions first:
   - Deploy practice-improve-transcript
   - Deploy practice-start-practice  
   - Deploy practice-submit-recording

2. Run this SQL in your Supabase SQL Editor

3. Test the triggers:
   
   -- Test auto-improve trigger
   INSERT INTO practice_sessions (original_audio_url) 
   VALUES ('https://example.com/test-audio.webm');
   
   -- Test auto-start trigger
   UPDATE practice_sessions 
   SET status = 'start_practice' 
   WHERE id = '[session-id]';
   
   -- Test auto-submit trigger
   INSERT INTO practice_attempts (session_id, attempt_type, content, audio_url, sentence_index)
   VALUES ('[session-id]', 'sentence', 'test sentence', 'https://example.com/recording.webm', 0);

4. Monitor edge function logs in Supabase Dashboard > Edge Functions

5. Check backend logs to see if endpoints are being called

6. If you need to disable triggers temporarily:
   SELECT disable_practice_triggers();
   
7. To re-enable:
   SELECT enable_practice_triggers();

EDGE FUNCTION DEPLOYMENT:
- supabase functions deploy practice-improve-transcript
- supabase functions deploy practice-start-practice
- supabase functions deploy practice-submit-recording
*/