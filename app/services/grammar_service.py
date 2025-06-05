import re
import logging
import aiohttp
import json
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
import difflib

# Setup logging
logger = logging.getLogger(__name__)

MODEL = "gpt-4o-mini"

async def call_openai_with_retry(prompt: str, expected_format: str = "list", max_retries: int = 2) -> Any:
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
                "messages": [{"role": "user", "content": current_prompt}],
                "temperature": 0.1,
                "response_format": { "type": "json_object" }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Log the raw response for debugging
                        logger.info(f"Raw API response: {content}")
                        
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
                        
        except Exception as e:
            logger.exception(f"Error in API call: {str(e)}")
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

async def check_grammar(sentences: List[str]) -> List[List[Dict[str, Any]]]:
    """Check grammar for each sentence"""
    logger.info(f"Checking grammar for {len(sentences)} sentences")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty corrections")
        return [[] for _ in sentences]
    
    try:
        prompt = """
You are an expert in English grammar. Analyze the following transcript, which is based on a spoken response. Since it is derived from speech, ignore disfluencies (e.g., "um", "uh"), filler words, and transcription-related punctuation issues.
IMPORTANT: ONLY GIVE A TOTAL OF 3 Grammar suggestions on different sentences.

Your job is to detect and correct grammar mistakes related to:
- Subject-verb agreement (e.g., "he don't" → "he doesn't")
- Verb tense consistency (e.g., "i am going yesterday" → "i went yesterday")
- Article usage (e.g., "i went to store" → "i went to the store")
- Singular/plural form (e.g., "they is happy" → "they are happy")
- Word order and sentence structure (e.g., "yesterday i went store" → "yesterday i went to the store")
- Preposition use (e.g., "i am good in english" → "i am good at english")
- Sentence completeness (e.g., "because i was tired" → "i went home because i was tired")

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
        
        corrections = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
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

async def analyze_grammar(transcript: str) -> Dict[str, Any]:
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
        
        # Get grammar analysis
        raw_corrections = await check_grammar(sentences)
        
        # Simplify single-word grammar corrections
        simplified_corrections = []
        for sentence_items in raw_corrections:
            sentence_processed = []
            for item in sentence_items:
                if item.get("type") == "grammar":
                    correction = {
                        "original_phrase": item["original_phrase"],
                        "suggested_correction": item["suggested_correction"],
                        "explanation": item["explanation"]
                    }
                    simplified = simplify_single_word_corrections([[correction]])
                    if simplified and simplified[0]:
                        sentence_processed.extend(
                            [dict(item, **corr) for corr in simplified[0]]
                        )
            simplified_corrections.append(sentence_processed)
        
        # Enhance with context
        enhanced_corrections = enhance_grammar_corrections_with_context(
            sentences, 
            simplified_corrections
        )
        
        # Format results for API response
        grammar_corrections_dict = {}
        total_corrections = 0
        
        for sentence_idx, sentence_items in enumerate(enhanced_corrections):
            for item_idx, item in enumerate(sentence_items):
                key = f"sentence_{sentence_idx}_{item_idx}"
                grammar_corrections_dict[key] = {
                    "original": sentences[sentence_idx],
                    "corrections": [item]
                }
                total_corrections += 1
        
        # Calculate grade
        if total_corrections == 0:
            grade = 100
        elif total_corrections <= 2:
            grade = 90
        elif total_corrections <= 4:
            grade = 80
        elif total_corrections <= 6:
            grade = 70
        else:
            grade = max(60 - (total_corrections - 6) * 5, 0)
        
        return {
            "grade": grade,
            "grammar_corrections": grammar_corrections_dict,
        }
        
    except Exception as e:
        logger.exception("Error in grammar analysis")
        return {
            "grade": 0,
            "grammar_corrections": {},
        } 