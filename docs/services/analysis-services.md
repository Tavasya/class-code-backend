# Analysis Services

## 🎯 Overview

The Audio Analysis API includes five core analysis services that evaluate different aspects of spoken language. Each service operates independently and can be scaled separately through the Pub/Sub messaging system.

## 🗣️ Pronunciation Service

**File**: `app/services/pronunciation_service.py`  
**Size**: 29KB (668 lines) - The largest and most complex service

### Purpose
Analyzes the phonetic accuracy of spoken words by comparing actual pronunciation with expected pronunciation patterns.

### Key Features
- **Phoneme-level analysis** using CMU Dictionary
- **Word-level pronunciation scoring**
- **Stress pattern recognition**
- **Confidence scoring for each analysis**
- **Support for multiple accents and variations**

### Technology Stack
- **spaCy NLP**: Text processing and tokenization
- **CMU Dictionary**: Phonetic transcription reference
- **Custom phonetic algorithms**: Pronunciation comparison
- **Audio analysis libraries**: WAV file processing

### Input Requirements
```json
{
  "wav_path": "/tmp/session_123/audio_1.wav",
  "transcript": "Hello world, this is my pronunciation test.",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

### Output Structure
```json
{
  "overall_score": 85.5,
  "phoneme_scores": [
    {
      "phoneme": "h",
      "expected": "h",
      "actual": "h", 
      "score": 95.0,
      "confidence": 0.92
    }
  ],
  "word_scores": [
    {
      "word": "hello",
      "expected_pronunciation": "HH AH L OW",
      "actual_pronunciation": "HH EH L OW",
      "score": 88.0,
      "issues": ["vowel_substitution"]
    }
  ],
  "stress_patterns": {...},
  "confidence": 0.89,
  "detailed_feedback": "Minor vowel variations detected..."
}
```

### Analysis Process
1. **Audio preprocessing**: WAV file analysis and cleanup
2. **Phonetic extraction**: Extract phonemes from audio
3. **Reference matching**: Compare with CMU Dictionary
4. **Scoring calculation**: Weight phonemes by importance
5. **Feedback generation**: Create detailed improvement suggestions

## 🎭 Fluency Service

**File**: `app/services/fluency_service.py`  
**Size**: 15KB (334 lines)

### Purpose
Evaluates the natural flow, rhythm, and pace of speech to determine speaking fluency.

### Key Features
- **Speech rate analysis** (words per minute)
- **Pause detection and analysis**
- **Filler word identification**
- **Rhythm and naturalness scoring**
- **Hesitation pattern recognition**

### Technology Stack
- **Audio processing**: Speech rate calculation
- **NLP libraries**: Filler word detection
- **Statistical analysis**: Pause pattern evaluation
- **Machine learning models**: Fluency scoring

### Analysis Metrics
```json
{
  "overall_score": 78.9,
  "words_per_minute": 145,
  "pause_analysis": {
    "total_pauses": 8,
    "average_pause_duration": 0.8,
    "pause_ratio": 0.12,
    "natural_pauses": 5,
    "hesitation_pauses": 3
  },
  "filler_words": {
    "count": 4,
    "types": ["um", "uh", "like"],
    "frequency": 0.08
  },
  "rhythm_score": 82.0,
  "naturalness_score": 75.0,
  "fluency_breaks": [
    {
      "timestamp": 12.5,
      "type": "long_pause",
      "duration": 2.1
    }
  ]
}
```

### Scoring Algorithm
1. **Base WPM scoring**: Optimal range 140-180 WPM
2. **Pause penalty**: Excessive or unnatural pauses reduce score
3. **Filler word penalty**: Too many fillers impact naturalness
4. **Rhythm bonus**: Consistent speech patterns increase score
5. **Context adjustment**: Adjust for question complexity

## 📝 Grammar Service

**File**: `app/services/grammar_service.py`  
**Size**: 17KB (381 lines)

### Purpose
Analyzes grammatical correctness, sentence structure, and linguistic complexity using advanced AI models.

### Key Features
- **OpenAI GPT integration** for advanced grammar analysis
- **Rule-based grammar checking**
- **Sentence structure evaluation**
- **Error categorization and suggestions**
- **Complexity assessment**

### Technology Stack
- **OpenAI API**: Advanced grammar analysis
- **spaCy NLP**: Sentence parsing and tokenization
- **Custom rule engine**: Grammar pattern matching
- **Linguistic databases**: Grammar rule repositories

### Analysis Categories
```json
{
  "overall_score": 84.2,
  "grammar_errors": [
    {
      "type": "subject_verb_agreement",
      "original_text": "The students was studying",
      "corrected_text": "The students were studying",
      "explanation": "Plural subject requires plural verb",
      "severity": "high",
      "position": {"start": 12, "end": 24}
    }
  ],
  "sentence_structure": {
    "score": 88.0,
    "avg_sentence_length": 12.5,
    "structure_variety": 0.75,
    "complex_sentences": 3,
    "compound_sentences": 2
  },
  "linguistic_complexity": {
    "score": 76.0,
    "subordinate_clauses": 4,
    "passive_voice_usage": 0.15,
    "tense_consistency": 0.92
  },
  "suggestions": [
    "Consider varying sentence length for better flow",
    "Use more complex sentence structures"
  ]
}
```

### Error Classification
- **Syntax errors**: Word order, punctuation
- **Morphological errors**: Verb forms, pluralization
- **Semantic errors**: Word choice, meaning clarity
- **Stylistic issues**: Repetition, awkward phrasing

## 📚 Lexical Service

**File**: `app/services/lexical_service.py`  
**Size**: 8.5KB (205 lines)

### Purpose
Evaluates vocabulary sophistication, word choice appropriateness, and lexical complexity.

### Key Features
- **Vocabulary level assessment**
- **Lexical diversity calculation**
- **Academic vocabulary identification**
- **Readability scoring**
- **Word frequency analysis**

### Technology Stack
- **spaCy NLP**: Linguistic analysis
- **Academic word lists**: Vocabulary level classification
- **Frequency databases**: Word commonness analysis
- **Readability algorithms**: Text complexity scoring

### Analysis Output
```json
{
  "overall_score": 80.1,
  "vocabulary_level": "intermediate-advanced",
  "lexical_diversity": {
    "type_token_ratio": 0.72,
    "unique_words": 45,
    "total_words": 62,
    "diversity_score": 85.0
  },
  "complexity_metrics": {
    "academic_words": 8,
    "rare_words": 3,
    "complex_words": 12,
    "average_word_length": 5.2
  },
  "readability": {
    "flesch_score": 62.3,
    "grade_level": "college",
    "complexity_rating": "moderate"
  },
  "word_frequency_analysis": {
    "high_frequency": 35,
    "medium_frequency": 20,
    "low_frequency": 7
  }
}
```

### Scoring Factors
1. **Lexical diversity**: Variety of vocabulary used
2. **Academic vocabulary**: Use of sophisticated words
3. **Appropriateness**: Context-appropriate word choices
4. **Complexity balance**: Not too simple or overly complex

## 🎓 Vocabulary Service

**File**: `app/services/vocabulary_service.py`  
**Size**: 9.6KB (224 lines)

### Purpose
Provides vocabulary enhancement suggestions and analyzes word choice effectiveness.

### Key Features
- **Vocabulary enhancement suggestions**
- **Synonym and alternative word recommendations**
- **Academic vocabulary identification**
- **Context-appropriate alternatives**
- **Vocabulary level progression tracking**

### Technology Stack
- **Custom vocabulary databases**: Word level classifications
- **Synonym engines**: Alternative word suggestions
- **Context analysis**: Appropriate word choice
- **spaCy NLP**: Text processing and analysis

### Enhancement Output
```json
{
  "overall_score": 83.7,
  "vocabulary_range": "intermediate-advanced",
  "enhancement_suggestions": [
    {
      "original_word": "good",
      "alternatives": ["excellent", "outstanding", "superior"],
      "context": "positive evaluation",
      "improvement_level": "high"
    },
    {
      "original_word": "use",
      "alternatives": ["utilize", "employ", "implement"],
      "context": "formal usage",
      "improvement_level": "medium"
    }
  ],
  "academic_vocabulary": {
    "count": 12,
    "words": ["methodology", "comprehensive", "facilitate"],
    "percentage": 19.4
  },
  "word_choice_analysis": [
    {
      "word": "utilized",
      "level": "academic",
      "appropriateness": "high",
      "frequency": "medium"
    }
  ],
  "vocabulary_gaps": [
    "More technical terminology could enhance precision",
    "Consider domain-specific vocabulary"
  ]
}
```

### Suggestion Algorithm
1. **Context analysis**: Understand word usage context
2. **Level assessment**: Determine current vocabulary level
3. **Gap identification**: Find improvement opportunities
4. **Alternative generation**: Suggest better word choices
5. **Progression tracking**: Monitor vocabulary development

## ⚙️ Service Coordination

### Analysis Coordinator Service
**File**: `app/services/analysis_coordinator_service.py`  
**Size**: 4.9KB (116 lines)

### Purpose
Orchestrates the execution of all analysis services and manages their dependencies.

### Coordination Logic
```python
# State tracking for each question
coordination_state = {
    "audio_done": bool,
    "transcript_done": bool,
    "audio_data": AudioDoneMessage,
    "transcript_data": TranscriptionDoneMessage
}

# When both audio and transcript ready
if state["audio_done"] and state["transcript_done"]:
    publish_to_analysis_services()
```

### Workflow Management
1. **Dependency tracking**: Wait for audio conversion and transcription
2. **Parallel execution**: Trigger all analysis services simultaneously
3. **Result aggregation**: Collect and combine analysis results
4. **Error handling**: Manage failures and retries
5. **Performance monitoring**: Track processing times

## 🔄 Inter-Service Communication

### Message Flow
```
AnalysisCoordinator
    ↓ QUESTION_ANALYSIS_READY
    ├─ PronunciationService → PRONUNCIATION_DONE
    ├─ FluencyService → FLUENCY_DONE
    ├─ GrammarService → GRAMMER_DONE
    ├─ LexicalService → LEXICAL_DONE
    └─ VocabularyService → VOCABULARY_DONE
    ↓
DatabaseService (aggregates all results)
```

### Shared Data Requirements
All analysis services receive:
- **wav_path**: Audio file location (if needed)
- **transcript**: Speech-to-text result
- **question_number**: Question identifier
- **submission_url**: Frontend callback URL
- **session_id**: File management identifier

## 📊 Performance Characteristics

### Processing Times (Typical)
- **Pronunciation**: 3-8 seconds (audio analysis intensive)
- **Fluency**: 2-5 seconds (audio + transcript analysis)
- **Grammar**: 1-3 seconds (OpenAI API dependent)
- **Lexical**: 1-2 seconds (text analysis only)
- **Vocabulary**: 1-2 seconds (text analysis only)

### Scalability Features
- **Independent scaling**: Each service scales separately
- **Parallel processing**: All services run simultaneously
- **Stateless design**: No inter-service dependencies
- **Resource optimization**: Different resource requirements per service

## 🔍 Error Handling & Reliability

### Common Error Scenarios
1. **Audio processing failures**: Corrupted or invalid audio files
2. **External API timeouts**: OpenAI or Azure service issues
3. **Resource exhaustion**: Memory or CPU limitations
4. **Network connectivity**: Service communication problems

### Resilience Strategies
- **Retry mechanisms**: Automatic retry with exponential backoff
- **Graceful degradation**: Continue with available services
- **Error isolation**: One service failure doesn't affect others
- **Comprehensive logging**: Detailed error tracking and debugging 