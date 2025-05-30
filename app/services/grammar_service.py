import re
import logging
import aiohttp
import json
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
import difflib
from app.utils.vocabulary_utils import (
    get_lemma,
    OXFORD_DATA_CACHE,
    NLP_PROCESSOR,
    CEFR_PROGRESSION_MAP
)
from app.models.grammar_model import VocabularySuggestion

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
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
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
                            
                            format_valid = False
                            if expected_format == "list" and isinstance(parsed_content, list):
                                format_valid = True
                            elif expected_format == "dict" and isinstance(parsed_content, dict):
                                format_valid = True
                                
                            if format_valid:
                                return parsed_content
                            
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
                        # This ensures that the 'replace' is the *only* significant change
                        # and not part of a larger set of differences.
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

async def check_grammar_and_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]:
    """Check grammar and suggest vocabulary enhancements for each sentence"""
    logger.info(f"Checking grammar and vocabulary for {len(sentences)} sentences")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty corrections")
        return [[] for _ in sentences]
    
    try:
        prompt = """
You are an expert in English grammar and vocabulary enhancement. Analyze the following transcript, which is based on a spoken response. Since it is derived from speech, ignore disfluencies (e.g., "um", "uh"), filler words, and transcription-related punctuation issues.
IMPORTANT: ONLY GIVE A TOTAL OF 3 Grammar suggestions on different sentences.

Your job is to:
1. Detect and correct grammar mistakes related to:
   - Subject-verb agreement
   - Verb tense consistency
   - Article usage (a, an, the)
   - Singular/plural form
   - Word order and sentence structure
   - Preposition use
   - Sentence completeness (fragments, run-ons)

2. Identify basic vocabulary that could be enhanced:
   - Very basic verbs (like "get", "put", "go", "come")
   - Simple adjectives (like "nice", "bad", "big", "small")
   - Basic adverbs (like "very", "really", "a lot")
   - General nouns that could be more specific

Provide a list of corrections and suggestions for each sentence in structured JSON format. Each item should include:
- "type": either "grammar" or "vocabulary"
- "original_phrase": the problematic phrase or basic word
- "suggested_correction": the corrected version or suggested alternatives (comma-separated for vocabulary)
- "explanation": brief explanation of the issue or suggestion
- "level": (for vocabulary only) target CEFR level (B1, B2, or C1)

Output format:
[
    [  // corrections for sentence 1
        {
            "type": "grammar",
            "original_phrase": "he don't",
            "suggested_correction": "he doesn't",
            "explanation": "Subject-verb agreement correction"
        },
        {
            "type": "vocabulary",
            "original_phrase": "nice",
            "suggested_correction": "pleasant, delightful, enjoyable",
            "explanation": "Consider using more sophisticated adjectives",
            "level": "B1"
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
        
        prompt += "\n\nProvide ONLY the JSON array with corrections and suggestions. No other text or markdown formatting."
        
        corrections = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if corrections is None:
            return [[] for _ in sentences]
        
        # Process corrections and filter vocabulary suggestions through Oxford 5000
        processed_corrections = []
        for sentence_idx, sentence_items in enumerate(corrections):
            if sentence_idx >= len(sentences):
                break
                
            filtered_items = []
            for item in sentence_items:
                if item.get("type") == "vocabulary":
                    # Get suggested alternatives
                    alternatives = [alt.strip() for alt in item.get("suggested_correction", "").split(",")]
                    
                    # Filter through Oxford 5000
                    if NLP_PROCESSOR and OXFORD_DATA_CACHE:
                        original_word = item.get("original_phrase", "").strip()
                        original_lemma = get_lemma(original_word, NLP_PROCESSOR)
                        
                        if original_lemma in OXFORD_DATA_CACHE:
                            original_level = OXFORD_DATA_CACHE[original_lemma].get('level')
                            
                            if original_level in CEFR_PROGRESSION_MAP:
                                target_level = CEFR_PROGRESSION_MAP[original_level]
                                
                                # Filter alternatives through Oxford 5000
                                valid_alternatives = []
                                for alt in alternatives:
                                    alt_lemma = get_lemma(alt, NLP_PROCESSOR)
                                    if (alt_lemma in OXFORD_DATA_CACHE and 
                                        OXFORD_DATA_CACHE[alt_lemma]['level'] == target_level):
                                        valid_alternatives.append(alt)
                                
                                if valid_alternatives:
                                    item["suggested_correction"] = ", ".join(valid_alternatives)
                                    item["level"] = target_level
                                    filtered_items.append(item)
                else:
                    # Keep grammar corrections as is
                    filtered_items.append(item)
            
            processed_corrections.append(filtered_items)
            
        while len(processed_corrections) < len(sentences):
            processed_corrections.append([])
        
        return processed_corrections
        
    except Exception as e:
        logger.exception(f"Error in grammar and vocabulary checking: {str(e)}")
        return [[] for _ in sentences]

async def analyze_grammar(transcript: str) -> Dict[str, Any]:
    """Analyze grammar and vocabulary in a transcript"""
    logger.info(f"Starting language analysis for transcript of length: {len(transcript)}")
    
    if not transcript or not transcript.strip():
        return {
            "grade": 100,
            "issues": [],
            "grammar_corrections": {},
            "vocabulary_suggestions": {},
        }
        
    try:
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences")
        
        # Get combined grammar and vocabulary analysis
        raw_corrections = await check_grammar_and_vocabulary(sentences)
        
        # Simplify single-word grammar corrections
        simplified_corrections = []
        for sentence_items in raw_corrections:
            sentence_processed = []
            for item in sentence_items:
                if item.get("type") == "grammar":
                    # Only simplify grammar corrections
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
                else:
                    # Keep vocabulary suggestions as is
                    sentence_processed.append(item)
            simplified_corrections.append(sentence_processed)
        
        # Enhance with context
        enhanced_corrections = enhance_grammar_corrections_with_context(
            sentences, 
            [[item for item in sent if item.get("type") == "grammar"] for sent in simplified_corrections]
        )
        
        # Format results for API response
        grammar_corrections_dict = {}
        vocabulary_suggestions_dict = {}
        all_issues = []
        
        for sentence_idx, sentence_items in enumerate(simplified_corrections):
            for item_idx, item in enumerate(sentence_items):
                key = f"sentence_{sentence_idx}_{item_idx}"
                if item.get("type") == "grammar":
                    grammar_corrections_dict[key] = {
                        "original": sentences[sentence_idx],
                        "corrections": [item]
                    }
                    all_issues.append({
                        "original": sentences[sentence_idx],
                        "correction": item
                    })
                else:  # vocabulary
                    vocabulary_suggestions_dict[key] = {
                        "original": sentences[sentence_idx],
                        "suggestions": [item]
                    }
                    all_issues.append({
                        "original": sentences[sentence_idx],
                        "correction": {
                            "explanation": f"Consider using more advanced vocabulary ({item.get('level', 'B1')}): '{item['original_phrase']}' could be '{item['suggested_correction']}'",
                            "original_phrase": item["original_phrase"],
                            "suggested_correction": item["suggested_correction"],
                            "sentence_index": sentence_idx,
                            "sentence_text": sentences[sentence_idx]
                        }
                    })
        
        # Calculate grade
        total_issues = len(all_issues)
        if total_issues == 0:
            grade = 100
        elif total_issues <= 2:
            grade = 90
        elif total_issues <= 4:
            grade = 80
        elif total_issues <= 6:
            grade = 70
        else:
            grade = max(60 - (total_issues - 6) * 5, 0)
        
        return {
            "grade": grade,
            "issues": all_issues,
            "grammar_corrections": grammar_corrections_dict,
            "vocabulary_suggestions": vocabulary_suggestions_dict,
        }
        
    except Exception as e:
        logger.exception("Error in language analysis")
        return {
            "grade": 0,
            "issues": [{"original": "", "correction": {"explanation": f"Error analyzing grammar: {str(e)}", "original_phrase": "", "suggested_correction": ""}}],
            "grammar_corrections": {},
            "vocabulary_suggestions": {},
        } 