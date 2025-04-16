import logging
import aiohttp
import json
import os
import re
from typing import Dict, List, Any, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"

async def call_api_with_retry(prompt: str, expected_format: str = "dict", max_retries: int = 2) -> Any:
    """
    Call OpenAI API with retry mechanism for format validation
    
    Args:
        prompt: The prompt to send to OpenAI
        expected_format: Expected format of response ("dict" or "list")
        max_retries: Maximum number of retry attempts
        
    Returns:
        Parsed content if successful, None otherwise
    """
    logger.info(f"Calling API for fluency analysis, expecting: {expected_format}")
    
    if not OPENAI_API_KEY:
        logger.warning("No API key available, cannot make API call")
        return None
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # For the first attempt, use the original prompt
    current_prompt = prompt
    
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                # For retry attempts, emphasize format requirements
                format_emphasis = f"""
                IMPORTANT: Your previous response was not in the expected JSON format.
                You MUST ONLY return a valid JSON {expected_format} without any explanation text or code blocks.
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
                        
                        # Clean up content if it contains markdown code blocks
                        if "```json" in content or "```" in content:
                            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
                            match = re.search(json_pattern, content, re.DOTALL)
                            if match:
                                content = match.group(1)
                        
                        try:
                            parsed_content = json.loads(content)
                            
                            # Validate format
                            format_valid = False
                            if expected_format == "dict" and isinstance(parsed_content, dict):
                                format_valid = True
                            elif expected_format == "list" and isinstance(parsed_content, list):
                                format_valid = True
                                
                            if format_valid:
                                logger.info(f"Successfully parsed content in expected {expected_format} format")
                                return parsed_content
                            else:
                                logger.warning(f"Content not in expected format. Got {type(parsed_content)}, expected {expected_format}")
                                if attempt == max_retries:
                                    return None
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse JSON")
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

async def analyze_fluency_coherence(transcript: str, word_details: List[Dict] = None) -> Dict[str, Any]:
    """
    Analyze fluency and coherence in a transcript
    
    Args:
        transcript: The speech transcript
        word_details: Optional timing information from pronunciation assessment
        
    Returns:
        Dictionary with fluency and coherence metrics
    """
    logger.info(f"Starting fluency and coherence analysis for transcript of length: {len(transcript)}")
    
    if not transcript or not transcript.strip():
        logger.warning("Empty transcript provided, returning default scores")
        return {
            "fluency_metrics": {
                "speech_rate": 0,
                "hesitation_ratio": 0,
                "pause_pattern_score": 0,
                "overall_fluency_score": 0
            },
            "coherence_metrics": {
                "topic_consistency": 0,
                "logical_flow": 0,
                "idea_development": 0,
                "overall_coherence_score": 0
            },
            "key_findings": [],
            "improvement_suggestions": []
        }
    
    try:
        # Calculate timing-based metrics if word_details are provided
        timing_metrics = {}
        if word_details and len(word_details) > 0:
            timing_metrics = calculate_timing_metrics(word_details)
        
        # Use LLM for deep analysis
        analysis_result = await get_fluency_coherence_analysis(transcript, timing_metrics)
        
        if not analysis_result:
            # Fallback to basic analysis if API call fails
            return generate_fallback_analysis(transcript, timing_metrics)
        
        logger.info("Successfully completed fluency and coherence analysis")
        return analysis_result
        
    except Exception as e:
        logger.exception("Error in fluency analysis")
        return {
            "fluency_metrics": {
                "speech_rate": 0,
                "hesitation_ratio": 0,
                "pause_pattern_score": 0,
                "overall_fluency_score": 0
            },
            "coherence_metrics": {
                "topic_consistency": 0,
                "logical_flow": 0, 
                "idea_development": 0,
                "overall_coherence_score": 0
            },
            "key_findings": [f"Error in analysis: {str(e)}"],
            "improvement_suggestions": ["Try speaking more clearly and organizing your thoughts before speaking."]
        }

def calculate_timing_metrics(word_details: List[Dict]) -> Dict[str, Any]:
    """
    Calculate timing-based metrics for fluency analysis
    
    Args:
        word_details: List of words with timing information
        
    Returns:
        Dictionary with timing metrics
    """
    if not word_details or len(word_details) < 2:
        return {}
    
    try:
        # Calculate total duration
        first_word_start = word_details[0].get("offset", 0)
        last_word_end = word_details[-1].get("offset", 0) + word_details[-1].get("duration", 0)
        total_duration = last_word_end - first_word_start
        
        if total_duration <= 0:
            return {}
        
        # Count words
        word_count = len(word_details)
        
        # Calculate speech rate (words per minute)
        words_per_minute = (word_count / total_duration) * 60
        
        # Calculate pauses (gaps between words > 0.3 seconds)
        pauses = []
        total_pause_duration = 0
        
        for i in range(1, len(word_details)):
            prev_word_end = word_details[i-1].get("offset", 0) + word_details[i-1].get("duration", 0)
            current_word_start = word_details[i].get("offset", 0)
            
            pause_duration = current_word_start - prev_word_end
            if pause_duration > 0.3:  # Threshold for counting as a pause
                pauses.append(pause_duration)
                total_pause_duration += pause_duration
        
        # Calculate hesitation ratio (pause time / speaking time)
        hesitation_ratio = total_pause_duration / total_duration if total_duration > 0 else 0
        
        return {
            "words_per_minute": round(words_per_minute, 1),
            "pause_count": len(pauses),
            "avg_pause_duration": round(sum(pauses) / len(pauses), 2) if pauses else 0,
            "pause_percentage": round((total_pause_duration / total_duration) * 100, 1) if total_duration > 0 else 0,
            "hesitation_ratio": round(hesitation_ratio, 2)
        }
        
    except Exception as e:
        logger.error(f"Error calculating timing metrics: {str(e)}")
        return {}

async def get_fluency_coherence_analysis(transcript: str, timing_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get comprehensive fluency and coherence analysis using OpenAI
    
    Args:
        transcript: The speech transcript
        timing_metrics: Calculated timing-based metrics
        
    Returns:
        Dictionary with fluency and coherence analysis
    """
    if not OPENAI_API_KEY:
        logger.warning("No API key available, returning basic analysis")
        return generate_fallback_analysis(transcript, timing_metrics)
    
    # Create prompt with timing metrics if available
    timing_info = ""
    if timing_metrics:
        timing_info = f"""
        Timing metrics:
        - Words per minute: {timing_metrics.get('words_per_minute', 'N/A')}
        - Number of pauses: {timing_metrics.get('pause_count', 'N/A')}
        - Average pause duration: {timing_metrics.get('avg_pause_duration', 'N/A')} seconds
        - Pause percentage: {timing_metrics.get('pause_percentage', 'N/A')}%
        - Hesitation ratio: {timing_metrics.get('hesitation_ratio', 'N/A')}
        """
    
    prompt = f"""
    You are an expert in speech assessment focusing on fluency and coherence. Answer in 2nd person. Analyze the following transcript from a language learner:
    
    "{transcript}"
    
    {timing_info}
    
    Provide a detailed analysis of the speaker's fluency and coherence with numerical scores (0-100) and specific observations.
    
    Return ONLY a JSON object with the following structure:
    {{
        "fluency_metrics": {{
            "speech_rate": [0-100 score],
            "hesitation_ratio": [0-100 score],
            "pause_pattern_score": [0-100 score],
            "overall_fluency_score": [0-100 score]
        }},
        "coherence_metrics": {{
            "topic_consistency": [0-100 score],
            "logical_flow": [0-100 score],
            "idea_development": [0-100 score],
            "overall_coherence_score": [0-100 score]
        }},
        "key_findings": [
            "3-5 specific observations about fluency and coherence"
        ],
        "improvement_suggestions": [
            "2-3 concrete and actionable suggestions for improvement"
        ]
    }}
    
    Ensure your analysis considers:
    - Fluency: speech rate, pauses, hesitations, and natural flow
    - Coherence: logical organization, topic maintenance, and idea development
    """
    
    # Call API with retry and format validation
    analysis = await call_api_with_retry(prompt, expected_format="dict")
    
    if not analysis:
        logger.warning("Failed to get valid analysis, returning fallback")
        return generate_fallback_analysis(transcript, timing_metrics)
    
    return analysis

def generate_fallback_analysis(transcript: str, timing_metrics: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a basic analysis when API is unavailable
    
    Args:
        transcript: The speech transcript
        timing_metrics: Any available timing metrics
        
    Returns:
        Basic fluency and coherence analysis
    """
    # Basic heuristics for scoring
    word_count = len(transcript.split())
    
    # Estimate coherence based on sentence count and length
    sentences = re.split(r'[.!?]+', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    
    # Coherence heuristics
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
    coherence_score = min(100, max(0, 50 + (avg_sentence_length - 5) * 5)) if sentence_count > 0 else 40
    
    # Fluency heuristics from timing metrics
    fluency_score = 60  # Default base score
    
    if timing_metrics:
        wpm = timing_metrics.get('words_per_minute', 0)
        if wpm > 0:
            # Adjust fluency score based on words per minute
            # Ideal range: 120-150 WPM
            if wpm < 80:
                fluency_score -= 15  # Too slow
            elif wpm > 180:
                fluency_score -= 10  # Too fast
            elif 120 <= wpm <= 150:
                fluency_score += 15  # Ideal range
                
        # Adjust for hesitation
        hesitation = timing_metrics.get('hesitation_ratio', 0)
        if hesitation > 0.4:
            fluency_score -= 20  # Too many hesitations
        elif hesitation < 0.15:
            fluency_score += 10  # Few hesitations
    
    # Ensure scores are within 0-100 range
    fluency_score = min(100, max(0, fluency_score))
    coherence_score = min(100, max(0, coherence_score))
    
    # Generate basic findings and suggestions
    findings = []
    suggestions = []
    
    # Basic findings
    if word_count < 50:
        findings.append("The response is quite brief, which affects the development of ideas.")
    
    if sentence_count <= 1:
        findings.append("The response consists of very few sentences, limiting coherence assessment.")
    
    if timing_metrics and timing_metrics.get('words_per_minute', 0) < 80:
        findings.append("Speech rate is notably slow, which may affect the perceived fluency.")
    
    if timing_metrics and timing_metrics.get('hesitation_ratio', 0) > 0.3:
        findings.append("Frequent hesitations are present, interrupting the natural flow of speech.")
    
    # Basic suggestions
    suggestions.append("Practice speaking on familiar topics to build confidence and reduce hesitations.")
    suggestions.append("Try organizing thoughts into a clear beginning, middle, and end to improve coherence.")
    
    if timing_metrics and timing_metrics.get('pause_count', 0) > 5:
        suggestions.append("Work on reducing unnecessary pauses by practicing with a timer.")
    
    # Ensure we have at least some findings and suggestions
    if not findings:
        findings = ["Limited analysis available without detailed metrics."]
    
    if not suggestions:
        suggestions = ["Practice speaking regularly on various topics to improve overall fluency and coherence."]
    
    return {
        "fluency_metrics": {
            "speech_rate": int(fluency_score * 0.8) if timing_metrics and 'words_per_minute' in timing_metrics else 50,
            "hesitation_ratio": int(fluency_score * 0.7) if timing_metrics and 'hesitation_ratio' in timing_metrics else 50,
            "pause_pattern_score": int(fluency_score * 0.9) if timing_metrics and 'pause_count' in timing_metrics else 55,
            "overall_fluency_score": int(fluency_score)
        },
        "coherence_metrics": {
            "topic_consistency": int(coherence_score * 0.9),
            "logical_flow": int(coherence_score * 0.8),
            "idea_development": int(coherence_score * 0.7),
            "overall_coherence_score": int(coherence_score)
        },
        "key_findings": findings[:3],  # Limit to top 3
        "improvement_suggestions": suggestions[:2]  # Limit to top 2
    }