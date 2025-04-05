import re
import logging
import aiohttp
import json
import os
from typing import Dict, List, Any, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"  # Use the model specified in requirements

async def analyze_grammar(transcript: str) -> Dict[str, Any]:
    """
    Analyze grammar and vocabulary in a transcript
    """
    if not transcript or not transcript.strip():
        return {
            "grammar_corrections": {},
            "vocabulary_suggestions": {}
        }
        
    try:
        # Split the transcript into sentences
        sentences = split_into_sentences(transcript)
        logger.info(f"Analyzing {len(sentences)} sentences for grammar and vocabulary")
        
        # Initialize results
        grammar_results = {}
        vocab_results = {}
        
        # Check grammar for all sentences
        grammar_corrections = await check_grammar(sentences)
        for i, corrections in enumerate(grammar_corrections):
            if corrections:
                grammar_results[f"sentence_{i+1}"] = {
                    "original": sentences[i],
                    "corrections": corrections
                }
        
        # Check vocabulary for improvement (using a subset to limit API usage)
        # Choose sentences that don't have grammar errors for vocab suggestions
        vocab_candidates = [
            (i, sent) for i, sent in enumerate(sentences)
            if f"sentence_{i+1}" not in grammar_results and len(sent.split()) > 5
        ]
        
        # Limit to max 5 sentences for vocabulary analysis
        vocab_candidates = vocab_candidates[:min(5, len(vocab_candidates))]
        
        if vocab_candidates:
            vocabulary_suggestions = await suggest_advanced_vocabulary([sent for _, sent in vocab_candidates])
            
            for i, suggestions in enumerate(vocabulary_suggestions):
                if suggestions:
                    orig_idx, sent = vocab_candidates[i]
                    vocab_results[f"sentence_{orig_idx+1}"] = {
                        "original": sent,
                        "suggestions": suggestions
                    }
        
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
    # Clean the text - remove excessive spaces, newlines, etc.
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Split on sentence boundaries
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s'
    sentences = re.split(sentence_pattern, text)
    
    # Remove empty sentences and clean each sentence
    return [s.strip() for s in sentences if s.strip()]

async def check_grammar(sentences: List[str]) -> List[List[Dict[str, str]]]:
    """
    Check grammar for each sentence and return corrections
    """
    if not OPENAI_API_KEY:
        # Return empty corrections if no API key
        return [[] for _ in sentences]
    
    try:
        # Batch analysis for efficiency
        prompt = """You are a language expert specializing in English grammar correction and analysis.
        
        Analyze the following sentences for grammatical errors. Focus on:
        1. Subject-verb agreement
        2. Verb tense consistency
        3. Article usage
        4. Plural/singular forms
        5. Word order and syntax
        6. Preposition usage
        
        For each sentence, provide a detailed list of corrections with explanations. Be thorough and detect all errors.
        
        Present the results in a structured JSON format like this:
        [
            [  // corrections for sentence 1
                {
                    "original_phrase": "the incorrect phrase",
                    "suggested_correction": "the correct phrase",
                    "explanation": "detailed grammatical explanation"
                },
                // more corrections if any
            ],
            // empty array [] if no corrections needed for this sentence
            [],
            // and so on for each sentence
        ]
        
        Here are the sentences to analyze:
        """
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with corrections. No other text."
        
        # Call OpenAI API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        logger.info("Calling OpenAI API for grammar analysis")
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    try:
                        corrections = json.loads(content)
                        # Ensure we have the right structure
                        if isinstance(corrections, list):
                            # Fill missing sentences with empty arrays
                            while len(corrections) < len(sentences):
                                corrections.append([])
                            return corrections
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse OpenAI response: {content}")
                
                # Return empty corrections if API call fails
                return [[] for _ in sentences]
                
    except Exception as e:
        logger.exception("Error in grammar checking")
        return [[] for _ in sentences]

async def suggest_advanced_vocabulary(sentences: List[str]) -> List[List[Dict[str, Any]]]:
    """
    Suggest advanced C1/C2 level vocabulary alternatives
    """
    if not sentences or not OPENAI_API_KEY:
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
        
        prompt += "\n\nProvide ONLY the JSON array with vocabulary suggestions. No other text."
        
        # Call OpenAI API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "response_format": {"type": "json_object"}
        }
        
        logger.info("Calling OpenAI API for vocabulary suggestions")
        async with aiohttp.ClientSession() as session:
            async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    try:
                        suggestions = json.loads(content)
                        # Ensure we have the right structure
                        if isinstance(suggestions, list):
                            # Fill missing sentences with empty arrays
                            while len(suggestions) < len(sentences):
                                suggestions.append([])
                            return suggestions
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse OpenAI response: {content}")
                
                # Return empty suggestions if API call fails
                return [[] for _ in sentences]
                
    except Exception as e:
        logger.exception("Error in vocabulary suggestion")
        return [[] for _ in sentences]