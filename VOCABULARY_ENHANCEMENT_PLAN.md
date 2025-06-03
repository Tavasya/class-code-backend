# Vocabulary Enhancement Feature Plan

This document outlines the plan for implementing an enhanced vocabulary suggestion feature based on the Oxford 5000 word list and CEFR levels.

## 1. Goal

To provide users with targeted vocabulary suggestions by identifying words in their transcript that are present in the Oxford 5000 list and offering contextually appropriate alternatives that are one CEFR level higher, also from the Oxford 5000 list.

## 2. Core Principles

*   **Strict Adherence to Oxford 5000**: Both the original word identified in the transcript and the suggested alternative *must* be present in the provided Oxford 5000 JSON data with corresponding CEFR levels.
*   **Targeted CEFR Range**: The system will identify words in the user's transcript that are at A2, B1, or B2 CEFR levels according to the Oxford 5000 list.
*   **One Level Higher Progression**: Suggestions will aim to elevate the user's vocabulary by one CEFR level (e.g., A2 -> B1, B1 -> B2, B2 -> C1).
*   **Contextual Relevance**: Alternatives must be contextually appropriate for the sentence in which the original word appears. The AI model will be leveraged for this.
*   **No Fallbacks for Non-Oxford 5000 Words**: If a word (either original or potential alternative) is not in the Oxford 5000 list, it will not be part of this specific enhancement feature.
*   **Exclusion of A1 and C1**: Words at A1 and C1 levels will not be flagged for suggestions under this feature.

## 3. Data Requirements

*   **Oxford 5000 JSON**: A JSON file located at `app/assets/full-word.json`. This file contains a list of words, each with associated information including its CEFR level (e.g., "A1", "B2"). This file will be loaded into memory for efficient lookup.
    *   Expected structure per entry within the JSON list (assuming your `full-word.json` follows the structure you showed earlier, where each item has a "value" object containing word details):
        ```json
        {
            "id": 0, // Or any identifier
            "value": {
                "word": "example_word",
                "level": "A1",
                // ... other fields like phonetics, examples
            }
        }
        ```
*   **CEFR Level Progression**: A defined order and mapping for CEFR levels:
    *   A1 -> A2 (No longer a starting point for this feature)
    *   A2 -> B1
    *   B1 -> B2
    *   B2 -> C1
    *   C1 -> No higher suggestion from this progression.
    This mapping can be implemented as a simple dictionary. The core logic will focus on initiating suggestions for words at A2, B1, and B2.

## 4. Implementation Workflow

The core logic will reside primarily in `app/services/grammar_service.py`. Helper functions for loading data and lemmatization might be placed in a new utility file (e.g., `app/utils/vocabulary_utils.py`) or within `grammar_service.py` itself if they are not broadly reusable.

**Step 1: Load and Prepare Oxford 5000 Data (Application Startup)**

*   **File to Create/Modify**:
    *   **`app/utils/vocabulary_utils.py` (New or Existing)**: This file should house the data loading logic, the cache, NLP processor, and related helper functions.
    *   **`main.py` (or your FastAPI app's main entry point)**: To call the initialization function at startup.
*   **Implementation Detail**:
    1.  In `app/utils/vocabulary_utils.py`, define `load_oxford_data(file_path: str = "app/assets/full-word.json", nlp_processor) -> Dict[str, Dict[str, Any]]`. (Details as previously specified: load JSON, lemmatize keys, store level and original form).
    2.  Also in `app/utils/vocabulary_utils.py`, define global variables:
        *   `OXFORD_DATA_CACHE: Dict[str, Dict[str, Any]] = {}`
        *   `NLP_PROCESSOR: Any = None`
        *   `CEFR_PROGRESSION_MAP: Dict[str, str] = {"A2": "B1", "B1": "B2", "B2": "C1"}`
    3.  In `app/utils/vocabulary_utils.py`, define `initialize_vocabulary_tools()`:
        ```python
        # In app/utils/vocabulary_utils.py
        # import spacy # Assuming spaCy
        
        # OXFORD_DATA_CACHE, NLP_PROCESSOR, CEFR_PROGRESSION_MAP defined above

        # def load_oxford_data(...): ...
        # def get_lemma(...): ... # (Covered in Step 2)

        def initialize_vocabulary_tools(oxford_json_path: str = "app/assets/full-word.json"):
            global NLP_PROCESSOR, OXFORD_DATA_CACHE
            if NLP_PROCESSOR is None: # Ensure it's initialized only once
                NLP_PROCESSOR = spacy.load("en_core_web_sm") # Or your chosen library
            
            if not OXFORD_DATA_CACHE: # Ensure it's loaded only once
                OXFORD_DATA_CACHE = load_oxford_data(file_path=oxford_json_path, nlp_processor=NLP_PROCESSOR)
            
            if not NLP_PROCESSOR or not OXFORD_DATA_CACHE:
                # Log error appropriately
                raise RuntimeError("Failed to initialize essential vocabulary tools.")
        ```
    4.  **Application Startup Call**: In your main application file (e.g., `main.py` if using FastAPI), ensure `initialize_vocabulary_tools()` is called during the startup sequence.
        ```python
        # Example for FastAPI in main.py
        # from fastapi import FastAPI
        # from app.utils.vocabulary_utils import initialize_vocabulary_tools

        # app = FastAPI()

        # @app.on_event("startup")
        # async def startup_event():
        #     initialize_vocabulary_tools()
        #     # Other startup tasks...
        ```
    5.  The `oxford_word_data_cache` and `CEFR_PROGRESSION_MAP` will be imported and used by `app/services/grammar_service.py`.

**Step 2: Lemmatization Setup**

*   **File to Modify/Consider**: `app/services/grammar_service.py` or `app/utils/vocabulary_utils.py`.
*   **Necessity**: Lemmatization is essential to standardize words. For instance, "running", "ran", and "runs" all need to be converted to their base form "run" to reliably match against the Oxford 5000 list (which typically stores lemmas) and to process AI-suggested alternatives consistently.
*   **Implementation Detail**:
    1.  Choose a lemmatization library (e.g., `spaCy` or `NLTK`). Add it to `requirements.txt`.
        *   If using `spaCy`: `spacy>=3.0.0,<4.0.0`. Remember to download the model: `python -m spacy download en_core_web_sm`.
    2.  Initialize the lemmatizer. For `spaCy`, this involves loading a language model (e.g., `nlp_processor = spacy.load("en_core_web_sm")`). This should ideally happen once at application startup (see `initialize_vocabulary_tools`).
    3.  Create a helper function `get_lemma(text: str, nlp_processor) -> str` that takes a word and returns its lowercase lemma.
        *   Example using `spaCy`:
            ```python
            # Assume nlp_processor is the loaded spaCy model
            # import spacy # At the top of your file
            # NLP_PROCESSOR = spacy.load("en_core_web_sm") # Loaded once

            def get_lemma(word_text: str, nlp_processor_instance) -> str:
                doc = nlp_processor_instance(word_text.lower())
                if doc and len(doc) > 0:
                    return doc[0].lemma_
                return word_text.lower() # Fallback for empty or unlemmatizable input
            ```
        *   This function will be used to process words from the user's transcript and words suggested by the AI before checking against the `oxford_word_data_cache`.

**Step 3: Process User Transcript (within `suggest_vocabulary` or a precursor function)**

*   **File to Modify**: `app/services/grammar_service.py` (likely inside the revamped `suggest_vocabulary` function).
*   **Input**: List of sentences (already available from `split_into_sentences`).
*   **Implementation Detail**:
    1.  Iterate through each sentence (`sentence_text` at `sentence_idx`).
    2.  Tokenize the `sentence_text` into individual words. Preserve original word form for context but use lemmas for lookups.
    3.  For each word in the sentence (at `word_idx`):
        a.  Obtain its lemma using `get_lemma()`.
        b.  This lemma is the `transcript_word_lemma`.

**Step 4: Identify Candidate Words from Transcript (within `suggest_vocabulary`)**

*   **File to Modify**: `app/services/grammar_service.py`.
*   **Input**: `transcript_word_lemma`, `oxford_word_data_cache`, `CEFR_PROGRESSION`.
*   **Implementation Detail**:
    1.  For each `transcript_word_lemma` from Step 3:
        a.  Check if `transcript_word_lemma` exists as a key in `oxford_word_data_cache`.
        b.  If it exists:
            i.  `original_word_data = oxford_word_data_cache[transcript_word_lemma]`
            ii. `original_level = original_word_data['level']`
            iii. If `original_level` is not one of "A2", "B1", or "B2" (or not in `CEFR_PROGRESSION` as a key, or its value is "C1"), skip this word. This ensures we only target words within the A2-B2 range for uplift.
            iv. Otherwise, this `transcript_word_lemma` (along with its original non-lemmatized form, `sentence_text`, `sentence_idx`, `word_idx`, and `original_level`) becomes an "original candidate."

**Step 5: Generate and Filter Suggestions for Each Candidate Word (within `suggest_vocabulary`)**

*   **File to Modify**: `app/services/grammar_service.py`.
*   **Input**: Each "original candidate" (containing original word, context, sentence_idx, original_level), `oxford_word_data_cache`, `CEFR_PROGRESSION`, `nlp` (for lemmatization).
*   **Implementation Detail**:
    1.  For each "original candidate":
        a.  **Determine Target CEFR Level**: `target_level = CEFR_PROGRESSION[original_level]`.
        b.  **AI-Powered Alternative Generation**:
            i.  Original word for prompt: `original_candidate['original_form']` (This is the non-lemmatized form from the transcript).
            ii. Sentence for context: `original_candidate['sentence_text']`.
            iii. Construct prompt for `call_openai_with_retry`: "Suggest 3-5 contextually appropriate single-word alternatives for the word '{original_word_for_prompt}' in the sentence: '{sentence_text}'. Provide only a JSON list of single-word strings." (Requesting a specific number like 3-5 helps, expected format: `["word1", "word2", ...]` ).
            iv. Let `ai_alternatives_list` be the list of words returned by the AI. Handle cases where AI might not return a valid list (e.g., empty list, malformed response).
        c.  **Filter AI Alternatives**:
            i.  `valid_suggestions_for_candidate = []`
            ii. For each `alt_word_from_ai` in `ai_alternatives_list`:
                1.  `alt_lemma = get_lemma(alt_word_from_ai, nlp)`. (Ensure `alt_word_from_ai` is treated as a single word for lemmatization).
                2.  Check if `alt_lemma` exists as a key in `oxford_word_data_cache`.
                3.  If it exists:
                    *   `alt_word_data = oxford_word_data_cache[alt_lemma]`
                    *   `alternative_actual_level = alt_word_data['level']`
                    *   If `alternative_actual_level == target_level`:
                        *   Add `alt_lemma` (the lemmatized form of the AI suggestion) to `valid_suggestions_for_candidate`. Avoid duplicates.
        d.  If `valid_suggestions_for_candidate` is not empty, store it along with the original candidate's details.

**Step 6: Format and Present Suggestions (final part of `suggest_vocabulary`)**

*   **File to Modify**: `app/services/grammar_service.py`.
*   **Implementation Detail**:
    1.  The `suggest_vocabulary` function will now return a structure similar to `List[List[Dict[str, Any]]]`, where the outer list corresponds to sentences, and the inner list contains vocabulary suggestion dictionaries for words in that sentence.
    2.  Each suggestion dictionary should conform to the `VocabularySuggestion` model in `app/models/grammar_model.py`. Ensure the model has a field (e.g., `context` or `sentence_text`) that can store the full sentence.
        *   `original_word`: The original non-lemmatized word from the transcript (`original_candidate['original_form']`).
        *   `context` (or `sentence_text` - use the exact field name from `VocabularySuggestion` model): The full `sentence_text` (`original_candidate['sentence_text']`).
        *   `advanced_alternatives`: The list of `valid_suggestions_for_candidate` (these are lemmas).
        *   `level`: The `target_level`.
        *   `sentence_index`: `original_candidate['sentence_idx']`.
        *   `phrase_index`: This should be `original_candidate['word_idx']`, representing the 0-based index of the original word within its tokenized sentence.
    3.  **Apply Limiting Heuristics**:
        *   Before finalizing, apply rules like "max N suggestions per sentence" or "total M suggestions per transcript." These thresholds (N, M) should ideally be configurable (e.g., via environment variables or a config file) rather than hardcoded.

## 5. How it Works (User Perspective)

1.  The user provides a transcript.
2.  The system analyzes the transcript.
3.  For words the user has used that are part of the Oxford 5000 and are at CEFR levels A2, B1, or B2:
    *   The system identifies these words.
    *   It then searches for contextually fitting alternative words from the Oxford 5000 list that are exactly one CEFR level higher than the word the user originally wrote (i.e., A2->B1, B1->B2, B2->C1).
4.  The user receives vocabulary suggestions that are:
    *   Directly related to words they used.
    *   Contextually appropriate.
    *   Sourced from a standard vocabulary list (Oxford 5000).
    *   Aimed at helping them incrementally improve their vocabulary by one CEFR level at a time.
    *   If no suitable "one level higher" alternatives are found in the Oxford 5000 for a given word, no suggestion will be made for that word.

## 6. Modifications to Existing Code

This section details specific changes and their locations.

**A. New Utility Components (Strongly Recommended in `app/utils/vocabulary_utils.py`)**

Create `app/utils/vocabulary_utils.py` if it doesn't exist. This file will consolidate vocabulary-specific logic.

1.  **Oxford 5000 Data Loader and Global Variables**:
    *   **File**: `app/utils/vocabulary_utils.py`
    *   **Variables**:
        *   `OXFORD_DATA_CACHE: Dict[str, Dict[str, Any]] = {}`
        *   `NLP_PROCESSOR: Any = None`
        *   `CEFR_PROGRESSION_MAP: Dict[str, str] = {"A2": "B1", "B1": "B2", "B2": "C1"}`
    *   **Function**: `load_oxford_data(file_path: str = "app/assets/full-word.json", nlp_processor) -> Dict[str, Dict[str, Any]]`
        *   **Purpose**: Loads `full-word.json`, lemmatizes keys using `nlp_processor`, and stores word details (level, original form).
    *   **Initialization Function**: `initialize_vocabulary_tools()`
        *   **File**: `app/utils/vocabulary_utils.py`
        *   **Purpose**: Initializes `NLP_PROCESSOR` and calls `load_oxford_data` to populate `OXFORD_DATA_CACHE`.
        *   **Called From**: Application startup sequence (e.g., in `main.py` for FastAPI, as shown in Section 4, Step 1).

2.  **Lemmatization Function**:
    *   **File**: `app/utils/vocabulary_utils.py`
    *   **Function**: `get_lemma(word_text: str, nlp_processor_instance) -> str`
    *   **Purpose**: Takes a single word and the initialized `NLP_PROCESSOR`, returns its lowercase lemma. (Details as previously specified).

**B. `app/services/grammar_service.py` Modifications**

1.  **Imports and Reliance on Utilities**:
    *   `app/services/grammar_service.py` will now import necessary components from `app/utils/vocabulary_utils.py`:
        ```python
        # At the top of app/services/grammar_service.py
        # from app.utils.vocabulary_utils import get_lemma, OXFORD_DATA_CACHE, NLP_PROCESSOR, CEFR_PROGRESSION_MAP
        # from app.models.grammar_model import VocabularySuggestion # Assuming this path
        # import other necessary modules like call_openai_with_retry
        ```
    *   It no longer needs to define these globals itself. The `initialize_vocabulary_tools()` ensures they are ready.

2.  **`suggest_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]` function (Major Refactor)**:
    *   **File**: `app/services/grammar_service.py`
    *   **Inputs**: `sentences: List[str]`. Implicitly uses imported `OXFORD_DATA_CACHE`, `NLP_PROCESSOR`, `CEFR_PROGRESSION_MAP`, and `get_lemma` from `app/utils/vocabulary_utils.py`.
    *   **Return Type**: `List[List[VocabularySuggestion]]` (using the actual model type).
    *   **Remove Old Logic**: The current OpenAI call that asks for general B1/B2 enhancements will be completely removed and replaced by the logic below.
    *   **New Workflow Integration**:
        1.  Initialize `all_vocab_suggestions: List[List[VocabularySuggestion]] = [[] for _ in sentences]`.
        2.  Iterate `sentence_idx, sentence_text` from `enumerate(sentences)`.
        3.  Tokenize `sentence_text` into words. A simple `tokenized_words = sentence_text.split()` can be a starting point. For more advanced tokenization that aligns with `spaCy` (if used for lemmatization), you might process the sentence: `doc = NLP_PROCESSOR(sentence_text); tokenized_words = [token.text for token in doc]`. Choose a consistent method. Store these original word forms.
        4.  For each `original_word_form` at `word_idx` in `enumerate(tokenized_words)`:
            a.  `transcript_word_lemma = get_lemma(original_word_form, NLP_PROCESSOR)`. Keep `original_word_form` for the suggestion output.
            b.  **Identify Candidate (Step 4 from Workflow)**:
                *   If `transcript_word_lemma` in `OXFORD_DATA_CACHE`:
                    *   `original_word_cache_data = OXFORD_DATA_CACHE[transcript_word_lemma]`
                    *   `original_level = original_word_cache_data['level']`.
                    *   If `original_level` in ["A2", "B1", "B2"] and `original_level` in `CEFR_PROGRESSION_MAP`:
                        *   `target_level = CEFR_PROGRESSION_MAP[original_level]`.
                        *   An "original candidate" is identified: `original_form=original_word_form`, `sentence_text=sentence_text`, `sentence_idx=sentence_idx`, `word_idx=word_idx`, `original_level=original_level`.
            c.  **Generate & Filter Suggestions (Step 5 from Workflow)**:
                *   If an "original candidate" is identified:
                    *   Call `call_openai_with_retry` ... (details as before) ... to get `ai_alternatives_list`. 
                    *   `filtered_advanced_alternatives = []`.
                    *   For `alt_word_from_ai` in `ai_alternatives_list`:
                        *   `alt_lemma = get_lemma(alt_word_from_ai, NLP_PROCESSOR)`.
                        *   If `alt_lemma` in `OXFORD_DATA_CACHE` and `OXFORD_DATA_CACHE[alt_lemma]['level'] == target_level`:
                            *   If `alt_lemma` not already in `filtered_advanced_alternatives`:
                                *   `filtered_advanced_alternatives.append(alt_lemma)`.
                    *   If `filtered_advanced_alternatives` is not empty:
                        *   Construct the `VocabularySuggestion` object (ensure field names match your model in `app/models/grammar_model.py`):
                            ```python
                            suggestion = VocabularySuggestion(
                                original_word=original_candidate['original_form'],
                                context=original_candidate['sentence_text'], # Or sentence_text if that's the model field
                                advanced_alternatives=filtered_advanced_alternatives,
                                level=target_level,
                                sentence_index=original_candidate['sentence_idx'],
                                phrase_index=original_candidate['word_idx']
                                # sentence_text field might be redundant if 'context' stores the full sentence
                            )
                            ```
                        *   `all_vocab_suggestions[sentence_idx].append(suggestion)`.
        5.  **(Crucial) Apply Limiting Heuristics**: ... (details as before) ...
        6.  Return `all_vocab_suggestions`.

**C. `app/models/grammar_model.py`**

*   **File**: `app/models/grammar_model.py`
*   **`VocabularySuggestion` Model**: 
    *   Verify that this Pydantic (or similar) model has a field to store the full sentence context (e.g., `context: str` or `sentence_text: str`