# Remove Practice Triggers Implementation Guide

## Overview
This guide outlines the steps to remove database triggers from the practice system while maintaining real-time updates and improving performance.

## Goals
- Remove trigger-based latency (200-800ms → 50-150ms)
- Keep real-time frontend updates via Supabase Realtime
- Maintain existing API endpoints
- Improve error handling and debugging

---

## Backend Changes

### 1. Update Practice Endpoints
**File:** `app/api/v1/endpoints/practice_endpoint.py`

- [ ] **Remove trigger dependencies** - Ensure all endpoints work without expecting triggers to fire
- [ ] **Add direct service calls** - Replace trigger-based flows with direct service method calls
- [ ] **Improve error handling** - Add proper error responses since triggers won't silently fail
- [ ] **Add logging** - Better observability for practice flow debugging

### 2. Enhance Practice Service
**File:** `app/services/practice_session_service.py`

- [ ] **Move trigger logic into service methods** - Consolidate auto-improve, auto-start, auto-submit logic
- [ ] **Add method: `auto_improve_transcript(session_id)`** - Replace trigger 1 functionality
- [ ] **Add method: `auto_start_practice(session_id)`** - Replace trigger 2 functionality  
- [ ] **Add method: `auto_submit_recording(attempt_data)`** - Replace trigger 3 functionality
- [ ] **Update existing methods** - Call new auto-methods where appropriate
- [ ] **Add retry logic** - Handle failures that triggers couldn't recover from

### 3. Update Webhook Handlers
**File:** `app/pubsub/webhooks/practice_webhook.py`

- [ ] **Ensure database updates trigger real-time** - Verify all status updates reach frontend
- [ ] **Add progress tracking updates** - Update practice session progress after each webhook
- [ ] **Optimize database writes** - Batch updates where possible for better performance

### 4. Remove Edge Function Dependencies
**Files:** Any edge function calls related to practice

- [ ] **Identify edge function usage** - Search for practice-related edge function calls
- [ ] **Replace with direct API calls** - Convert edge function calls to internal service calls
- [ ] **Remove edge function deployments** - Clean up unused practice edge functions

---

## Frontend Changes

### 1. Update Practice Flow Components
**Files:** Practice-related frontend components

- [ ] **Add direct API calls** - Replace any trigger-dependent logic with direct endpoint calls
- [ ] **Update practice session creation** - Call improve-transcript endpoint directly after session creation
- [ ] **Update practice start flow** - Call start-practice endpoint directly when user starts practice
- [ ] **Update recording submission** - Call sentence/word endpoints directly after recording

### 2. Enhance Real-time Subscriptions
**Files:** Practice real-time hooks/components

- [ ] **Verify Supabase Realtime subscriptions** - Ensure practice_sessions and practice_attempts tables are subscribed
- [ ] **Add progress update handling** - Handle real-time progress updates from webhook completions
- [ ] **Optimize subscription scope** - Subscribe only to relevant session/attempt changes
- [ ] **Add connection error handling** - Handle WebSocket disconnections gracefully

### 3. Update State Management
**Files:** Practice Redux/state files

- [ ] **Remove trigger assumptions** - Update state logic that assumed triggers would handle certain flows
- [ ] **Add loading states** - Show loading indicators for direct API calls
- [ ] **Improve error states** - Handle API errors that triggers couldn't communicate
- [ ] **Add retry mechanisms** - Allow users to retry failed operations

---

## Database Changes

### 1. Remove Practice Triggers
**File:** `supabase/practice_triggers.sql`

- [ ] **Disable triggers first** - Run `SELECT disable_practice_triggers();` to test without triggers
- [ ] **Test system functionality** - Verify everything works with triggers disabled
- [ ] **Drop trigger functions** - Remove `trigger_improve_transcript()`, `trigger_start_practice()`, `trigger_submit_recording()`
- [ ] **Drop triggers** - Remove `practice_session_auto_improve_trigger`, `practice_session_auto_start_trigger`, `practice_attempts_auto_submit_trigger`
- [ ] **Remove utility functions** - Clean up `disable_practice_triggers()` and `enable_practice_triggers()`

### 2. Optimize Database Performance
**Database:** Supabase SQL Editor

- [ ] **Add performance indexes** - Index frequently queried columns in practice tables
- [ ] **Review query patterns** - Optimize queries that were previously hidden in triggers
- [ ] **Add database constraints** - Ensure data integrity without trigger validations
- [ ] **Update RLS policies** - Verify Row Level Security still works without triggers

### 3. Clean Up Edge Functions
**Supabase:** Edge Functions Dashboard

- [ ] **Remove practice edge functions** - Delete `practice-improve-transcript`, `practice-start-practice`, `practice-submit-recording`
- [ ] **Update function list** - Remove practice functions from deployment scripts
- [ ] **Clean up function logs** - Clear old edge function logs and monitoring

---

## Testing Checklist

### Backend Testing
- [ ] **Test practice session creation** - Verify transcript improvement starts automatically
- [ ] **Test practice start flow** - Verify sentence extraction and practice setup
- [ ] **Test recording submission** - Verify pronunciation analysis and progress tracking
- [ ] **Test webhook handling** - Verify real-time updates work after webhook completion
- [ ] **Load test endpoints** - Verify improved latency (target: 50-150ms)

### Frontend Testing
- [ ] **Test real-time updates** - Verify UI updates instantly when backend changes status
- [ ] **Test error handling** - Verify user sees clear errors instead of silent trigger failures
- [ ] **Test practice flow** - Complete end-to-end practice session without triggers
- [ ] **Test offline/reconnection** - Verify real-time subscriptions reconnect properly

### Database Testing
- [ ] **Verify data integrity** - Ensure practice data is consistent without triggers
- [ ] **Test concurrent sessions** - Verify multiple users can practice simultaneously
- [ ] **Monitor query performance** - Ensure database queries are optimized

---

## Rollback Plan

If issues arise, you can quickly rollback:

### Quick Rollback
- [ ] **Re-enable triggers** - Run `SELECT enable_practice_triggers();`
- [ ] **Redeploy edge functions** - Restore practice edge functions
- [ ] **Revert frontend changes** - Switch back to trigger-dependent frontend code

### Full Rollback
- [ ] **Restore trigger SQL** - Run the original `practice_triggers.sql` file
- [ ] **Restore edge functions** - Redeploy all practice edge functions
- [ ] **Restore frontend** - Revert all frontend changes
- [ ] **Restore backend** - Revert service and endpoint changes

---

## Performance Monitoring

After implementation, monitor these metrics:

### Latency Metrics
- [ ] **Practice session creation time** - Should improve from 200-800ms to 50-150ms
- [ ] **Recording submission response time** - Should be consistently under 100ms
- [ ] **Real-time update delay** - Should remain under 50ms

### Error Metrics
- [ ] **Practice session failure rate** - Should improve with better error handling
- [ ] **API timeout rate** - Should decrease without edge function cold starts
- [ ] **Real-time connection drops** - Should remain stable

### User Experience Metrics
- [ ] **Practice completion rate** - Should improve with faster, more reliable system
- [ ] **User satisfaction** - Should improve with better performance and error messaging

---

## Implementation Order

1. **Phase 1:** Backend changes (services and endpoints)
2. **Phase 2:** Frontend changes (API calls and state management)
3. **Phase 3:** Database changes (remove triggers)
4. **Phase 4:** Testing and monitoring
5. **Phase 5:** Clean up (remove edge functions and unused code)

This order ensures you can test each phase before proceeding and have working rollback options at each step.