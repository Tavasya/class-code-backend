import re
import logging
import aiohttp
import json
import asyncio
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
import difflib

# Setup logging
logger = logging.getLogger(__name__)

MODEL = "gpt-5-nano"

async def call_openai_with_retry(prompt: str, expected_format: str = "list", max_retries: int = 2, submission_url: str = None, question_number: int = None) -> Any:
    """Call OpenAI API with retry mechanism for format validation"""
    logger.info(f"Calling OpenAI API with format validation, expecting: {expected_format}")
    
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
            
            logger.info(f"API call attempt {attempt + 1}/{max_retries + 1}")
            
            payload = {
                "model": MODEL,
                "messages": [{"role": "user", "content": current_prompt}]
            }
            
            # Track API call
            if submission_url:
                try:
                    from app.services.api_call_tracker import api_call_tracker
                    await api_call_tracker.increment_openai_call(submission_url, "grammar", question_number)
                except Exception as e:
                    logger.warning(f"Failed to track API call: {str(e)}")
            
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            connector = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300, use_dns_cache=True)
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        if "```json" in content or "```" in content:
                            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
                            match = re.search(json_pattern, content, re.DOTALL)
                            if match:
                                content = match.group(1)
                        
                        try:
                            parsed_content = json.loads(content)
                            logger.info(f"Parsed content: {parsed_content}")
                            
                            # Handle both list and dict responses
                            if isinstance(parsed_content, dict) and "corrections" in parsed_content:
                                return parsed_content["corrections"]
                            elif isinstance(parsed_content, list):
                                return parsed_content
                            else:
                                logger.warning(f"Invalid format: expected list or dict with 'corrections' key, got {type(parsed_content)}")
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}")
                            if attempt == max_retries:
                                return None
                    else:
                        error_content = await response.text()
                        logger.error(f"API error: {response.status}, {error_content[:200]}...")
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

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using regex"""
    logger.info("Splitting text into sentences")
    text = re.sub(r'\s+', ' ', text).strip()
    
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(sentence_pattern, text)
    
    result = [s.strip() for s in sentences if s.strip()]
    logger.info(f"Split text into {len(result)} sentences")
    
    return result

def enhance_grammar_corrections_with_context(sentences: List[str], corrections_per_sentence: List[List[Dict[str, str]]]) -> List[List[Dict[str, str]]]:
    """Add sentence and phrase context to grammar corrections"""
    logger.info("Enhancing grammar corrections with context")
    
    for sentence_idx, sentence_corrections in enumerate(corrections_per_sentence):
        if not sentence_corrections or sentence_idx >= len(sentences):
            continue
            
        sentence_text = sentences[sentence_idx]
        phrase_counts = {}  # Track occurrences of each phrase in this sentence
        
        for correction in sentence_corrections:
            original_phrase = correction.get("original_phrase", "")
            
            # Count how many times we've seen this phrase
            phrase_counts[original_phrase] = phrase_counts.get(original_phrase, 0)
            
            # Add context fields
            correction.update({
                "sentence_index": sentence_idx,
                "phrase_index": phrase_counts[original_phrase],
                "sentence_text": sentence_text
            })
            
            phrase_counts[original_phrase] += 1
            
    return corrections_per_sentence

def simplify_single_word_corrections(
    corrections_per_sentence: List[List[Dict[str, str]]]
) -> List[List[Dict[str, str]]]:
    """
    Attempts to simplify corrections down to a single word if the change
    is primarily a single-word substitution.
    """
    processed_sentences = []
    for sentence_corrections in corrections_per_sentence:
        if not sentence_corrections:
            processed_sentences.append([])
            continue

        processed_corrections_for_sentence = []
        for correction in sentence_corrections:
            original_phrase_str = correction.get("original_phrase", "")
            suggested_correction_str = correction.get("suggested_correction", "")

            if not original_phrase_str or not suggested_correction_str or original_phrase_str == suggested_correction_str:
                processed_corrections_for_sentence.append(correction)
                continue
            
            original_tokens = original_phrase_str.split()
            suggested_tokens = suggested_correction_str.split()

            matcher = difflib.SequenceMatcher(None, original_tokens, suggested_tokens)
            opcodes = matcher.get_opcodes()
            
            is_single_word_substitution = False
            new_original_word = None
            new_suggested_word = None

            if len(opcodes) > 0:
                change_opcodes = [op for op in opcodes if op[0] != 'equal']

                if len(change_opcodes) == 1 and change_opcodes[0][0] == 'replace':
                    tag, i1, i2, j1, j2 = change_opcodes[0]
                    if (i2 - i1 == 1) and (j2 - j1 == 1): 
                        # Check if all other opcodes are 'equal'
                        only_one_replace_and_rest_equal = True
                        for op_tag, _, _, _, _ in opcodes:
                            if op_tag != 'equal' and op_tag != 'replace':
                                only_one_replace_and_rest_equal = False
                                break
                        
                        if only_one_replace_and_rest_equal:
                             # Further check: ensure the replace operation itself is surrounded by equals or is the only operation
                            if len(opcodes) == 1: # Only the replace operation
                                is_single_word_substitution = True
                            elif len(opcodes) > 1 :
                                # Check if this replace is bounded by equals or at an end
                                replace_opcode_index = -1
                                for idx, op in enumerate(opcodes):
                                    if op[0] == 'replace' and op[1]==i1 and op[2]==i2 and op[3]==j1 and op[4]==j2:
                                        replace_opcode_index = idx
                                        break
                                
                                if replace_opcode_index != -1:
                                    is_valid_context = True
                                    # Check opcode before (if exists)
                                    if replace_opcode_index > 0 and opcodes[replace_opcode_index-1][0] != 'equal':
                                        is_valid_context = False
                                    # Check opcode after (if exists)
                                    if replace_opcode_index < len(opcodes) - 1 and opcodes[replace_opcode_index+1][0] != 'equal':
                                        is_valid_context = False
                                    
                                    if is_valid_context:
                                        is_single_word_substitution = True

                        if is_single_word_substitution:
                            new_original_word = original_tokens[i1]
                            new_suggested_word = suggested_tokens[j1]
            
            if is_single_word_substitution and new_original_word and new_suggested_word:
                simplified_correction = correction.copy() 
                simplified_correction["original_phrase"] = new_original_word
                simplified_correction["suggested_correction"] = new_suggested_word
                processed_corrections_for_sentence.append(simplified_correction)
                logger.info(f"Simplified correction: '{original_phrase_str}' -> '{suggested_correction_str}' to '{new_original_word}' -> '{new_suggested_word}'")
            else:
                processed_corrections_for_sentence.append(correction)
        
        processed_sentences.append(processed_corrections_for_sentence)
    return processed_sentences

def create_grammar_prompt_for_single_sentence(sentence: str) -> str:
    """Create optimized prompt for single sentence grammar analysis"""
    return f"""
You are an expert in English grammar. Analyze the following sentence, which is based on a spoken response. Since it is derived from speech, ignore disfluencies (e.g., "um", "uh"), filler words, and transcription-related punctuation issues.

Your job is to detect and correct grammar mistakes related to:
1. Subject-verb agreement (e.g., "he don't" → "he doesn't")
2. Verb tense consistency (e.g., "i am going yesterday" → "i went yesterday")
3. Article usage (e.g., "i went to store" → "i went to the store")
4. Singular/plural form (e.g., "they is happy" → "they are happy")
5. Word order and sentence structure (e.g., "yesterday i went store" → "yesterday i went to the store")
6. Preposition use (e.g., "i am good in english" → "i am good at english")
7. Sentence completeness (e.g., "because i was tired" → "i went home because i was tired")
8. Disfluencies (e.g., "um", "uh")
9. Punctuation issues
10. Mispellings/Fragments (e.g., "M not too sure by testing this." → "I'm not too sure about testing this.")
11. Grammar issues that arise from the punctuation (periods, commas, hyphens)
12. Other

IMPORTANT: Always analyze complete phrases, not just single words. Grammar issues often involve multiple words working together.

Sentence: "{sentence}"

Provide corrections in JSON format:
[
    {{
        "type": "grammar",
        "category": 1,
        "original_phrase": "problematic phrase",
        "suggested_correction": "corrected phrase", 
        "explanation": "brief explanation"
    }}
]

Return ONLY the JSON array. No other text or markdown formatting.
"""

async def analyze_single_sentence_grammar(sentence: str, sentence_idx: int, submission_url: str = None, question_number: int = None) -> Dict[str, Any]:
    """Analyze grammar for a single sentence"""
    logger.info(f"Analyzing grammar for sentence {sentence_idx}")
    
    if not sentence or not sentence.strip():
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "corrections": [],
            "success": True
        }
    
    try:
        prompt = create_grammar_prompt_for_single_sentence(sentence)
        result = await call_openai_with_retry(prompt, expected_format="list", max_retries=2, submission_url=submission_url, question_number=question_number)
        
        corrections = []
        if result and isinstance(result, list):
            for correction in result:
                if isinstance(correction, dict) and all(k in correction for k in ["type", "original_phrase", "suggested_correction", "explanation"]):
                    corrections.append(correction)
        
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "corrections": corrections,
            "success": result is not None
        }
        
    except Exception as e:
        logger.error(f"Error analyzing sentence {sentence_idx}: {e}")
        return {
            "sentence_idx": sentence_idx,
            "sentence": sentence,
            "corrections": [],
            "success": False,
            "error": str(e)
        }

async def check_grammar(sentences: List[str], submission_url: str = None, question_number: int = None) -> List[List[Dict[str, Any]]]:
    """Check grammar for each sentence"""
    logger.info(f"Checking grammar for {len(sentences)} sentences")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty corrections")
        return [[] for _ in sentences]
    
    try:
        prompt = """
You are an expert in English grammar. Analyze the following transcript, which is based on a spoken response. Since it is derived from speech, ignore disfluencies (e.g., "um", "uh"), filler words, and transcription-related punctuation issues.

Your job is to detect and correct grammar mistakes related to:
1. Subject-verb agreement (e.g., "he don't" → "he doesn't")
2. Verb tense consistency (e.g., "i am going yesterday" → "i went yesterday")
3. Article usage (e.g., "i went to store" → "i went to the store")
4. Singular/plural form (e.g., "they is happy" → "they are happy")
5. Word order and sentence structure (e.g., "yesterday i went store" → "yesterday i went to the store")
6. Preposition use (e.g., "i am good in english" → "i am good at english")
7. Sentence completeness (e.g., "because i was tired" → "i went home because i was tired")
8. Other

IMPORTANT: Always analyze complete phrases, not just single words. Grammar issues often involve multiple words working together.
For example:
- "he don't" (not just "don't")
- "i am going yesterday" (not just "going")
- "they is happy" (not just "is")

Provide a list of corrections for each sentence in structured JSON format. Each item should include:
- "type": "grammar"
- "original_phrase": the complete problematic phrase (not just a single word)
- "suggested_correction": the complete corrected phrase
- "explanation": brief explanation of the issue

Output format:
[
    [  // corrections for sentence 1
        {
            "type": "grammar",
            "original_phrase": "he don't like",
            "suggested_correction": "he doesn't like",
            "explanation": "Subject-verb agreement correction"
        }
    ],
    [], // sentence 2: no corrections
    [ ... ], // sentence 3: corrections
    ...
]

Here are the sentences to analyze:
"""
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with corrections. No other text or markdown formatting."
        
        corrections = await call_openai_with_retry(prompt, expected_format="list", max_retries=2, submission_url=submission_url, question_number=question_number)
        
        if corrections is None:
            logger.warning("Failed to get corrections from API")
            return [[] for _ in sentences]
            
        # Log the corrections for debugging
        logger.info(f"Received corrections: {corrections}")
            
        # Ensure we have the correct number of sentence entries
        while len(corrections) < len(sentences):
            corrections.append([])
            
        # Ensure each correction has the required fields
        processed_corrections = []
        for sentence_corrections in corrections:
            processed_sentence = []
            for correction in sentence_corrections:
                if isinstance(correction, dict) and all(k in correction for k in ["type", "original_phrase", "suggested_correction", "explanation"]):
                    processed_sentence.append(correction)
            processed_corrections.append(processed_sentence)
            
        # Log the processed corrections for debugging
        logger.info(f"Processed corrections: {processed_corrections}")
            
        return processed_corrections
        
    except Exception as e:
        logger.exception(f"Error in grammar checking: {str(e)}")
        return [[] for _ in sentences]

def aggregate_grammar_results(results: List[Dict], sentences: List[str]) -> Dict[str, Any]:
    """Aggregate grammar results from parallel sentence processing"""
    grammar_corrections_dict = {}
    total_corrections = 0
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
        corrections = result["corrections"]
        
        for correction_idx, correction in enumerate(corrections):
            key = f"sentence_{sentence_idx}_{correction_idx}"
            
            # Enhance correction with context
            enhanced_correction = correction.copy()
            enhanced_correction.update({
                "sentence_index": sentence_idx,
                "phrase_index": 0,  # Will be updated by enhance_grammar_corrections_with_context if needed
                "sentence_text": sentences[sentence_idx]
            })
            
            grammar_corrections_dict[key] = {
                "original": sentences[sentence_idx],
                "corrections": [enhanced_correction]
            }
            total_corrections += 1
    
    # Calculate grade based on total corrections
    if total_corrections == 0:
        grade = 100
    elif total_corrections <= 2:
        grade = 90
    elif total_corrections <= 4:
        grade = 80
    elif total_corrections <= 6:
        grade = 70
    else:
        grade = max(60 - (total_corrections - 6) * 5, 50)
    
    logger.info(f"Grammar analysis completed: {successful_sentences}/{len(sentences)} sentences successful, {total_corrections} corrections found")
    
    return {
        "grade": grade,
        "grammar_corrections": grammar_corrections_dict,
        "failed_sentences": len(failed_sentences),
        "successful_sentences": successful_sentences,
        "total_corrections": total_corrections
    }

async def analyze_grammar(transcript: str, submission_url: str = None, question_number: int = None) -> Dict[str, Any]:
    """Analyze grammar in a transcript"""
    logger.info(f"Starting grammar analysis for transcript of length: {len(transcript)}")
    
    if not transcript or not transcript.strip():
        return {
            "grade": 100,
            "grammar_corrections": {},
        }
        
    try:
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences")
        
        # Process sentences in parallel
        tasks = [analyze_single_sentence_grammar(sentence, idx, submission_url, question_number) for idx, sentence in enumerate(sentences)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        return aggregate_grammar_results(results, sentences)
        
    except Exception as e:
        logger.exception("Error in grammar analysis")
        return {
            "grade": 0,
            "grammar_corrections": {},
        } 