import logging
import aiohttp
import json
from typing import Dict, List, Any
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
from app.models.vocabulary_model import VocabularySuggestion, VocabularyFeedback
from app.utils.vocabulary_utils import vocabulary_tools

# Setup logging
logger = logging.getLogger(__name__)

MODEL = "gpt-4"

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
        
        prompt = """You are an expert in English vocabulary analysis specializing in CEFR levels and word usage.
        
        For each of the following sentences, identify:
        
        1. Basic level words (A1-A2) that could be replaced with more advanced vocabulary
        2. Words that are used in an incorrect or unnatural context
        3. Opportunities to use more sophisticated vocabulary, even if the current word is already advanced
        
        IMPORTANT: When suggesting replacements, you MUST follow this progression:
        - For A1 words, suggest ONLY A2 alternatives
        - For A2 words, suggest ONLY B1 alternatives
        - For B1 words, suggest ONLY B2 alternatives
        - For B2 words, suggest ONLY C1 alternatives
        
        Never skip levels in your suggestions. Each suggestion should be exactly one level higher than the original word.
        
        Look carefully for opportunities to improve vocabulary, even in advanced text. For example:
        - If you see a B2 word, consider if there's a C1 alternative that would be more precise or impactful
        - If you see a B1 word, consider if there's a B2 alternative that would be more sophisticated
        - Don't assume that advanced words can't be improved
        
        For each issue identified, provide:
        - The original word
        - A suggested replacement word
        - The CEFR level of both words
        - A brief explanation of why the change would improve the text
        - Example usage of the suggested word
        
        Present the results in a structured JSON format like this:
        [
            [  // suggestions for sentence 1
                {
                    "original_word": "[word_from_text]",
                    "suggested_word": "[better_alternative]",
                    "original_level": "[CEFR_level]",
                    "suggested_level": "[higher_CEFR_level]",
                    "explanation": "[reason_for_improvement]",
                    "examples": ["[example_sentence_with_suggested_word]"]
                }
            ],
            [], // sentence 2: no issues found
            [ ... ], // sentence 3: any issues found
            ...
        ]
        
        ONLY analyze the actual words present in the sentences provided below. Do not suggest changes for words that are not in the text.
        
        Here are the sentences to analyze:
        """
        
        for i, sentence in enumerate(sentences):
            prompt += f"\n{i+1}. {sentence}"
        
        prompt += "\n\nProvide ONLY the JSON array with vocabulary suggestions. No other text or markdown formatting."
        
        vocabulary_analysis = await call_openai_with_retry(prompt, expected_format="list", max_retries=2)
        
        if vocabulary_analysis is None:
            return {
                "grade": 50,
                "issues": [{"type": "vocabulary", "sentence": "", "suggestion": {"explanation": "Unable to analyze vocabulary due to API issues.", "original_word": "", "suggested_word": ""}}],
                "vocabulary_suggestions": {}
            }

        # Enhance vocabulary analysis with context
        enhanced_vocabulary_analysis = enhance_vocabulary_suggestions_with_context(sentences, vocabulary_analysis)

        # Convert the API response to standardized format
        vocabulary_suggestions = {}
        total_suggestions = 0
        
        for i, sentence_suggestions in enumerate(enhanced_vocabulary_analysis):
            if i < len(sentences) and sentence_suggestions:
                for suggestion in sentence_suggestions:
                    key = f"{i}_{suggestion.get('phrase_index', 0)}"
                    vocabulary_suggestions[key] = {
                        "original_word": suggestion.get("original_word", ""),
                        "suggested_word": suggestion.get("suggested_word", ""),
                        "original_level": suggestion.get("original_level", ""),
                        "suggested_level": suggestion.get("suggested_level", ""),
                        "word_type": "unknown",  # Could be enhanced with POS tagging
                        "examples": suggestion.get("examples", []),
                        "explanation": suggestion.get("explanation", ""),
                        "sentence_index": i,
                        "phrase_index": suggestion.get("phrase_index", 0),
                        "sentence_text": sentences[i]
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

        return {
            "grade": grade,
            "vocabulary_suggestions": vocabulary_suggestions
        }

    except Exception as e:
        logger.exception(f"Error in vocabulary analysis: {str(e)}")
        return {
            "grade": 0,
            "vocabulary_suggestions": {}
        } 