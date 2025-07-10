# Frontend Implementation Guide - Direct Practice Flow

The practice feature now works directly with user-provided transcripts, eliminating the transcript improvement step for faster and simpler practice sessions.

## 🎯 **Complete Frontend Flow**

### **Step 1: Create Practice Session with User Transcript**

```javascript
// When user provides a transcript and wants to start practice
async function createPracticeSession(transcript, audioUrl = null) {
  // Insert record with user-provided transcript
  const { data, error } = await supabase
    .from('practice_sessions')
    .insert([{
      original_transcript: transcript,
      original_audio_url: audioUrl, // optional
      status: 'ready_for_practice' // ready immediately
    }])
    .select()
    .single();
  
  if (error) throw error;
  
  // Show "Ready to practice" UI immediately
  showReadyToPractice(transcript);
  
  return data.id; // This is your session_id
}
```

### **Step 2: Set Up Real-time Updates (Immediately After Creation)**

```javascript
function setupRealtimeUpdates(sessionId) {
  const channel = supabase
    .channel(`practice-session-${sessionId}`)
    .on('postgres_changes', {
      event: 'UPDATE',
      schema: 'public',
      table: 'practice_sessions',
      filter: `id=eq.${sessionId}`
    }, (payload) => {
      handleSessionUpdate(payload.new);
    })
    .subscribe();
    
  return channel; // Save this to unsubscribe later
}

function handleSessionUpdate(session) {
  const status = session.status;
  
  switch(status) {
    case 'ready_for_practice':
      // Show transcript and "Start Practice" button
      showReadyToPractice(session.original_transcript);
      break;
      
    case 'practicing_sentences':
      // Show sentence recording UI
      showSentencePractice(session);
      break;
      
    case 'practicing_words':
      // Show word recording UI  
      showWordPractice(session);
      break;
      
    case 'completed':
      // Show success screen
      showPracticeComplete(session);
      cleanup();
      break;
      
    case 'failed':
      // Show error message
      showError(session.error_message);
      break;
  }
}
```

### **Step 3: Start Practice Flow (Button Click)**

```javascript
// When user clicks "Start Practice" button
async function startPractice(sessionId) {
  // Update status - trigger automatically calls start-practice endpoint
  const { error } = await supabase
    .from('practice_sessions')
    .update({ status: 'start_practice' })
    .eq('id', sessionId);
  
  if (error) throw error;
  
  // Show "Starting practice..." state
  // Real-time updates will handle the transition to sentence practice
  showStartingPractice();
}
```

### **Step 4: Submit Sentence Recording**

```javascript
// When user records a sentence
async function submitSentenceRecording(sessionId, sentenceIndex, audioBlob) {
  // 1. Upload audio file
  const audioUrl = await uploadAudio(audioBlob);
  
  // 2. Insert practice attempt - trigger automatically calls /sentences endpoint
  const { error } = await supabase
    .from('practice_attempts')
    .insert([{
      session_id: sessionId,
      attempt_type: 'sentence',
      content: getCurrentSentenceText(), // Store the sentence text
      audio_url: audioUrl,
      sentence_index: sentenceIndex
    }]);
  
  if (error) throw error;
  
  // Show "Analyzing pronunciation..." state
  // Real-time updates will handle the results
  showAnalyzing();
}
```

### **Step 5: Submit Word Recording**

```javascript
// When user records a word
async function submitWordRecording(sessionId, word, audioBlob) {
  // 1. Upload audio file
  const audioUrl = await uploadAudio(audioBlob);
  
  // 2. Insert practice attempt - trigger automatically calls /words endpoint
  const { error } = await supabase
    .from('practice_attempts')
    .insert([{
      session_id: sessionId,
      attempt_type: 'word',
      content: word,
      audio_url: audioUrl
      // sentence_index not needed for words
    }]);
  
  if (error) throw error;
  
  // Show "Analyzing pronunciation..." state
  showAnalyzing();
}
```

## 🎯 **UI State Management**

### **Sentence Practice UI**

```javascript
function showSentencePractice(session) {
  const sentences = session.sentences || [];
  const currentIndex = session.current_sentence_index || 0;
  const currentSentence = sentences[currentIndex];
  
  if (!currentSentence) return;
  
  displayUI({
    type: 'sentence_practice',
    text: currentSentence.text,
    progress: `Sentence ${currentIndex + 1} of ${sentences.length}`,
    onRecord: (audioBlob) => submitSentenceRecording(session.id, currentIndex, audioBlob)
  });
}
```

### **Word Practice UI**

```javascript
function showWordPractice(session) {
  const words = session.problematic_words || [];
  const currentIndex = session.current_word_index || 0;
  const currentWord = words[currentIndex];
  
  if (!currentWord) return;
  
  displayUI({
    type: 'word_practice',
    word: currentWord.word,
    context: currentWord.sentence_context,
    progress: `Word ${currentIndex + 1} of ${words.length}`,
    onRecord: (audioBlob) => submitWordRecording(session.id, currentWord.word, audioBlob)
  });
}
```

## 🎯 **Complete Example Implementation**

```javascript
class PracticeFlow {
  constructor() {
    this.sessionId = null;
    this.realtimeChannel = null;
  }
  
  // Start the entire flow with user-provided transcript
  async start(transcript, audioFile = null) {
    try {
      // 1. Upload audio if provided
      let audioUrl = null;
      if (audioFile) {
        audioUrl = await this.uploadAudio(audioFile);
      }
      
      // 2. Create session with transcript (no improvement needed)
      this.sessionId = await this.createSession(transcript, audioUrl);
      
      // 3. Set up real-time updates
      this.setupRealtime();
      
    } catch (error) {
      this.showError('Failed to start practice session');
    }
  }
  
  async createSession(transcript, audioUrl = null) {
    const { data, error } = await supabase
      .from('practice_sessions')
      .insert([{ 
        original_transcript: transcript,
        original_audio_url: audioUrl,
        status: 'ready_for_practice'
      }])
      .select()
      .single();
    
    if (error) throw error;
    return data.id;
  }
  
  setupRealtime() {
    this.realtimeChannel = supabase
      .channel(`practice-session-${this.sessionId}`)
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'practice_sessions',
        filter: `id=eq.${this.sessionId}`
      }, (payload) => {
        this.handleUpdate(payload.new);
      })
      .subscribe();
  }
  
  handleUpdate(session) {
    switch(session.status) {
      case 'ready_for_practice':
        this.showStartPracticeButton(session.original_transcript);
        break;
      case 'practicing_sentences':
        this.showSentencePractice(session);
        break;
      case 'practicing_words':
        this.showWordPractice(session);
        break;
      case 'completed':
        this.showSuccess(session);
        this.cleanup();
        break;
    }
  }
  
  async startPractice() {
    await supabase
      .from('practice_sessions')
      .update({ status: 'start_practice' })
      .eq('id', this.sessionId);
  }
  
  async submitRecording(type, audioBlob, metadata = {}) {
    const audioUrl = await this.uploadAudio(audioBlob);
    
    await supabase
      .from('practice_attempts')
      .insert([{
        session_id: this.sessionId,
        attempt_type: type,
        audio_url: audioUrl,
        ...metadata
      }]);
  }
  
  cleanup() {
    if (this.realtimeChannel) {
      this.realtimeChannel.unsubscribe();
    }
  }
}
```

## 🚫 **What Frontend Should NOT Do**

❌ **Never call these endpoints directly:**
- `/start-practice`  
- `/sentences`
- `/words`

❌ **Never update these fields directly:**
- `status` (except to 'start_practice')
- `sentences`
- `problematic_words`
- `current_sentence_index`
- `current_word_index`

## ✅ **What Frontend SHOULD Do**

✅ **Database operations only:**
- Insert `practice_sessions` record with transcript
- Update `status` to 'start_practice'
- Insert `practice_attempts` records
- Listen to real-time updates

✅ **UI management:**
- React to database state changes
- Show appropriate recording interfaces
- Handle audio upload/recording
- Display progress and results

## 🎯 **Setup Instructions**

1. **Install the database triggers** from `practice_triggers.sql`
2. **Replace the backend URL** in the triggers with your actual domain
3. **Implement the frontend flow** using the examples above

## 🔄 **Migration from Old System**

If you were previously using the improve-transcript functionality:

1. **Update session creation** - Pass transcript directly instead of waiting for improvement
2. **Remove transcript processing UI** - No more "Processing transcript..." states
3. **Update status handling** - Start with 'ready_for_practice' instead of 'transcript_ready'
4. **Simplify real-time handling** - Remove transcript processing status checks