import logging
import aiohttp
import json
import asyncio
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
from app.models.vocabulary_model import VocabularySuggestion, VocabularyFeedback
from app.utils.vocabulary_utils import vocabulary_tools

# Setup logging
logger = logging.getLogger(__name__)

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
                "messages": [{"role": "user", "content": current_prompt}],
                "temperature": 0.1
            }

            async with aiohttp.ClientSession() as session:
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

        except Exception as e:
            logger.exception(f"Error in API call: {str(e)}")
            if attempt == max_retries:
                return None

    return None

def create_vocabulary_prompt_for_single_sentence(sentence: str) -> str:
    """Create optimized prompt for single sentence vocabulary analysis"""
    return f"""
You are an expert in English vocabulary analysis specializing in CEFR levels and word usage.

Analyze this sentence for vocabulary improvement opportunities: "{sentence}"

Identify:
1. Basic level words (A1-A2) that could be replaced with more advanced vocabulary
2. Words that are used in an incorrect or unnatural context
3. Opportunities to use more sophisticated vocabulary, even if the current word is already advanced

IMPORTANT: When suggesting replacements, you MUST follow this progression:
- For A1 words, suggest ONLY A2 alternatives
- For A2 words, suggest ONLY B1 alternatives
- For B1 words, suggest ONLY B2 alternatives
- For B2 words, suggest ONLY C1 alternatives

Never skip levels in your suggestions. Each suggestion should be exactly one level higher than the original word.

For each issue identified, provide:
- The original word
- A suggested replacement word
- The CEFR level of both words
- A brief explanation of why the change would improve the text
- Example usage of the suggested word

Present the results in JSON format:
[
    {{
        "original_word": "[word_from_text]",
        "suggested_word": "[better_alternative]",
        "original_level": "[CEFR_level]",
        "suggested_level": "[higher_CEFR_level]",
        "explanation": "[reason_for_improvement]",
        "examples": ["[example_sentence_with_suggested_word]"]
    }}
]

ONLY analyze the actual words present in the sentence provided above. Do not suggest changes for words that are not in the text.

Return ONLY the JSON array. No other text or markdown formatting.
"""

async def analyze_single_sentence_vocabulary(sentence: str, sentence_idx: int) -> Dict[str, Any]:
    """Analyze vocabulary for a single sentence"""
    logger.info(f"Analyzing vocabulary for sentence {sentence_idx}")
    
    if not sentence or not sentence.strip():
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": True
        }
    
    try:
        prompt = create_vocabulary_prompt_for_single_sentence(sentence)
        result = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        suggestions = []
        if result and isinstance(result, list):
            for suggestion in result:
                if isinstance(suggestion, dict) and all(k in suggestion for k in ["original_word", "suggested_word", "original_level", "suggested_level", "explanation", "examples"]):
                    suggestions.append(suggestion)
        
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": suggestions,
            "success": result is not None
        }
        
    except Exception as e:
        logger.error(f"Error analyzing vocabulary for sentence {sentence_idx}: {e}")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": False,
            "error": str(e)
        }

def aggregate_vocabulary_results(results: List[Dict], sentences: List[str]) -> Dict[str, Any]:
    """Aggregate vocabulary results from parallel sentence processing"""
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
            key = f"{sentence_idx}_{suggestion_idx}"
            
            vocabulary_suggestions[key] = {
                "original_word": suggestion.get("original_word", ""),
                "suggested_word": suggestion.get("suggested_word", ""),
                "original_level": suggestion.get("original_level", ""),
                "suggested_level": suggestion.get("suggested_level", ""),
                "word_type": "unknown",  # Could be enhanced with POS tagging
                "examples": suggestion.get("examples", []),
                "explanation": suggestion.get("explanation", ""),
                "sentence_index": sentence_idx,
                "phrase_index": suggestion_idx,
                "sentence_text": sentences[sentence_idx]
            }
            total_suggestions += 1
    
    # Calculate grade based on number of vocabulary suggestions
    if total_suggestions == 0:
        grade = 100
    elif total_suggestions <= 1:
        grade = 95
    elif total_suggestions <= 2:
        grade = 90
    elif total_suggestions <= 3:
        grade = 85
    elif total_suggestions <= 4:
        grade = 80
    else:
        grade = max(75 - (total_suggestions - 4) * 5, 50)
    
    logger.info(f"Vocabulary analysis completed: {successful_sentences}/{len(sentences)} sentences successful, {total_suggestions} suggestions found")
    
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

async def analyze_vocabulary(transcript: str) -> Dict[str, Any]:
    """Analyze vocabulary in a transcript"""
    try:
        # Ensure NLP processor is initialized
        if vocabulary_tools.nlp_processor is None:
            logger.info("Initializing NLP processor...")
            vocabulary_tools.initialize()
            if vocabulary_tools.nlp_processor is None:
                raise RuntimeError("Failed to initialize NLP processor")

        # Split transcript into sentences
        doc = vocabulary_tools.nlp_processor(transcript)
        sentences = [sent.text.strip() for sent in doc.sents]
        
        # Process sentences in parallel
        tasks = [analyze_single_sentence_vocabulary(sentence, idx) for idx, sentence in enumerate(sentences)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        return aggregate_vocabulary_results(results, sentences)

    except Exception as e:
        logger.exception(f"Error in vocabulary analysis: {str(e)}")
        return {
            "grade": 0,
            "vocabulary_suggestions": {}
        } 