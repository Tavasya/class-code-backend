import logging
import aiohttp
import json
import os
import re
from typing import Dict, List, Any
from app.models.fluency_model import FluencyRequest, FluencyResponse, WordDetail
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI API configuration
MODEL = "gpt-4o-mini"

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
    You are an expert in speech assessment focusing on fluency, coherence, and the use of cohesive devices. Analyze the following transcript from a language learner:

    "{transcript}"

    {timing_info}

    Provide a detailed analysis. Your response MUST be ONLY a JSON object with the following structure:
    {{ 
        "grade": [0-100 overall fluency and coherence score],
        "issues": [
            "Specific observation about speech rate and fluency",
            "Observation about pause patterns and hesitation",
            "Comment on topic consistency and logical flow",
            "Note about idea development and coherence",
            "Actionable improvement suggestion"
        ],
        "cohesive_device_band_level": [Integer: 9, 7, 5, 3, or 1 based on the proficiency bands below],
        "cohesive_device_feedback": "[String: The specific feedback starting with 'Speech is...' for the identified band]"
    }}

    The overall 'grade' should be based on:
    - Speech rate and smoothness (25%)
    - Pause patterns and hesitation (25%)
    - Topic consistency and logical flow (25%)
    - Idea development and coherence (25%)

    'Issues' should be 4-6 specific, actionable observations written in 2nd person.

    For 'cohesive_device_band_level' and 'cohesive_device_feedback', use the following proficiency bands:
    - Band 9 (Expert Proficiency): Use of cohesive devices is natural and appropriate, enhancing clarity and flow.
      Feedback: "Speech is coherent and well-structured, with ideas developed fully and appropriately."
    - Band 7 (Good Proficiency): Employs a range of connectives and discourse markers with some flexibility, aiding coherence.
      Feedback: "Speech is generally well-organized, with ideas developed coherently."
    - Band 5 (Modest Proficiency): Usually maintains flow but may overuse certain connectives/discourse markers. May lack coherence at times.
      Feedback: "Speech may lack coherence at times."
    - Band 3 (Extremely Limited Proficiency): Limited ability to link simple sentences, often relying on basic connectives.
      Feedback: "Speech is often disjointed, and ideas may not be clearly connected."
    - Band 1 (Non-User): No communication possible; no rateable language.
      Feedback: "Speech lacks any logical organization."

    Select the single most appropriate band level (9, 7, 5, 3, or 1) and provide its corresponding feedback string.
    """

    analysis = await call_api_with_retry(prompt, expected_format="dict")
    if not analysis:
        raise ValueError("Failed to get valid analysis from API")

    # Ensure the response has the correct structure
    if "grade" not in analysis or "issues" not in analysis or \
       "cohesive_device_band_level" not in analysis or "cohesive_device_feedback" not in analysis:
        logger.warning("API response did not contain all expected fields for fluency/coherence/cohesive analysis. Falling back.")
        # Fallback to default structure if API doesn't return expected format
        return {
            "grade": 50,
            "issues": ["Unable to analyze fluency due to API response format issues."],
            "cohesive_device_band_level": None,
            "cohesive_device_feedback": None
        }

    return analysis

async def analyze_fluency(request: FluencyRequest) -> FluencyResponse:
    """Main function to analyze fluency and coherence"""
    try:
        timing_metrics = {}
        wpm = 0.0
        hesitation_ratio = 0.0
        pause_count = 0
        avg_pause_duration = 0.0
        pause_percentage = 0.0

        if request.word_details and len(request.word_details) >= 2:
            # Prioritize word_details if available and sufficient
            detailed_timing_metrics = calculate_timing_metrics(request.word_details)
            if detailed_timing_metrics:
                wpm = detailed_timing_metrics.get('words_per_minute', 0.0)
                hesitation_ratio = detailed_timing_metrics.get('hesitation_ratio', 0.0)
                pause_count = detailed_timing_metrics.get('pause_count', 0)
                avg_pause_duration = detailed_timing_metrics.get('avg_pause_duration', 0.0)
                pause_percentage = detailed_timing_metrics.get('pause_percentage', 0.0)
                
                # Use all detailed metrics for the AI prompt
                timing_metrics = detailed_timing_metrics
            
        if wpm == 0.0 and request.reference_text and request.audio_duration and request.audio_duration > 0:
            # Fallback to audio_duration and transcript if WPM couldn't be calculated from word_details
            word_count = len(request.reference_text.split())
            if word_count > 0:
                wpm = round((word_count / request.audio_duration) * 60, 1)
            
            # For the AI prompt, only include WPM if calculated this way, others are unknown
            timing_metrics = {"words_per_minute": wpm}
            # Other detailed metrics (hesitation, pauses) remain 0 as they can't be derived this way

        analysis_result = await get_fluency_coherence_analysis(request.reference_text, timing_metrics)
        
        # Create FluencyMetrics with the calculated WPM and other available metrics
        fluency_metrics_data = {
            "speech_rate": wpm,  # Using WPM as speech rate
            "hesitation_ratio": hesitation_ratio,
            "pause_pattern_score": max(0, 100 - (pause_percentage * 2)) if pause_percentage > 0 else (100 if wpm > 0 else 0), # Simplified score
            "overall_fluency_score": analysis_result.get('grade', 0),
            "words_per_minute": wpm
        }
        
        # Create CoherenceMetrics (using grade as baseline for now)
        coherence_metrics = {
            "topic_consistency": analysis_result.get('grade', 0), # Consider if cohesive band should influence this
            "logical_flow": analysis_result.get('grade', 0),    # Consider if cohesive band should influence this
            "idea_development": analysis_result.get('grade', 0), # Consider if cohesive band should influence this
            "overall_coherence_score": analysis_result.get('grade', 0) # Consider if cohesive band should influence this
        }
        
        return FluencyResponse(
            status="success",
            fluency_metrics=fluency_metrics_data,
            coherence_metrics=coherence_metrics,
            key_findings=analysis_result.get('issues', []),
            improvement_suggestions=analysis_result.get('issues', []),  # Using same issues for now
            cohesive_device_band_level=analysis_result.get('cohesive_device_band_level'),
            cohesive_device_feedback=analysis_result.get('cohesive_device_feedback')
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
                "overall_fluency_score": 0,
                "words_per_minute": 0.0
            },
            coherence_metrics={
                "topic_consistency": 0,
                "logical_flow": 0,
                "idea_development": 0,
                "overall_coherence_score": 0
            },
            key_findings=[],
            improvement_suggestions=[],
            cohesive_device_band_level=None,
            cohesive_device_feedback=None
        )
