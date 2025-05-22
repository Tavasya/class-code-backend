import logging
import aiohttp
import json
import os
import re
from typing import Dict, List, Any
from app.models.fluency_model import FluencyRequest, FluencyResponse, WordDetail

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4"

async def call_api_with_retry(prompt: str, expected_format: str = "dict", max_retries: int = 2) -> Any:
    """Call OpenAI API with retry mechanism for format validation"""
    logger.info(f"Calling API for fluency analysis, expecting: {expected_format}")
    
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
                You MUST ONLY return a valid JSON {expected_format} without any explanation text or code blocks.
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
                        
                        if "```json" in content or "```" in content:
                            json_pattern = r"```(?:json)?\s*(.*?)\s*```"
                            match = re.search(json_pattern, content, re.DOTALL)
                            if match:
                                content = match.group(1)
                        
                        try:
                            parsed_content = json.loads(content)
                            if (expected_format == "dict" and isinstance(parsed_content, dict)) or \
                               (expected_format == "list" and isinstance(parsed_content, list)):
                                return parsed_content
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

def calculate_timing_metrics(word_details: List[WordDetail]) -> Dict[str, Any]:
    """Calculate timing-based metrics for fluency analysis"""
    if not word_details or len(word_details) < 2:
        return {}
    
    try:
        first_word_start = word_details[0].offset
        last_word_end = word_details[-1].offset + word_details[-1].duration
        total_duration = last_word_end - first_word_start
        
        if total_duration <= 0:
            return {}
        
        word_count = len(word_details)
        words_per_minute = (word_count / total_duration) * 60
        
        pauses = []
        total_pause_duration = 0
        
        for i in range(1, len(word_details)):
            prev_word_end = word_details[i-1].offset + word_details[i-1].duration
            current_word_start = word_details[i].offset
            
            pause_duration = current_word_start - prev_word_end
            if pause_duration > 0.3:
                pauses.append(pause_duration)
                total_pause_duration += pause_duration
        
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
    """Get comprehensive fluency and coherence analysis using OpenAI"""
    if not OPENAI_API_KEY:
        raise ValueError("No API key available")
    
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
    """
    
    analysis = await call_api_with_retry(prompt, expected_format="dict")
    if not analysis:
        raise ValueError("Failed to get valid analysis from API")
    
    return analysis

async def analyze_fluency(request: FluencyRequest) -> FluencyResponse:
    """Main function to analyze fluency and coherence"""
    try:
        timing_metrics = calculate_timing_metrics(request.word_details)
        analysis_result = await get_fluency_coherence_analysis(request.reference_text, timing_metrics)
        
        return FluencyResponse(
            status="success",
            **analysis_result
        )
        
    except Exception as e:
        logger.exception("Error in fluency analysis")
        return FluencyResponse(
            status="error",
            error=str(e),
            fluency_metrics={
                "speech_rate": 0,
                "hesitation_ratio": 0,
                "pause_pattern_score": 0,
                "overall_fluency_score": 0
            },
            coherence_metrics={
                "topic_consistency": 0,
                "logical_flow": 0,
                "idea_development": 0,
                "overall_coherence_score": 0
            },
            key_findings=[],
            improvement_suggestions=[]
        )
