import re
import logging
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple

# Setup logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log startup information
logger.info("Starting language analysis service")

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

# Log API configuration (without the full key for security)
if OPENAI_API_KEY:
    masked_key = OPENAI_API_KEY[:10] + "..." + OPENAI_API_KEY[-5:]
    logger.info(f"Using OpenAI API with model: {MODEL}")
    logger.info(f"API Key configured: {masked_key}")
else:
    logger.warning("No OpenAI API key found. Some functionality will be limited.")
async def call_openai_with_retry(prompt: str, expected_format: str = "list", max_retries: int = 2) -> Any:
    """
    Call OpenAI API with retry mechanism for format validation
    
    Args:
        prompt: The prompt to send to OpenAI
        expected_format: Expected format of response ("list" or "dict")
        max_retries: Maximum number of retry attempts
        
    Returns:
        Parsed content if successful, None otherwise
    """
    logger.info(f"Calling OpenAI API with format validation, expecting: {expected_format}")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, cannot make API call")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # For the first attempt, use the original prompt
    current_prompt = prompt
    
    for attempt in range(max_retries + 1):  # +1 for the initial attempt
        try:
            if attempt > 0:
                # For retry attempts, modify the prompt to emphasize format requirements
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
            
            start_time = __import__('time').time()
            
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    response_time = __import__('time').time() - start_time
                    logger.info(f"OpenAI API responded in {response_time:.2f} seconds with status: {response.status}")
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Clean up content if it contains markdown code blocks
                        if "```json" in content or "```" in content:
                            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
                            match = re.search(json_pattern, content, re.DOTALL)
                            if match:
                                content = match.group(1)
                                logger.info("Extracted JSON from markdown code block")
                        
                        try:
                            parsed_content = json.loads(content)
                            
                            # Validate the format
                            format_valid = False
                            if expected_format == "list" and isinstance(parsed_content, list):
                                format_valid = True
                            elif expected_format == "dict" and isinstance(parsed_content, dict):
                                format_valid = True
                                
                            if format_valid:
                                logger.info(f"Successfully parsed content in expected {expected_format} format")
                                return parsed_content
                            else:
                                logger.warning(f"Content not in expected format. Got {type(parsed_content)}, expected {expected_format}")
                                if attempt == max_retries:
                                    logger.error("Max retries reached, returning None")
                                    return None
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}")
                            logger.debug(f"Raw content: {content[:300]}...")
                            if attempt == max_retries:
                                logger.error("Max retries reached, returning None")
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
async def analyze_grammar(transcript: str) -> Dict[str, Any]:
    """
    Analyze grammar and vocabulary in a transcript
    """
    logger.info(f"Starting grammar analysis for transcript of length: {len(transcript)}")
    
    if not transcript or not transcript.strip():
        logger.warning("Empty transcript provided, returning empty results")
        return {
            "grammar_corrections": {},
            "vocabulary_suggestions": {}
        }
        
    try:
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences for grammar and vocabulary")
        
        grammar_results = {}
        vocab_results = {}
        
        logger.info("Starting grammar correction process")
        grammar_corrections = await check_grammar(sentences)
        logger.info(f"Received {sum(1 for corr in grammar_corrections if corr)} sentences with grammar corrections")
        
        for i, corrections in enumerate(grammar_corrections):
            if corrections:
                logger.debug(f"Found {len(corrections)} grammar corrections for sentence {i+1}")
                grammar_results[f"sentence_{i+1}"] = {
                    "original": sentences[i],
                    "corrections": corrections
                }
        
        vocab_candidates = [
            (i, sent) for i, sent in enumerate(sentences)
            if f"sentence_{i+1}" not in grammar_results and len(sent.split()) > 5
        ]
        
        original_count = len(vocab_candidates)
        vocab_candidates = vocab_candidates[:min(5, len(vocab_candidates))]
        logger.info(f"Selected {len(vocab_candidates)} sentences for vocabulary suggestions out of {original_count} candidates")
        
        if vocab_candidates:
            logger.info("Starting vocabulary suggestion process")
            vocabulary_suggestions = await suggest_advanced_vocabulary([sent for _, sent in vocab_candidates])
            logger.info(f"Received vocabulary suggestions for {sum(1 for sugg in vocabulary_suggestions if sugg)} sentences")
            
            for i, suggestions in enumerate(vocabulary_suggestions):
                if suggestions:
                    orig_idx, sent = vocab_candidates[i]
                    logger.debug(f"Found {len(suggestions)} vocabulary suggestions for sentence {orig_idx+1}")
                    vocab_results[f"sentence_{orig_idx+1}"] = {
                        "original": sent,
                        "suggestions": suggestions
                    }
        else:
            logger.info("No sentences selected for vocabulary suggestions")
        
        logger.info(f"Analysis complete. Found grammar issues in {len(grammar_results)} sentences and vocabulary suggestions for {len(vocab_results)} sentences")
        return {
            "grammar_corrections": grammar_results,
            "vocabulary_suggestions": vocab_results
        }
        
    except Exception as e:
        logger.exception("Error in grammar analysis")
        return {
            "grammar_corrections": {"error": str(e)},
            "vocabulary_suggestions": {}
        }

def split_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences using regex
    """
    logger.info("Splitting text into sentences")
    text = re.sub(r'\s+', ' ', text).strip()
    
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(sentence_pattern, text)
    
    result = [s.strip() for s in sentences if s.strip()]
    logger.info(f"Split text into {len(result)} sentences")
    
    # Log first few sentences for debugging
    if result:
        sample = result[:min(3, len(result))]
        logger.debug(f"Sample sentences: {sample}")
    
    return result

async def check_grammar(sentences: List[str]) -> List[List[Dict[str, str]]]:
    """
    Check grammar for each sentence and return corrections with format validation and retry
    """
    logger.info(f"Checking grammar for {len(sentences)} sentences")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty grammar corrections")
        return [[] for _ in sentences]
    
    try:
        # Batch analysis for efficiency
        prompt = prompt = """
You are an expert in analyzing spoken English grammar. Analyze the following transcript from a spoken response, focusing only on actual grammar mistakes that would be considered errors even in casual spoken American English.

Important: Since this is transcribed speech, IGNORE:
- Disfluencies (e.g., "um", "uh") and filler words
- Minor punctuation or capitalization issues
- Natural speech patterns like contractions ("gonna", "wanna")
- Sentence fragments that are normal in conversation
- Minor word repetitions or self-corrections
- Regional speech patterns or dialects

ONLY focus on clear grammar mistakes that would be noticed in everyday speech:
1. Subject-verb agreement (e.g., "he don't" instead of "he doesn't")
2. Incorrect verb tenses (e.g., "yesterday I go" instead of "yesterday I went")
3. Missing or wrong articles when they affect meaning
4. Incorrect plural/singular forms
5. Word order that causes confusion
6. Preposition errors that sound unnatural to native speakers
7. Run-on sentences that create confusion

Provide a list of corrections for each sentence in **structured JSON format**, even if no corrections are needed (return an empty array for those). Each correction should include:
- "original_phrase": the problematic phrase from the sentence  
- "suggested_correction": the corrected version  
- "explanation": a brief, clear explanation of why this would be considered an error even in casual spoken American English

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
        
        # Call OpenAI API with retry and format validation
        corrections = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if corrections is None:
            logger.warning("Failed to get valid corrections after retries, returning empty results")
            return [[] for _ in sentences]
        
        # Ensure we have corrections for all sentences
        while len(corrections) < len(sentences):
            corrections.append([])
            logger.warning("Added empty corrections for missing sentences")
            
        # Trim if we got more corrections than sentences
        if len(corrections) > len(sentences):
            logger.warning(f"Got {len(corrections)} corrections for {len(sentences)} sentences, trimming")
            corrections = corrections[:len(sentences)]
        
        # Log statistics
        sentences_with_corrections = sum(1 for corr in corrections if corr)
        total_corrections = sum(len(corr) for corr in corrections if corr)
        logger.info(f"Found {total_corrections} grammar issues in {sentences_with_corrections} sentences")
        
        return corrections
                
    except Exception as e:
        logger.exception(f"Error in grammar checking: {str(e)}")
        return [[] for _ in sentences]
async def suggest_advanced_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]:
    """
    Suggest advanced C1/C2 level vocabulary alternatives with format validation and retry
    """
    logger.info(f"Suggesting advanced vocabulary for {len(sentences)} sentences")
    
    if not sentences:
        logger.warning("No sentences provided for vocabulary suggestions")
        return []
        
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning empty vocabulary suggestions")
        return [[] for _ in sentences]
    
    try:
        # Create prompt for advanced vocabulary suggestions
        prompt = """You are a language expert specializing in C1/C2 level English vocabulary enhancement.
        
        For each of the following sentences, identify basic or intermediate (B1/B2 level) words that could be replaced 
        with more sophisticated C1/C2 level alternatives. Suggest 2-3 advanced alternatives for each basic word.
        
        Focus on:
        1. Common verbs (like "get", "make", "do", "say")
        2. Basic adjectives (like "good", "bad", "big", "small")
        3. Simple adverbs (like "very", "really", "a lot")
        4. General nouns that could be more specific
        
        Present the results in a structured JSON format like this:
        [
            [  // suggestions for sentence 1
                {
                    "original_word": "good",
                    "context": "the project was good",
                    "advanced_alternatives": ["exceptional", "outstanding", "exemplary"],
                    "level": "C1"
                },
                // more suggestions if any
            ],
            // empty array [] if no suggestions for this sentence
            [],
            // and so on for each sentence
        ]
        
        Here are the sentences to analyze:
        """
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with vocabulary suggestions. No other text or markdown formatting."
        
        # Call OpenAI API with retry and format validation
        suggestions = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if suggestions is None:
            logger.warning("Failed to get valid suggestions after retries, returning empty results")
            return [[] for _ in sentences]
        
        # Ensure we have suggestions for all sentences
        while len(suggestions) < len(sentences):
            suggestions.append([])
            logger.warning("Added empty suggestions for missing sentences")
            
        # Trim if we got more suggestions than sentences
        if len(suggestions) > len(sentences):
            logger.warning(f"Got {len(suggestions)} suggestions for {len(sentences)} sentences, trimming")
            suggestions = suggestions[:len(sentences)]
        
        # Log statistics
        sentences_with_suggestions = sum(1 for sugg in suggestions if sugg)
        total_suggestions = sum(len(sugg) for sugg in suggestions if sugg)
        logger.info(f"Found {total_suggestions} vocabulary suggestions in {sentences_with_suggestions} sentences")
        
        return suggestions
                
    except Exception as e:
        logger.exception(f"Error in vocabulary suggestion: {str(e)}")
        return [[] for _ in sentences]
    
logger.info("Language analysis module loaded and ready")