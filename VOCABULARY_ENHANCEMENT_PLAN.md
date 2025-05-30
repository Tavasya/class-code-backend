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

*   **File to Modify/Create**:
    *   Potentially `app/core/config.py` or a new `app/utils/vocabulary_utils.py` for loading, or directly in `app/services/grammar_service.py` if initialized globally or passed around.
*   **Implementation Detail**:
    1.  Define a function, let's call it `load_oxford_data(file_path: str = "app/assets/full-word.json") -> Dict[str, Dict[str, Any]]`.
    2.  This function will:
        a.  Open and read the JSON file specified by `file_path`.
        b.  Parse the JSON (which is a list of objects).
        c.  Iterate through the list. For each item, extract the `value.word` (lemmatized and lowercased) as the key and the `value` object (or just `value.level`) as the value for an in-memory dictionary.
            *   Example: `oxford_word_data_cache = {}`
            *   For each `entry` in `json_data_list`:
                *   `word = entry['value']['word'].lower()` (Consider if lemmatization is needed here if words in JSON aren't already lemmas. Assuming they are for now.)
                *   `level = entry['value']['level']`
                *   `oxford_word_data_cache[word] = {"level": level, ...other_details_if_needed}`
    3.  This `oxford_word_data_cache` dictionary should be loaded once when the application starts and made accessible to the `grammar_service`. This could be a global variable in the service module or passed as a dependency.
    4.  Define the CEFR progression map: `CEFR_PROGRESSION = {"A2": "B1", "B1": "B2", "B2": "C1"}`.

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
            i.  Original word for prompt: `original_candidate['original_form']`.
            ii. Sentence for context: `original_candidate['sentence_text']`.
            iii. Construct prompt for `call_openai_with_retry`: "Suggest a few contextually appropriate single-word alternatives for the word '{original_word_for_prompt}' in the sentence: '{sentence_text}'. Provide only a list of words." (Expected format: JSON list of strings).
            iv. Let `ai_alternatives_list` be the list of words returned by the AI.
        c.  **Filter AI Alternatives**:
            i.  `valid_suggestions_for_candidate = []`
            ii. For each `alt_word_from_ai` in `ai_alternatives_list`:
                1.  `alt_lemma = get_lemma(alt_word_from_ai, nlp)`.
                2.  Check if `alt_lemma` exists as a key in `oxford_word_data_cache`.
                3.  If it exists:
                    *   `alt_word_data = oxford_word_data_cache[alt_lemma]`
                    *   `alternative_actual_level = alt_word_data['level']`
                    *   If `alternative_actual_level == target_level`:
                        *   Add `alt_lemma` (or `alt_word_from_ai` if you want to preserve AI's casing/form if it varies from lemma) to `valid_suggestions_for_candidate`.
        d.  If `valid_suggestions_for_candidate` is not empty, store it along with the original candidate's details.

**Step 6: Format and Present Suggestions (final part of `suggest_vocabulary`)**

*   **File to Modify**: `app/services/grammar_service.py`.
*   **Implementation Detail**:
    1.  The `suggest_vocabulary` function will now return a structure similar to `List[List[Dict[str, Any]]]`, where the outer list corresponds to sentences, and the inner list contains vocabulary suggestion dictionaries for words in that sentence.
    2.  Each suggestion dictionary should conform to the `VocabularySuggestion` model in `app/models/grammer_model.py`.
        *   `original_word`: The original non-lemmatized word from the transcript.
        *   `context`: The `sentence_text`.
        *   `advanced_alternatives`: The list of `valid_suggestions_for_candidate` (lemmas or AI's form).
        *   `level`: The `target_level`.
        *   `sentence_index`: `original_candidate['sentence_idx']`.
        *   `phrase_index`: `original_candidate['word_idx']` (or a similar index tracking distinct words if needed, as per current `enhance_vocabulary_suggestions_with_context`). Consider if the existing `phrase_index` logic for multiple occurrences of the *same* original word needs to be adapted.
        *   `sentence_text`: `original_candidate['sentence_text']`.
    3.  **Apply Limiting Heuristics**:
        *   Before finalizing, apply rules like "max N suggestions per sentence" or "total M suggestions per transcript." This might involve sorting candidates (e.g., by lowest original CEFR level) and picking the top N/M.

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

**A. New Utility Components (Consider `app/utils/vocabulary_utils.py` or within `grammar_service.py`)**

1.  **Oxford 5000 Data Loader**:
    *   **Function**: `load_oxford_data(file_path: str = "app/assets/full-word.json") -> Dict[str, Dict[str, Any]]`
    *   **Purpose**: Loads `full-word.json`, parses it, and transforms it into a dictionary mapping lowercased, lemmatized words to their details (especially 'level').
    *   **Initialization**: Called once at application startup. The resulting dictionary is stored globally or passed as a dependency.
    *   **Global Variable Example (in `grammar_service.py` or `vocabulary_utils.py`)**:
        ```python
        # At the top of the file
        OXFORD_DATA_CACHE: Dict[str, Dict[str, Any]] = {}
        NLP_PROCESSOR: Any = None # spaCy model
        CEFR_PROGRESSION_MAP: Dict[str, str] = {"A2": "B1", "B1": "B2", "B2": "C1"}

        def initialize_vocabulary_tools():
            global OXFORD_DATA_CACHE, NLP_PROCESSOR
            # OXFORD_DATA_CACHE = load_oxford_data() # Implement load_oxford_data
            # NLP_PROCESSOR = spacy.load("en_core_web_sm") # Or your chosen library
            pass # Actual implementation
        ```
        *Call `initialize_vocabulary_tools()` when the FastAPI app starts.*

2.  **Lemmatization Function**:
    *   **Function**: `get_lemma(word_text: str, nlp_processor_instance) -> str` (Note: `nlp_processor_instance` is the loaded spaCy model, e.g., `NLP_PROCESSOR`)
    *   **Purpose**: Takes a single word string and the initialized NLP processor (e.g., spaCy model), returns its lowercase lemma. Essential for standardizing words from the transcript and AI suggestions before dictionary lookups.
    *   **Usage**: Called repeatedly. Example implementation (if using spaCy):
        ```python
        # Ensure spaCy is imported, e.g., import spacy
        # And NLP_PROCESSOR is loaded globally, e.g.,
        # NLP_PROCESSOR = spacy.load("en_core_web_sm")

        def get_lemma(word_text: str, nlp_processor_instance) -> str:
            doc = nlp_processor_instance(word_text.lower())
            if doc and len(doc) > 0:
                return doc[0].lemma_
            return word_text.lower() # Fallback for empty or unlemmatizable input
        ```
    *   **Consideration**: Ensure the `nlp_processor_instance` passed to this function is the globally initialized one to avoid reloading the model on each call.

**B. `app/services/grammar_service.py` Modifications**

1.  **Global Variables/Initialization**:
    *   Store the loaded `OXFORD_DATA_CACHE`, `NLP_PROCESSOR`, and `CEFR_PROGRESSION_MAP` so they are accessible by `suggest_vocabulary`.
    *   Ensure `initialize_vocabulary_tools()` is called.

2.  **`suggest_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]` function (Major Refactor)**:
    *   **Inputs**: Will now implicitly use `OXFORD_DATA_CACHE`, `NLP_PROCESSOR`, and `CEFR_PROGRESSION_MAP`.
    *   **Remove Old Logic**: The current OpenAI call that asks for general B1/B2 enhancements will be replaced.
    *   **New Workflow Integration**:
        1.  Initialize `all_vocab_suggestions = [[] for _ in sentences]`.
        2.  Iterate `sentence_idx, sentence_text` from `enumerate(sentences)`.
        3.  Tokenize `sentence_text` into words (with their original index/position in the sentence for `phrase_index`).
        4.  For each `original_word_form` at `word_idx` in the tokenized sentence:
            a.  `transcript_word_lemma = get_lemma(original_word_form, NLP_PROCESSOR)`.
            b.  **Identify Candidate (Step 4 from Workflow)**:
                *   If `transcript_word_lemma` in `OXFORD_DATA_CACHE`:
                    *   `original_level = OXFORD_DATA_CACHE[transcript_word_lemma]['level']`.
                    *   If `original_level` in ["A2", "B1", "B2"] and `original_level` in `CEFR_PROGRESSION_MAP`:
                        *   `target_level = CEFR_PROGRESSION_MAP[original_level]`.
                        *   This becomes an "original candidate."
            c.  **Generate & Filter Suggestions (Step 5 from Workflow)**:
                *   If an "original candidate" is identified:
                    *   Call `call_openai_with_retry` with the new prompt (see Workflow Step 5.b.iii) to get `ai_alternatives_list`.
                    *   `filtered_advanced_alternatives = []`.
                    *   For `alt_word_from_ai` in `ai_alternatives_list`:
                        *   `alt_lemma = get_lemma(alt_word_from_ai, NLP_PROCESSOR)`.
                        *   If `alt_lemma` in `OXFORD_DATA_CACHE` and `OXFORD_DATA_CACHE[alt_lemma]['level'] == target_level`:
                            *   `filtered_advanced_alternatives.append(alt_lemma)` (or `alt_word_from_ai`).
                    *   If `filtered_advanced_alternatives` is not empty:
                        *   Construct the `VocabularySuggestion` dictionary (see Workflow Step 6.2).
                        *   `all_vocab_suggestions[sentence_idx].append(suggestion_dict)`.
        5.  **(Crucial) Apply Limiting Heuristics**: Before returning, prune `all_vocab_suggestions` based on rules like max suggestions per sentence/transcript. This might involve sorting and slicing.
        6.  Return `all_vocab_suggestions`.

3.  **`enhance_vocabulary_suggestions_with_context` function**:
    *   May still be useful if the `phrase_index` logic needs to be more sophisticated than just the word's position, especially if the same word appears multiple times and each instance is treated as a separate candidate. Review if its current logic is directly applicable or needs adjustment based on how candidates are identified and stored. The `suggest_vocabulary` refactor should aim to populate most fields directly.

4.  **`analyze_grammar(transcript: str) -> Dict[str, Any]` function**:
    *   **Initialization Call**: Ensure `initialize_vocabulary_tools()` has been run if not handled at app startup.
    *   **`vocab_candidate_sentences` logic**: This will likely be removed or completely rethought. The new `suggest_vocabulary` operates on all sentences and filters based on Oxford 5000 presence.
    *   The call to `suggest_vocabulary` will remain, but its output will now be based on the new Oxford 5000 driven logic.
    *   The formatting of `vocab_issues` and `vocabulary_suggestions_dict` will largely remain the same, as the `VocabularySuggestion` model structure is preserved.

**C. `app/models/grammer_model.py`**

*   No changes expected to `VocabularySuggestion` model itself, as the new logic will populate the existing fields.

**D. `app/requirements.txt`**

*   Add the chosen lemmatization library (e.g., `spacy` and the specific model like `en_core_web_sm`).
    *   Example:
        ```
        spacy>=3.0.0,<4.0.0
        # If using spaCy, also remind to download the model:
        # python -m spacy download en_core_web_sm
        ```

## 7. Potential Challenges & Mitigation

*   **Lemmatization Accuracy**: Mismatches due to imperfect lemmatization.
    *   *Mitigation*: Use a robust lemmatization library (e.g., spaCy is generally very good).
*   **Contextual Fit of AI Alternatives**: AI might suggest alternatives that are at the right level but don't perfectly fit the nuance.
    *   *Mitigation*: The prompt to the AI is key. Emphasize contextual fit. The strict filtering by Oxford 5000 at the target level will also help.
*   **Limited Number of Suggestions**: The strict filtering, now focused on words starting at A2, B1, or B2, might result in few suggestions.
    *   *Mitigation*: This is an accepted trade-off for quality and adherence to the Oxford 5000. Ensure the AI is prompted to provide a decent number of initial alternatives to increase the chances of a match.
*   **Overwhelming Users**: If too many words in a sentence are from Oxford 5000 B1/B2 (previously A1/A2).
    *   *Mitigation*: Implement the limiting heuristics mentioned in Step 5 of the workflow.

This plan provides a clear path forward for enhancing the vocabulary suggestion feature with a strong pedagogical basis. 