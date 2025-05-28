import re
import logging
import aiohttp
import json
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

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

async def check_grammar(sentences: List[str]) -> List[List[Dict[str, str]]]:
    """Check grammar for each sentence and return corrections"""
    logger.info(f"Checking grammar for {len(sentences)} sentences")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty grammar corrections")
        return [[] for _ in sentences]
    
    try:
        prompt = """
You are an expert in English grammar and spoken communication. Analyze the following transcript, which is based on a spoken response. Since it is derived from speech, ignore disfluencies (e.g., "um", "uh"), filler words, and transcription-related punctuation issues.

Your job is to:
- Detect and correct grammar mistakes related to:
  1. Subject-verb agreement  
  2. Verb tense consistency  
  3. Article usage (a, an, the)  
  4. Singular/plural form  
  5. Word order and sentence structure  
  6. Preposition use  
  7. Sentence completeness (fragments, run-ons)

Provide a list of corrections for each sentence in **structured JSON format**, even if no corrections are needed (return an empty array for those). Each correction should include:
- "original_phrase": the problematic phrase from the sentence  
- "suggested_correction": the corrected version  
- "explanation": a brief, clear explanation of the issue

Output format:
[
    [  // corrections for sentence 1
        {
            "original_phrase": "the incorrect phrase",
            "suggested_correction": "the correct phrase",
            "explanation": "reason for correction"
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
            return [[] for _ in sentences]
        
        while len(corrections) < len(sentences):
            corrections.append([])
            
        if len(corrections) > len(sentences):
            corrections = corrections[:len(sentences)]
        
        return corrections
                
    except Exception as e:
        logger.exception(f"Error in grammar checking: {str(e)}")
        return [[] for _ in sentences]

async def suggest_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]:
    """Suggest intermediate B1/B2 level vocabulary alternatives"""
    logger.info(f"Suggesting intermediate vocabulary for {len(sentences)} sentences")
    
    if not sentences:
        return []
        
    if not OPENAI_API_KEY:
        return [[] for _ in sentences]
    
    try:
        prompt = """You are a language expert specializing in B1/B2 level English vocabulary enhancement.
        
        For each of the following sentences, identify basic (A1/A2 level) words that could be replaced
        with more appropriate B1/B2 level alternatives. Suggest 2-3 intermediate alternatives for each basic word.
        
        Focus on:
        1. Very basic verbs (like "get", "put", "go", "come")
        2. Simple adjectives (like "nice", "bad", "big", "small")
        3. Basic adverbs (like "very", "really", "a lot") 
        4. General nouns that could be more specific
        
        Present the results in a structured JSON format like this:
        [
            [  // suggestions for sentence 1
                {
                    "original_word": "nice",
                    "context": "the project was nice",
                    "advanced_alternatives": ["pleasant", "enjoyable", "interesting"],
                    "level": "B1"
                }
            ],
            [], // sentence 2: no suggestions
            [ ... ], // sentence 3: suggestions
            ...
        ]
        
        Here are the sentences to analyze:
        """
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with vocabulary suggestions. No other text or markdown formatting."
        
        suggestions = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if suggestions is None:
            return [[] for _ in sentences]
        
        while len(suggestions) < len(sentences):
            suggestions.append([])
            
        if len(suggestions) > len(sentences):
            suggestions = suggestions[:len(sentences)]
        
        return suggestions
        
    except Exception as e:
        logger.exception(f"Error in vocabulary suggestion: {str(e)}")
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
            "lexical_resources": {}
        }
        
    try:
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences")
        
        # 1. Get grammar corrections for all sentences
        grammar_corrections = await check_grammar(sentences)
        
        # 2. Enhance grammar corrections with context
        enhanced_grammar_corrections = enhance_grammar_corrections_with_context(sentences, grammar_corrections)
        
        # 3. Get vocabulary suggestions for sentences without grammar issues
        vocab_candidate_sentences = []
        vocab_candidate_indices = []
        
        for i, corrections in enumerate(grammar_corrections):
            if not corrections:  # No grammar issues in this sentence
                vocab_candidate_sentences.append(sentences[i])
                vocab_candidate_indices.append(i)
        
        # Get vocabulary suggestions only for sentences without grammar issues
        vocabulary_suggestions = []
        if vocab_candidate_sentences:
            vocab_raw = await suggest_vocabulary(vocab_candidate_sentences)
            
            # Map back to original sentence indices and enhance with context
            vocabulary_suggestions = [[] for _ in sentences]  # Initialize for all sentences
            for j, suggestions in enumerate(vocab_raw):
                original_sentence_idx = vocab_candidate_indices[j]
                vocabulary_suggestions[original_sentence_idx] = suggestions
        else:
            vocabulary_suggestions = [[] for _ in sentences]
        
        # 4. Enhance vocabulary suggestions with context
        enhanced_vocabulary_suggestions = enhance_vocabulary_suggestions_with_context(sentences, vocabulary_suggestions)
        
        # 5. Convert to the expected format for backwards compatibility
        grammar_issues = []
        vocab_issues = []
        
        # Process enhanced grammar corrections
        for sentence_idx, sentence_corrections in enumerate(enhanced_grammar_corrections):
            for correction in sentence_corrections:
                grammar_issues.append({
                    "original": sentences[sentence_idx],
                    "correction": {
                        "explanation": correction.get("explanation", ""),
                        "original_phrase": correction.get("original_phrase", ""),
                        "suggested_correction": correction.get("suggested_correction", ""),
                        "sentence_index": correction.get("sentence_index"),
                        "phrase_index": correction.get("phrase_index"),
                        "sentence_text": correction.get("sentence_text")
                    }
                })
        
        # Process enhanced vocabulary suggestions
        for sentence_idx, sentence_suggestions in enumerate(enhanced_vocabulary_suggestions):
            for suggestion in sentence_suggestions:
                vocab_issues.append({
                    "original": sentences[sentence_idx],
                    "correction": {
                        "explanation": f"Consider using more advanced vocabulary: '{suggestion.get('original_word', '')}' could be '{', '.join(suggestion.get('advanced_alternatives', []))}'",
                        "original_phrase": suggestion.get('original_word', ''),
                        "suggested_correction": ', '.join(suggestion.get('advanced_alternatives', [])),
                        "sentence_index": suggestion.get("sentence_index"),
                        "phrase_index": suggestion.get("phrase_index"),
                        "sentence_text": suggestion.get("sentence_text")
                    }
                })
        
        # 6. Combine all issues for grade calculation
        all_issues = grammar_issues + vocab_issues
        
        # 7. Calculate grade based on number of issues
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
        
        # 8. Format enhanced results for new API structure
        grammar_corrections_dict = {}
        vocabulary_suggestions_dict = {}
        
        for sentence_idx, sentence_corrections in enumerate(enhanced_grammar_corrections):
            if sentence_corrections:
                for j, correction in enumerate(sentence_corrections):
                    key = f"sentence_{sentence_idx}_{j}"
                    grammar_corrections_dict[key] = {
                        "original": sentences[sentence_idx],
                        "corrections": [correction]
                    }
        
        for sentence_idx, sentence_suggestions in enumerate(enhanced_vocabulary_suggestions):
            if sentence_suggestions:
                for j, suggestion in enumerate(sentence_suggestions):
                    key = f"sentence_{sentence_idx}_{j}"
                    vocabulary_suggestions_dict[key] = {
                        "original": sentences[sentence_idx],
                        "suggestions": [suggestion]
                    }
        
        return {
            "grade": grade,
            "issues": all_issues,
            "grammar_corrections": grammar_corrections_dict,
            "vocabulary_suggestions": vocabulary_suggestions_dict,
            "lexical_resources": {}  # Placeholder for future lexical integration
        }
        
    except Exception as e:
        logger.exception("Error in language analysis")
        return {
            "grade": 0,
            "issues": [{"original": "", "correction": {"explanation": f"Error analyzing grammar: {str(e)}", "original_phrase": "", "suggested_correction": ""}}],
            "grammar_corrections": {},
            "vocabulary_suggestions": {},
            "lexical_resources": {}
        } 