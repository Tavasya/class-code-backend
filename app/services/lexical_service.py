import logging
import aiohttp
import json
import asyncio
from typing import List, Dict, Any, Optional
from app.models.lexical_model import LexicalFeedback, LexicalCorrection
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

# Setup logging
logger = logging.getLogger(__name__)

# OpenAI API configuration
MODEL = "gpt-4o-mini"  # or your preferred model

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

            timeout = aiohttp.ClientTimeout(total=60, connect=10)
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

def create_lexical_prompt_for_single_sentence(sentence: str) -> str:
    """Create optimized prompt for single sentence lexical analysis"""
    return f"""
You are an expert in English lexical resources specializing in collocations, idioms, and natural word usage.

Analyze this sentence for lexical resource issues: "{sentence}"

Identify:
1. Collocations that are used incorrectly or unnaturally
2. Idioms that are used incorrectly or could be used to enhance the sentence
3. Word usage errors where a word is used in an incorrect or unnatural context
4. Word combinations that don't follow conventional Oxford English patterns

For each issue identified, provide:
- The incorrect/unnatural phrase
- The suggested correction with proper collocation/idiom usage
- A brief explanation of the correction
- The type of issue (collocation, idiom, or word_usage)

Present the results in JSON format:
[
    {{
        "original_phrase": "make a decision",
        "suggested_phrase": "take a decision",
        "explanation": "In English, decisions are typically 'taken' rather than 'made'",
        "resource_type": "collocation"
    }}
]

Return ONLY the JSON array. No other text or markdown formatting.
"""

async def analyze_single_sentence_lexical(sentence: str, sentence_idx: int) -> Dict[str, Any]:
    """Analyze lexical resources for a single sentence"""
    logger.info(f"Analyzing lexical resources for sentence {sentence_idx}")
    
    if not sentence or not sentence.strip():
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": True
        }
    
    try:
        prompt = create_lexical_prompt_for_single_sentence(sentence)
        result = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        suggestions = []
        if result and isinstance(result, list):
            for suggestion in result:
                if isinstance(suggestion, dict) and all(k in suggestion for k in ["original_phrase", "suggested_phrase", "explanation", "resource_type"]):
                    suggestions.append(suggestion)
        
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": suggestions,
            "success": result is not None
        }
        
    except Exception as e:
        logger.error(f"Error analyzing lexical resources for sentence {sentence_idx}: {e}")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "suggestions": [],
            "success": False,
            "error": str(e)
        }

def aggregate_lexical_results(results: List[Dict], sentences: List[str]) -> Dict[str, Any]:
    """Aggregate lexical results from parallel sentence processing"""
    all_issues = []
    enhanced_lexical_analysis = []
    total_corrections = 0
    failed_sentences = []
    successful_sentences = 0
    
    for result in results:
        if isinstance(result, Exception):
            failed_sentences.append(str(result))
            enhanced_lexical_analysis.append([])
            continue
        
        if not result.get("success", False):
            failed_sentences.append(result.get("error", "Unknown error"))
            enhanced_lexical_analysis.append([])
            continue
        
        successful_sentences += 1
        sentence_idx = result["sentence_idx"]
        suggestions = result["suggestions"]
        
        # Add to enhanced_lexical_analysis for backward compatibility
        enhanced_suggestions = []
        for suggestion in suggestions:
            enhanced_suggestion = suggestion.copy()
            enhanced_suggestion.update({
                "sentence_index": sentence_idx,
                "phrase_index": 0,
                "sentence_text": sentences[sentence_idx]
            })
            enhanced_suggestions.append(enhanced_suggestion)
            
            # Add to all_issues for standardized format
            all_issues.append({
                "type": "lexical",
                "sentence": sentences[sentence_idx],
                "suggestion": {
                    "explanation": suggestion.get("explanation", ""),
                    "resource_type": suggestion.get("resource_type", "word usage"),
                    "original_phrase": suggestion.get("original_phrase", ""),
                    "suggested_phrase": suggestion.get("suggested_phrase", ""),
                    "sentence_index": sentence_idx,
                    "phrase_index": 0,
                    "sentence_text": sentences[sentence_idx]
                }
            })
            total_corrections += 1
        
        enhanced_lexical_analysis.append(enhanced_suggestions)
    
    # Calculate grade based on number of lexical issues
    if total_corrections == 0:
        grade = 100
    elif total_corrections <= 1:
        grade = 95
    elif total_corrections <= 2:
        grade = 90
    elif total_corrections <= 3:
        grade = 85
    elif total_corrections <= 4:
        grade = 80
    else:
        grade = max(75 - (total_corrections - 4) * 5, 50)
    
    logger.info(f"Lexical analysis completed: {successful_sentences}/{len(sentences)} sentences successful, {total_corrections} suggestions found")
    
    return {
        "grade": grade,
        "issues": all_issues,
        "enhanced_lexical_analysis": enhanced_lexical_analysis,
        "failed_sentences": len(failed_sentences),
        "successful_sentences": successful_sentences,
        "total_corrections": total_corrections
    }

async def analyze_lexical_resources(sentences: List[str]) -> Dict[str, Any]:
    """Analyze lexical resources in sentences and return feedback in standardized format"""
    if not sentences:
        return {
            "grade": 100,
            "issues": [],
            "enhanced_lexical_analysis": []
        }

    try:
        # Process sentences in parallel
        tasks = [analyze_single_sentence_lexical(sentence, idx) for idx, sentence in enumerate(sentences)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        return aggregate_lexical_results(results, sentences)

    except Exception as e:
        logger.exception(f"Error in lexical analysis: {str(e)}")
        return {
            "grade": 0,
            "issues": [{"type": "lexical", "sentence": "", "suggestion": {"explanation": f"Error analyzing lexical resources: {str(e)}", "resource_type": "error", "original_phrase": "", "suggested_phrase": ""}}],
            "enhanced_lexical_analysis": []
        }

def enhance_lexical_suggestions_with_context(sentences: List[str], lexical_analysis_per_sentence: List[List[Dict[str, Any]]]) -> List[List[Dict[str, Any]]]:
    """Add sentence and phrase context to lexical suggestions"""
    logger.info("Enhancing lexical suggestions with context")
    
    for sentence_idx, sentence_suggestions in enumerate(lexical_analysis_per_sentence):
        if not sentence_suggestions or sentence_idx >= len(sentences):
            continue
            
        sentence_text = sentences[sentence_idx]
        phrase_counts = {}  # Track occurrences of each phrase in this sentence
        
        for suggestion in sentence_suggestions:
            original_phrase = suggestion.get("original_phrase", "")
            
            # Count how many times we've seen this phrase
            phrase_counts[original_phrase] = phrase_counts.get(original_phrase, 0)
            
            # Add context fields
            suggestion.update({
                "sentence_index": sentence_idx,
                "phrase_index": phrase_counts[original_phrase],
                "sentence_text": sentence_text
            })
            
            phrase_counts[original_phrase] += 1
            
    return lexical_analysis_per_sentence 