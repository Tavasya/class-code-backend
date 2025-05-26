# 🚨 Pub/Sub Infinite Loop Fix - Action Plan

## 🔍 **ROOT CAUSE IDENTIFIED**

The infinite loop in your Google Cloud Pub/Sub system is caused by **duplicate subscriptions** processing the same message multiple times, leading to race conditions and state corruption.

## ❌ **CURRENT BROKEN SETUP**

```
student-submission-topic
    ├── student-submission-topic-audio-sub → /webhooks/student-submission-audio
    └── student-submission-topic-transcription-sub → /webhooks/student-submission-transcription
```

**Problem:** Both subscriptions receive the **SAME MESSAGE**, causing:
- Duplicate processing of each submission
- Race conditions in state management
- Infinite loops when state gets corrupted
- Multiple "done" messages for the same operation

## ✅ **NEW FIXED ARCHITECTURE**

```
student-submission-topic
    └── student-submission-topic-sub → /webhooks/student-submission
        └── Handles BOTH audio and transcription in parallel internally
```

## 🛠️ **REQUIRED GOOGLE CLOUD CHANGES**

### **1. Delete Duplicate Subscription (CRITICAL)**

**DELETE THIS SUBSCRIPTION:**
```bash
gcloud pubsub subscriptions delete student-submission-topic-transcription-sub
```

### **2. Rename Remaining Subscription**

**RENAME THIS SUBSCRIPTION:**
```bash
# First, create new subscription with correct name
gcloud pubsub subscriptions create student-submission-topic-sub \
    --topic=student-submission-topic \
    --push-endpoint=https://classconnect-staging-107872842385.us-west2.run.app/api/v1/webhooks/student-submission

# Then delete the old one
gcloud pubsub subscriptions delete student-submission-topic-audio-sub
```

### **3. Fix Pronunciation Subscription (CRITICAL)**

Your `pronunciation-done-topic-sub` subscription is **BROKEN** because it's trying to listen to a non-existent topic.

**EITHER Option A - Rename Subscription:**
```bash
gcloud pubsub subscriptions delete pronunciation-done-topic-sub

gcloud pubsub subscriptions create pronoun-done-topic-sub \
    --topic=pronoun-done-topic \
    --push-endpoint=https://classconnect-staging-107872842385.us-west2.run.app/api/v1/webhooks/pronunciation-done
```

**OR Option B - Rename Topic:**
```bash
# This is more complex, would need to recreate topic and all its subscriptions
# Recommend Option A instead
```

## 💻 **CODE CHANGES IMPLEMENTED**

✅ **New `SubmissionWebhook`** - Handles both audio and transcription in parallel  
✅ **Updated webhook endpoints** - Single `/student-submission` endpoint  
✅ **Fixed topic references** - `PRONUNCIATION_DONE` instead of `PRONOUN_DONE`  
✅ **Updated configurations** - All webhook configs updated  
✅ **Updated test scripts** - Local testing uses new endpoints  

## 🎯 **DEPLOYMENT STEPS**

### **Step 1: Deploy Code Changes**
1. Deploy the updated code to your Cloud Run service
2. Verify the new `/api/v1/webhooks/student-submission` endpoint is working

### **Step 2: Update Subscriptions**
1. Delete `student-submission-topic-transcription-sub`
2. Create new `student-submission-topic-sub` 
3. Delete old `student-submission-topic-audio-sub`
4. Fix `pronunciation-done-topic-sub` → `pronoun-done-topic-sub`

### **Step 3: Test**
1. Send a test submission using your curl command
2. Monitor logs - should see single processing instead of duplicate
3. Verify no infinite loops occur

## 🔧 **IMMEDIATE BENEFIT**

- ✅ **Eliminates infinite loops**
- ✅ **Maintains parallel processing** (audio + transcription still run in parallel)
- ✅ **Fixes state corruption**
- ✅ **Reduces resource usage** (no duplicate processing)
- ✅ **Improves reliability**

## ⚠️ **CRITICAL NOTES**

1. **The duplicate subscription issue MUST be fixed first** - this is the primary cause of the infinite loop
2. **Audio and transcription will STILL run in parallel** - just from a single message trigger instead of duplicate messages
3. **Test thoroughly** after making subscription changes
4. **Monitor logs** to ensure no more infinite loops occur

## 🚀 **VERIFICATION COMMANDS**

After making changes, verify with:

```bash
# List all subscriptions to confirm changes
gcloud pubsub subscriptions list

# Test the endpoint
curl -X POST https://classconnect-staging-107872842385.us-west2.run.app/api/v1/submission/submit \
-H "Content-Type: application/json" \
-d '{
    "audio_urls": ["your-test-url"],
    "submission_url": "test_fix_verification"
}'
```

The infinite loop should be **completely eliminated** once these changes are deployed! 