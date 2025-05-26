import logging
import aiohttp
import json
from typing import List, Dict, Any, Optional
from app.models.lexical_model import LexicalFeedback, LexicalCorrection
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

# Setup logging
logger = logging.getLogger(__name__)

# OpenAI API configuration
MODEL = "gpt-4"  # or your preferred model

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

async def analyze_lexical_resources(sentences: List[str]) -> Dict[str, Any]:
    """Analyze lexical resources in sentences and return feedback in standardized format"""
    if not sentences:
        return {
            "grade": 100,
            "issues": []
        }

    try:
        prompt = """You are an expert in English lexical resources specializing in collocations, idioms, and natural word usage.
        
        For each of the following sentences, identify:
        
        1. Collocations that are used incorrectly or unnaturally
        2. Idioms that are used incorrectly or could be used to enhance the sentence
        3. Word usage errors where a word is used in an incorrect or unnatural context
        4. Word combinations that don't follow conventional Oxford English patterns
        
        For each issue identified, provide:
        - The incorrect/unnatural phrase
        - The suggested correction with proper collocation/idiom usage
        - A brief explanation of the correction
        - The type of issue (collocation, idiom, or word_usage)
        
        Present the results in a structured JSON format like this:
        [
            [  // suggestions for sentence 1
                {
                    "original_phrase": "make a decision",
                    "suggested_phrase": "take a decision",
                    "explanation": "In English, decisions are typically 'taken' rather than 'made'",
                    "resource_type": "collocation"
                }
            ],
            [], // sentence 2: no issues
            [ ... ], // sentence 3: issues
            ...
        ]
        
        Here are the sentences to analyze:
        """
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with lexical resource suggestions. No other text or markdown formatting."
        
        lexical_analysis = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if lexical_analysis is None:
            return {
                "grade": 50,
                "issues": [{"type": "lexical", "sentence": "", "suggestion": {"explanation": "Unable to analyze lexical resources due to API issues.", "resource_type": "error", "original_phrase": "", "suggested_phrase": ""}}]
            }

        # Convert the API response to standardized format
        all_issues = []
        total_corrections = 0
        
        for i, sentence_corrections in enumerate(lexical_analysis):
            if i < len(sentences) and sentence_corrections:
                for correction in sentence_corrections:
                    all_issues.append({
                        "type": "lexical",
                        "sentence": sentences[i],
                        "suggestion": {
                            "explanation": correction.get("explanation", ""),
                            "resource_type": correction.get("resource_type", "word usage"),
                            "original_phrase": correction.get("original_phrase", ""),
                            "suggested_phrase": correction.get("suggested_phrase", "")
                        }
                    })
                    total_corrections += 1

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

        return {
            "grade": grade,
            "issues": all_issues
        }

    except Exception as e:
        logger.exception(f"Error in lexical analysis: {str(e)}")
        return {
            "grade": 0,
            "issues": [{"type": "lexical", "sentence": "", "suggestion": {"explanation": f"Error analyzing lexical resources: {str(e)}", "resource_type": "error", "original_phrase": "", "suggested_phrase": ""}}]
        } 