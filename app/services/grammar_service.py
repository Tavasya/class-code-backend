import re
import logging
import aiohttp
import json
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

# Setup logging
logger = logging.getLogger(__name__)

MODEL = "gpt-4"

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
            "issues": []
        }
        
    try:
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences")
        
        # 1. Grammar corrections
        grammar_corrections = await check_grammar(sentences)
        
        # 2. Vocabulary suggestions for sentences without grammar issues
        vocab_candidates = []
        grammar_issues = []
        
        # Process grammar corrections
        for i, corrections in enumerate(grammar_corrections):
            if corrections:
                for correction in corrections:
                    grammar_issues.append({
                        "original": sentences[i],
                        "correction": {
                            "explanation": correction.get("explanation", ""),
                            "original_phrase": correction.get("original_phrase", ""),
                            "suggested_correction": correction.get("suggested_correction", "")
                        }
                    })
            else:
                # No grammar issues, candidate for vocabulary suggestions
                vocab_candidates.append((i, sentences[i]))
        
        # Get vocabulary suggestions for sentences without grammar issues
        vocab_issues = []
        if vocab_candidates:
            vocabulary_suggestions = await suggest_vocabulary([sent for _, sent in vocab_candidates])
            
            for j, suggestions in enumerate(vocabulary_suggestions):
                if suggestions:
                    orig_idx, sent = vocab_candidates[j]
                    for suggestion in suggestions:
                        vocab_issues.append({
                            "original": sent,
                            "correction": {
                                "explanation": f"Consider using more advanced vocabulary: '{suggestion.get('original_word', '')}' could be '{', '.join(suggestion.get('advanced_alternatives', []))}'",
                                "original_phrase": suggestion.get('original_word', ''),
                                "suggested_correction": ', '.join(suggestion.get('advanced_alternatives', []))
                            }
                        })
        
        # Combine all issues
        all_issues = grammar_issues + vocab_issues
        
        # Calculate grade based on number of issues
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
            "issues": all_issues
        }
        
    except Exception as e:
        logger.exception("Error in language analysis")
        return {
            "grade": 0,
            "issues": [{"original": "", "correction": {"explanation": f"Error analyzing grammar: {str(e)}", "original_phrase": "", "suggested_correction": ""}}]
        } 