# Vocabulary Service Implementation Guide

## Overview
This document outlines the implementation of vocabulary analysis service that integrates with the existing analysis pipeline. The service analyzes vocabulary usage in transcripts using the Oxford word list data and provides CEFR level-based suggestions.

## Architecture

### Components
1. Vocabulary Service
2. Pub/Sub Integration
3. Analysis Coordinator Integration

### Analysis Coordinator Integration

The vocabulary service integrates with the existing `AnalysisCoordinatorService` which manages parallel execution of different analysis services. The coordinator:

- Triggers vocabulary analysis as part of PHASE 1 analysis
- Manages state tracking for vocabulary analysis completion
- Coordinates with other services (grammar, pronunciation, lexical)
- Handles cleanup of analysis state

### Model Dependencies

The vocabulary service requires updates to the following models:

1. `analysis_model.py`:
   - Add `VocabularyDoneMessage` model
   - Update `QuestionAnalysisReadyMessage` to include vocabulary-specific fields

### Service Dependencies

The vocabulary service integrates with:

1. `analysis_coordinator_service.py`:
   - Manages parallel execution
   - Coordinates analysis flow
   - Handles state management

### Pub/Sub Integration

The vocabulary service integrates with the following Pub/Sub topics:

1. Input Topics:
   - `QUESTION_ANALYSIS_READY`: Triggers vocabulary analysis
   - `VOCABULARY_DONE`: Publishes vocabulary analysis results

2. Required Message Formats:
   - Input: `QuestionAnalysisReadyMessage`
   - Output: `VocabularyDoneMessage`

## Implementation Details

### 1. Models

```python
# app/models/analysis_model.py
class VocabularyDoneMessage(BaseModel):
    """Message model for vocabulary analysis completion"""
    question_number: int
    submission_url: str
    total_questions: Optional[int] = None
    result: Dict[str, Any]  # Vocabulary analysis results
```

### 2. Service Implementation

```python
# app/services/vocabulary_service.py
import logging
from typing import Dict, List, Any
from app.models.analysis_model import VocabularyDoneMessage
from app.utils.vocabulary_utils import (
    get_lemma,
    OXFORD_DATA_CACHE,
    NLP_PROCESSOR
)

logger = logging.getLogger(__name__)

async def analyze_vocabulary(transcript: str) -> Dict[str, Any]:
    """Analyze vocabulary in a transcript"""
    try:
        # Split transcript into sentences
        doc = NLP_PROCESSOR(transcript)
        sentences = [sent.text.strip() for sent in doc.sents]
        
        suggestions = {}
        for i, sentence in enumerate(sentences):
            sent_doc = NLP_PROCESSOR(sentence)
            for j, token in enumerate(sent_doc):
                if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV"]:
                    lemma = get_lemma(token.text, NLP_PROCESSOR)
                    if lemma in OXFORD_DATA_CACHE:
                        word_data = OXFORD_DATA_CACHE[lemma]["value"]  # Access the value field
                        if word_data["level"] in ["A1", "A2"]:  # Basic level words
                            suggestions[f"{i}_{j}"] = {
                                "original_word": token.text,
                                "context": sentence,
                                "word_type": word_data["type"],
                                "level": word_data["level"],
                                "examples": word_data["examples"],
                                "sentence_index": i,
                                "phrase_index": j,
                                "sentence_text": sentence
                            }
        
        # Calculate grade based on suggestions
        grade = calculate_vocabulary_grade(suggestions)
        
        return {
            "grade": grade,
            "vocabulary_suggestions": suggestions,
            "issues": format_issues(suggestions)
        }
    except Exception as e:
        logger.exception("Error in vocabulary analysis")
        return {
            "grade": 0,
            "vocabulary_suggestions": {},
            "issues": [{"error": str(e)}]
        }

def calculate_vocabulary_grade(suggestions: Dict[str, Dict[str, Any]]) -> float:
    """Calculate vocabulary grade based on suggestions"""
    if not suggestions:
        return 100.0
    
    total_words = len(suggestions)
    basic_words = sum(1 for s in suggestions.values() if s["level"] in ["A1", "A2"])
    
    # Grade decreases as more basic words are used
    grade = 100.0 - (basic_words / total_words * 30.0)
    return max(0.0, min(100.0, grade))

def format_issues(suggestions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format vocabulary issues for response"""
    return [
        {
            "type": "vocabulary",
            "word": s["original_word"],
            "word_type": s["word_type"],
            "level": s["level"],
            "context": s["context"],
            "examples": s["examples"]
        }
        for s in suggestions.values()
    ]
```

### 3. Analysis Webhook Integration

```python
# app/pubsub/webhooks/analysis_webhook.py
async def handle_question_analysis_ready_webhook(self, request: Request) -> Dict[str, str]:
    """Handle question ready for analysis webhook from Pub/Sub push
    
    PHASE 1: Run Grammar, Pronunciation, Lexical, and Vocabulary in PARALLEL
    """
    try:
        # ... existing initialization code ...
        
        # Initialize analysis state
        state = self._get_or_create_analysis_state(submission_url, question_number)
        state["wav_path"] = wav_path
        state["transcript"] = transcript
        state["audio_url"] = audio_url
        state["session_id"] = session_id
        state["total_questions"] = total_questions
        
        # Create tasks for parallel execution
        tasks = []
        
        # ... existing pronunciation, grammar, lexical tasks ...
        
        # 4. Vocabulary Analysis Task
        async def vocabulary_task():
            try:
                vocabulary_result = await analyze_vocabulary(transcript)
                state["vocabulary_result"] = vocabulary_result
                state["vocabulary_done"] = True
                
                # Publish vocabulary done
                self.pubsub_client.publish_message_by_name(
                    "VOCABULARY_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "total_questions": total_questions,
                        "result": vocabulary_result
                    }
                )
                logger.info(f"Vocabulary analysis completed for question {question_number}")
            except Exception as e:
                logger.error(f"Vocabulary analysis failed for question {question_number}: {str(e)}")
                state["vocabulary_result"] = {"error": str(e)}
                state["vocabulary_done"] = True
        
        # Add vocabulary task to parallel execution
        tasks.extend([pronunciation_task(), grammar_task(), lexical_task(), vocabulary_task()])
        
        # Run all Phase 1 tasks in parallel
        await asyncio.gather(*tasks)
        
        logger.info(f"PHASE 1 analysis completed for question {question_number}")
        return {"status": "success", "message": "Phase 1 analysis completed"}
```

## Implementation Steps

1. **Update Models**
   - Add `VocabularyDoneMessage` to `analysis_model.py`

2. **Implement Vocabulary Analysis**
   - Add vocabulary analysis task to parallel execution
   - Implement vocabulary analysis logic
   - Add vocabulary results to final analysis

3. **Testing**
   - Test vocabulary analysis in isolation
   - Test integration with analysis pipeline
   - Verify parallel execution

## Error Handling

1. **Service Errors**
   - Proper error responses
   - Error logging
   - Error tracking

2. **State Management**
   - Graceful failure handling
   - State recovery
   - Cleanup on completion

## Monitoring

1. **Logging**
   - Vocabulary analysis completion
   - Error tracking
   - Performance metrics

2. **Metrics**
   - Analysis duration
   - Success rate
   - Error rate 