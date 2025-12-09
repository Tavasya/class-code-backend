import re
import logging
import json
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY
from app.services.openai_client import get_openai_client
from app.models.vocabulary_model import VocabularySuggestion, VocabularyFeedback
from app.utils.vocabulary_utils import vocabulary_tools

# Setup logging
logger = logging.getLogger(__name__)

# Vocabulary debug log file
VOCAB_LOG_FILE = "/tmp/vocabulary_debug.log"

def vocab_log(message: str, question_number: int = None):
    """Log vocabulary messages to separate file for easy debugging"""
    try:
        timestamp = datetime.now().strftime("%H:%M:%S")
        q_prefix = f"Q{question_number} | " if question_number else ""
        with open(VOCAB_LOG_FILE, 'a') as f:
            f.write(f"{timestamp} | {q_prefix}{message}\n")
        # Also log to regular logger
        logger.info(f"{q_prefix}{message}")
    except Exception:
        # Fallback to regular logger only
        logger.info(f"{q_prefix if question_number else ''}{message}")

def init_vocab_log():
    """Initialize vocabulary log file for new session"""
    try:
        with open(VOCAB_LOG_FILE, 'w') as f:
            f.write(f"=== VOCABULARY DEBUG LOG - {datetime.now().isoformat()} ===\n")
    except Exception:
        pass

# Version 3: Collocation-based vocabulary analysis with categorization (similar to grammar service)
# Previous v2: CEFR-based vocabulary analysis (legacy, commented out)
MODEL = "gpt-5-nano"

# Batch size for processing multiple sentences in one API call
VOCABULARY_BATCH_SIZE = 5

async def call_openai_with_retry(prompt: str, expected_format: str = "list", max_retries: int = 2) -> Any:
    """Call OpenAI API with retry mechanism for format validation"""
    if not OPENAI_API_KEY:
        logger.warning("No API key available, cannot make API call")
        return None

    current_prompt = prompt
    client = get_openai_client()

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                format_emphasis = f"""
                IMPORTANT: Your previous response was not in the expected JSON format.
                You MUST ONLY return a valid JSON {expected_format} without any explanation text, markdown formatting, or code blocks.
                DO NOT include ```json or ``` markers.
                ONLY return the raw JSON {expected_format}.
                """
                current_prompt = format_emphasis + "\n\n" + prompt

            result = await client.chat(MODEL, [{"role": "user", "content": current_prompt}])
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            try:
                parsed_content = json.loads(content)
                if (expected_format == "list" and isinstance(parsed_content, list)) or \
                   (expected_format == "dict" and isinstance(parsed_content, dict)):
                    return parsed_content
            except json.JSONDecodeError:
                if attempt == max_retries:
                    return None

        except Exception as e:
            logger.warning(f"Error in API call (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries:
                logger.error(f"Max retries reached for API call: {str(e)}")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return None

# LEGACY CEFR-based vocabulary analysis - commented out for collocation approach
# def create_vocabulary_prompt_for_single_sentence(sentence: str) -> str:
#     """Create optimized prompt for single sentence vocabulary analysis"""
#     return f"""
# You are an expert in English vocabulary analysis specializing in CEFR levels and word usage.
# 
# Analyze this sentence for vocabulary improvement opportunities: "{sentence}"
# 
# Identify:
# 1. Basic level words (A1-A2) that could be replaced with more advanced vocabulary
# 2. Words that are used in an incorrect or unnatural context
# 3. Opportunities to use more sophisticated vocabulary, even if the current word is already advanced
# 
# IMPORTANT: When suggesting replacements, you MUST follow this progression:
# - For A1 words, suggest ONLY A2 alternatives
# - For A2 words, suggest ONLY B1 alternatives
# - For B1 words, suggest ONLY B2 alternatives
# - For B2 words, suggest ONLY C1 alternatives
# 
# Never skip levels in your suggestions. Each suggestion should be exactly one level higher than the original word.
# 
# For each issue identified, provide:
# - The original word
# - A suggested replacement word
# - The CEFR level of both words
# - A brief explanation of why the change would improve the text
# - Example usage of the suggested word
# 
# Present the results in JSON format:
# [
#     {{
#         "original_word": "[word_from_text]",
#         "suggested_word": "[better_alternative]",
#         "original_level": "[CEFR_level]",
#         "suggested_level": "[higher_CEFR_level]",
#         "explanation": "[reason_for_improvement]",
#         "examples": ["[example_sentence_with_suggested_word]"]
#     }}
# ]
# 
# ONLY analyze the actual words present in the sentence provided above. Do not suggest changes for words that are not in the text.
# 
# Return ONLY the JSON array. No other text or markdown formatting.
# """

def create_vocabulary_prompt_for_single_sentence(sentence: str) -> str:
    """Create optimized prompt for single sentence collocation analysis"""
    return f"""
You are an expert in English vocabulary and collocation analysis. Analyze the following sentence for incorrect word usage and poor word choices on a word-by-word basis. If you chose a word in a sentence you dont need to choose it again.

Sentence: "{sentence}"

Your job is to identify words that are:
1. Used incorrectly in context (wrong word choice)
2. Poor collocations (words that don't naturally go together)
3. Unnatural or awkward word selections
4. Misspelled or malformed words
5. Words that could be replaced with more appropriate alternatives
6. Vocabulary that doesn't fit the register or style
7. Words used in wrong grammatical contexts
8. Redundant or unnecessary words
9. Missing words that would improve collocations
10. Other vocabulary issues

IMPORTANT: Focus on individual words and their immediate context. Analyze each word for appropriateness, correctness, and natural usage.

For each issue identified, provide:
- The problematic word
- A suggested replacement word
- The category number (1-10 from above)
- A brief explanation of the issue
- Example usage of the correct word

Present the results in JSON format:
[
    {{
        "type": "vocabulary",
        "category": [category_number],
        "original_word": "[problematic_word]",
        "suggested_word": "[better_alternative]",
        "explanation": "[reason_for_improvement]",
        "examples": ["[example_with_suggested_word]"]
    }}
]

ONLY analyze words that are actually present in the sentence. Return ONLY the JSON array.
"""

def create_vocabulary_prompt_for_batch(sentences: List[str], start_index: int) -> str:
    """Create prompt for analyzing a batch of sentences for vocabulary"""
    sentences_text = ""
    for i, sentence in enumerate(sentences):
        sentences_text += f"\n{start_index + i + 1}. {sentence}"

    return f"""
You are an expert in English vocabulary and collocation analysis. Analyze the following sentences for incorrect word usage and poor word choices.

Your job is to identify words that are:
1. Used incorrectly in context (wrong word choice)
2. Poor collocations (words that don't naturally go together)
3. Unnatural or awkward word selections
4. Misspelled or malformed words
5. Words that could be replaced with more appropriate alternatives
6. Vocabulary that doesn't fit the register or style
7. Words used in wrong grammatical contexts
8. Redundant or unnecessary words
9. Missing words that would improve collocations
10. Other vocabulary issues

IMPORTANT: Focus on individual words and their immediate context. Analyze each word for appropriateness, correctness, and natural usage.

Sentences to analyze:{sentences_text}

Provide suggestions as a JSON array of arrays. Each inner array contains suggestions for the corresponding sentence (by order). If a sentence has no issues, use an empty array.

Output format:
[
    [  // suggestions for sentence {start_index + 1}
        {{
            "type": "vocabulary",
            "category": [category_number],
            "original_word": "[problematic_word]",
            "suggested_word": "[better_alternative]",
            "explanation": "[reason_for_improvement]",
            "examples": ["[example_with_suggested_word]"]
        }}
    ],
    [],  // sentence {start_index + 2}: no suggestions
    ...
]

ONLY analyze words that are actually present in the sentences. Return ONLY the JSON array with exactly {len(sentences)} inner arrays. No other text or markdown formatting.
"""

async def analyze_single_sentence_vocabulary(sentence: str, sentence_idx: int) -> Dict[str, Any]:
    """Analyze vocabulary collocations for a single sentence (fallback for batch failures)"""
    vocab_log(f"🔍 VOCAB: Analyzing sentence {sentence_idx} (len: {len(sentence)})")

    if not sentence or not sentence.strip():
        vocab_log(f"🔍 VOCAB: Empty sentence {sentence_idx}, skipping")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": True
        }

    try:
        prompt = create_vocabulary_prompt_for_single_sentence(sentence)

        # Add timeout protection for individual sentence analysis
        try:
            result = await asyncio.wait_for(
                call_openai_with_retry(prompt, expected_format="list", max_retries=1),
                timeout=30.0
            )
            vocab_log(f"✅ VOCAB: Sentence {sentence_idx} API call completed")
        except asyncio.TimeoutError:
            vocab_log(f"⚠️ VOCAB: Sentence {sentence_idx} timed out after 30s")
            return {
                "sentence_idx": sentence_idx,
                "sentence": sentence,
                "suggestions": [],
                "success": False,
                "error": "timeout"
            }

        suggestions = []
        if result and isinstance(result, list):
            for suggestion in result:
                if isinstance(suggestion, dict) and all(k in suggestion for k in ["type", "category", "original_word", "suggested_word", "explanation", "examples"]):
                    suggestions.append(suggestion)

        vocab_log(f"✅ VOCAB: Sentence {sentence_idx} completed with {len(suggestions)} suggestions")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": suggestions,
            "success": result is not None
        }

    except Exception as e:
        vocab_log(f"💥 VOCAB: Error analyzing sentence {sentence_idx}: {str(e)[:100]}")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": False,
            "error": str(e)
        }

async def analyze_batch_vocabulary(sentences: List[str], start_index: int, question_number: int = None) -> List[Dict[str, Any]]:
    """Analyze vocabulary for a batch of sentences in a single API call"""
    vocab_log(f"🔍 VOCAB: Analyzing batch of {len(sentences)} sentences starting at index {start_index}", question_number)

    if not sentences:
        return []

    # Filter out empty sentences but track their positions
    non_empty_indices = []
    non_empty_sentences = []
    for i, sentence in enumerate(sentences):
        if sentence and sentence.strip():
            non_empty_indices.append(i)
            non_empty_sentences.append(sentence)

    # If all sentences are empty, return empty results
    if not non_empty_sentences:
        return [{"sentence_idx": start_index + i, "sentence": s, "suggestions": [], "success": True} for i, s in enumerate(sentences)]

    try:
        prompt = create_vocabulary_prompt_for_batch(non_empty_sentences, start_index)

        # Add timeout protection
        try:
            result = await asyncio.wait_for(
                call_openai_with_retry(prompt, expected_format="list", max_retries=2),
                timeout=60.0  # 60 second timeout for batch
            )
            vocab_log(f"✅ VOCAB: Batch starting at {start_index} API call completed", question_number)
        except asyncio.TimeoutError:
            vocab_log(f"⚠️ VOCAB: Batch starting at {start_index} timed out after 60s", question_number)
            return [{"sentence_idx": start_index + i, "sentence": s, "suggestions": [], "success": False, "error": "timeout"} for i, s in enumerate(sentences)]

        # Initialize results for all sentences (including empty ones)
        batch_results = []
        for i, sentence in enumerate(sentences):
            batch_results.append({
                "sentence_idx": start_index + i,
                "sentence": sentence,
                "suggestions": [],
                "success": True
            })

        if result and isinstance(result, list):
            # Map results back to original positions
            for result_idx, suggestions in enumerate(result):
                if result_idx < len(non_empty_indices):
                    original_batch_idx = non_empty_indices[result_idx]

                    if isinstance(suggestions, list):
                        valid_suggestions = []
                        for suggestion in suggestions:
                            if isinstance(suggestion, dict) and all(k in suggestion for k in ["type", "category", "original_word", "suggested_word", "explanation", "examples"]):
                                valid_suggestions.append(suggestion)
                        batch_results[original_batch_idx]["suggestions"] = valid_suggestions
        else:
            # Mark all as failed if API returned nothing
            for br in batch_results:
                if br["sentence"] and br["sentence"].strip():
                    br["success"] = False

        vocab_log(f"✅ VOCAB: Batch starting at {start_index} completed", question_number)
        return batch_results

    except Exception as e:
        vocab_log(f"💥 VOCAB: Error analyzing batch starting at {start_index}: {str(e)[:100]}", question_number)
        return [{"sentence_idx": start_index + i, "sentence": s, "suggestions": [], "success": False, "error": str(e)} for i, s in enumerate(sentences)]

def aggregate_vocabulary_results(results: List[Dict], sentences: List[str]) -> Dict[str, Any]:
    """Aggregate vocabulary collocation results from parallel sentence processing"""
    vocabulary_suggestions = {}
    total_suggestions = 0
    failed_sentences = []
    successful_sentences = 0
    
    for result in results:
        if isinstance(result, Exception):
            failed_sentences.append(str(result))
            continue
        
        if not result.get("success", False):
            failed_sentences.append(result.get("error", "Unknown error"))
            continue
        
        successful_sentences += 1
        sentence_idx = result["sentence_idx"]
        suggestions = result["suggestions"]
        
        for suggestion_idx, suggestion in enumerate(suggestions):
            key = f"sentence_{sentence_idx}_{suggestion_idx}"
            
            vocabulary_suggestions[key] = {
                "type": suggestion.get("type", "vocabulary"),
                "category": suggestion.get("category", 10),  # Default to "Other" category
                "original_word": suggestion.get("original_word", ""),
                "suggested_word": suggestion.get("suggested_word", ""),
                "explanation": suggestion.get("explanation", ""),
                "examples": suggestion.get("examples", []),
                "sentence_index": sentence_idx,
                "phrase_index": suggestion_idx,
                "sentence_text": sentences[sentence_idx]
            }
            total_suggestions += 1
    
    # Calculate grade based on number of vocabulary suggestions (similar to grammar service)
    if total_suggestions == 0:
        grade = 100
    elif total_suggestions <= 2:
        grade = 90
    elif total_suggestions <= 4:
        grade = 80
    elif total_suggestions <= 6:
        grade = 70
    else:
        grade = max(60 - (total_suggestions - 6) * 5, 0)
    
    logger.info(f"Vocabulary collocation analysis completed: {successful_sentences}/{len(sentences)} sentences successful, {total_suggestions} suggestions found")
    
    return {
        "grade": grade,
        "vocabulary_suggestions": vocabulary_suggestions,
        "failed_sentences": len(failed_sentences),
        "successful_sentences": successful_sentences,
        "total_suggestions": total_suggestions
    }

def enhance_vocabulary_suggestions_with_context(sentences: List[str], vocab_suggestions_per_sentence: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Add sentence and phrase context to vocabulary suggestions"""
    logger.info("Enhancing vocabulary suggestions with context")
    
    for sentence_idx, sentence_suggestions in enumerate(vocab_suggestions_per_sentence):
        if not sentence_suggestions or sentence_idx >= len(sentences):
            continue
            
        sentence_text = sentences[sentence_idx]
        word_counts = {}  # Track occurrences of each word in this sentence
        
        for suggestion in sentence_suggestions:
            original_word = suggestion.get("original_word", "")
            
            # Count how many times we've seen this word
            word_counts[original_word] = word_counts.get(original_word, 0)
            
            # Add context fields
            suggestion.update({
                "sentence_index": sentence_idx,
                "phrase_index": word_counts[original_word],
                "sentence_text": sentence_text
            })
            
            word_counts[original_word] += 1
            
    return vocab_suggestions_per_sentence

# LEGACY CEFR-based analysis using NLP processor - commented out
# async def analyze_vocabulary(transcript: str) -> Dict[str, Any]:
#     """Analyze vocabulary in a transcript"""
#     try:
#         # Ensure NLP processor is initialized
#         if vocabulary_tools.nlp_processor is None:
#             logger.info("Initializing NLP processor...")
#             vocabulary_tools.initialize()
#             if vocabulary_tools.nlp_processor is None:
#                 raise RuntimeError("Failed to initialize NLP processor")
# 
#         # Split transcript into sentences
#         doc = vocabulary_tools.nlp_processor(transcript)
#         sentences = [sent.text.strip() for sent in doc.sents]
#         
#         # Process sentences in parallel
#         tasks = [analyze_single_sentence_vocabulary(sentence, idx) for idx, sentence in enumerate(sentences)]
#         results = await asyncio.gather(*tasks, return_exceptions=True)
#         
#         # Aggregate results
#         return aggregate_vocabulary_results(results, sentences)
# 
#     except Exception as e:
#         logger.exception(f"Error in vocabulary analysis: {str(e)}")
#         return {
#             "grade": 0,
#             "vocabulary_suggestions": {}
#         }

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex (similar to grammar service)"""
    logger.info("Splitting text into sentences")
    text = re.sub(r'\s+', ' ', text).strip()
    
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(sentence_pattern, text)
    
    result = [s.strip() for s in sentences if s.strip()]
    logger.info(f"Split text into {len(result)} sentences")
    
    return result

async def analyze_vocabulary(transcript: str, question_number: int = None) -> Dict[str, Any]:
    """Analyze vocabulary collocations in a transcript using batched API calls for efficiency"""
    vocab_log(f"🔍 VOCAB: Starting vocabulary analysis for transcript of length: {len(transcript)}", question_number)

    if not transcript or not transcript.strip():
        vocab_log(f"🔍 VOCAB: Empty transcript, returning default result", question_number)
        return {
            "grade": 100,
            "vocabulary_suggestions": {},
        }

    try:
        sentences = split_into_sentences(transcript)
        vocab_log(f"🔍 VOCAB: Analyzing {len(sentences)} sentences in batches of {VOCABULARY_BATCH_SIZE}", question_number)

        # Split sentences into batches
        batches = []
        for i in range(0, len(sentences), VOCABULARY_BATCH_SIZE):
            batch = sentences[i:i + VOCABULARY_BATCH_SIZE]
            batches.append((batch, i))  # (sentences, start_index)

        vocab_log(f"🔍 VOCAB: Created {len(batches)} batches for {len(sentences)} sentences", question_number)

        # Process batches in parallel
        batch_tasks = [
            analyze_batch_vocabulary(batch_sentences, start_idx, question_number)
            for batch_sentences, start_idx in batches
        ]

        # Add timeout to prevent hanging
        try:
            batch_results = await asyncio.wait_for(
                asyncio.gather(*batch_tasks, return_exceptions=True),
                timeout=180.0  # 3 minute timeout for all batches
            )
            vocab_log(f"🔍 VOCAB: Batch processing completed successfully", question_number)
        except asyncio.TimeoutError:
            vocab_log(f"💥 VOCAB: Timeout after 180s processing {len(batches)} batches", question_number)
            return {
                "grade": 50,
                "vocabulary_suggestions": {},
            }

        # Flatten results from all batches
        all_results = []
        failed_batches = []

        for batch_idx, batch_result in enumerate(batch_results):
            if isinstance(batch_result, Exception):
                vocab_log(f"💥 VOCAB: Batch {batch_idx} failed with exception: {batch_result}", question_number)
                failed_batches.append(batch_idx)
                # Add failed results for this batch
                batch_sentences, start_idx = batches[batch_idx]
                for i, s in enumerate(batch_sentences):
                    all_results.append({
                        "sentence_idx": start_idx + i,
                        "sentence": s,
                        "suggestions": [],
                        "success": False,
                        "error": str(batch_result)
                    })
            else:
                all_results.extend(batch_result)

        # Retry failed batches with per-sentence analysis as fallback
        if failed_batches:
            vocab_log(f"⚠️ VOCAB: Retrying {len(failed_batches)} failed batches with per-sentence analysis", question_number)
            for batch_idx in failed_batches:
                batch_sentences, start_idx = batches[batch_idx]
                fallback_tasks = [
                    analyze_single_sentence_vocabulary(sentence, start_idx + i)
                    for i, sentence in enumerate(batch_sentences)
                ]
                fallback_results = await asyncio.gather(*fallback_tasks, return_exceptions=True)

                # Replace failed results with fallback results
                for i, fallback_result in enumerate(fallback_results):
                    result_idx = start_idx + i
                    for j, r in enumerate(all_results):
                        if r["sentence_idx"] == result_idx:
                            if isinstance(fallback_result, Exception):
                                all_results[j] = {
                                    "sentence_idx": result_idx,
                                    "sentence": batch_sentences[i],
                                    "suggestions": [],
                                    "success": False,
                                    "error": str(fallback_result)
                                }
                            else:
                                all_results[j] = fallback_result
                            break

        # Sort results by sentence index
        all_results.sort(key=lambda x: x["sentence_idx"])

        # Aggregate results
        vocab_log(f"🔍 VOCAB: Aggregating results from {len(all_results)} sentence analyses", question_number)
        final_result = aggregate_vocabulary_results(all_results, sentences)
        vocab_log(f"✅ VOCAB: Analysis completed successfully with grade: {final_result.get('grade', 'N/A')}", question_number)
        return final_result

    except Exception as e:
        vocab_log(f"💥 VOCAB: Critical error in vocabulary analysis: {str(e)}", question_number)
        logger.exception("Full vocabulary analysis exception:")
        return {
            "grade": 25,
            "vocabulary_suggestions": {},
        } 