import re
import logging
import aiohttp
import json
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
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
MODEL = "gpt-4o-mini"

async def call_openai_with_retry(prompt: str, expected_format: str = "list", max_retries: int = 2) -> Any:
    """Call OpenAI API with retry mechanism for format validation"""
    if not OPENAI_API_KEY:
        logger.warning("No API key available, cannot make API call")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    current_prompt = prompt

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

            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": current_prompt}]
            }

            timeout = aiohttp.ClientTimeout(total=30, connect=5)  # Reduced timeout
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, use_dns_cache=True)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        try:
                            parsed_content = json.loads(content)
                            if (expected_format == "list" and isinstance(parsed_content, list)) or \
                               (expected_format == "dict" and isinstance(parsed_content, dict)):
                                return parsed_content
                        except json.JSONDecodeError:
                            if attempt == max_retries:
                                return None
                    else:
                        if attempt == max_retries:
                            return None

        except (aiohttp.ClientError, BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.warning(f"Connection error in API call (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries:
                logger.error(f"Max retries reached for API call: {str(e)}")
                return None
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except Exception as e:
            logger.exception(f"Unexpected error in API call: {str(e)}")
            if attempt == max_retries:
                return None

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

async def analyze_single_sentence_vocabulary(sentence: str, sentence_idx: int) -> Dict[str, Any]:
    """Analyze vocabulary collocations for a single sentence"""
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
                call_openai_with_retry(prompt, expected_format="list", max_retries=1),  # Reduced retries
                timeout=30.0  # 30 second timeout per sentence
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
    """Analyze vocabulary collocations in a transcript"""
    vocab_log(f"🔍 VOCAB: Starting vocabulary analysis for transcript of length: {len(transcript)}", question_number)
    
    if not transcript or not transcript.strip():
        vocab_log(f"🔍 VOCAB: Empty transcript, returning default result", question_number)
        return {
            "grade": 100,
            "vocabulary_suggestions": {},
        }
        
    try:
        sentences = split_into_sentences(transcript)
        vocab_log(f"🔍 VOCAB: Analyzing {len(sentences)} sentences for vocabulary collocations", question_number)
        
        # Process sentences in parallel with timeout protection
        tasks = [analyze_single_sentence_vocabulary(sentence, idx) for idx, sentence in enumerate(sentences)]
        
        # Add timeout to prevent hanging
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=120.0  # 2 minute timeout
            )
            vocab_log(f"🔍 VOCAB: Parallel sentence analysis completed successfully", question_number)
        except asyncio.TimeoutError:
            vocab_log(f"💥 VOCAB: Timeout after 120s processing {len(sentences)} sentences", question_number)
            # Return fallback result instead of failing
            return {
                "grade": 50,  # Neutral score for timeout
                "vocabulary_suggestions": {},
            }
        
        # Check for exceptions in results
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            vocab_log(f"⚠️ VOCAB: {len(exceptions)} sentence analyses failed, continuing with successful ones", question_number)
            for i, exc in enumerate(exceptions):
                vocab_log(f"⚠️ VOCAB: Sentence {i} failed: {str(exc)[:100]}", question_number)
        
        # Aggregate results
        vocab_log(f"🔍 VOCAB: Aggregating results from {len(results)} sentence analyses", question_number)
        final_result = aggregate_vocabulary_results(results, sentences)
        vocab_log(f"✅ VOCAB: Analysis completed successfully with grade: {final_result.get('grade', 'N/A')}", question_number)
        return final_result
        
    except Exception as e:
        vocab_log(f"💥 VOCAB: Critical error in vocabulary analysis: {str(e)}", question_number)
        logger.exception("Full vocabulary analysis exception:")
        # Return fallback result instead of failing
        return {
            "grade": 25,  # Low score for error
            "vocabulary_suggestions": {},
        } 