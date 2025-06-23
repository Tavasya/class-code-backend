import logging
import aiohttp
from typing import Dict, Any, Optional
from app.models.paragraph_restructuring_model import (
    ParagraphRestructuringRequest,
    ParagraphRestructuringResult, 
    BandLevelDetectionResult
)
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

# Setup logging
logger = logging.getLogger(__name__)

# CEFR Band mappings
CEFR_BANDS = ["A1", "A2", "B1", "B2", "C1", "C2"]
BAND_PROGRESSION = {
    "A1": "A2",
    "A2": "B1", 
    "B1": "B2",
    "B2": "C1",
    "C1": "C2",
    "C2": "C2"  # C2 is the highest level
}

SCORE_TO_CEFR = {
    (0, 30): "A1",
    (31, 50): "A2", 
    (51, 70): "B1",
    (71, 85): "B2",
    (86, 95): "C1",
    (96, 100): "C2"
}


def determine_band_level_from_scores(analysis_results: Dict[str, Any]) -> BandLevelDetectionResult:
    """
    Determine CEFR band level from analysis scores
    
    Args:
        analysis_results: Dictionary containing analysis results from all services
        
    Returns:
        BandLevelDetectionResult with detected band and confidence
    """
    logger.info("Determining CEFR band level from analysis scores")
    
    scores = {}
    total_weight = 0
    weighted_sum = 0
    
    # Extract scores with weights
    score_weights = {
        "pronunciation": 0.25,
        "fluency": 0.25,
        "grammar": 0.25,
        "lexical": 0.125,  # Combined lexical and vocabulary = 0.25
        "vocabulary": 0.125
    }
    
    for analysis_type, weight in score_weights.items():
        if analysis_type in analysis_results:
            result = analysis_results[analysis_type]
            if isinstance(result, dict) and "grade" in result:
                score = result["grade"]
                if isinstance(score, (int, float)) and 0 <= score <= 100:
                    scores[analysis_type] = score
                    weighted_sum += score * weight
                    total_weight += weight
                    logger.info(f"Using {analysis_type} score: {score} (weight: {weight})")
    
    if total_weight == 0:
        logger.warning("No valid scores found for band level detection")
        return BandLevelDetectionResult(
            detected_band="A1",
            confidence_score=0.0,
            score_breakdown={}
        )
    
    # Calculate weighted average
    average_score = weighted_sum / total_weight
    logger.info(f"Calculated weighted average score: {average_score:.2f}")
    
    # Map score to CEFR band
    detected_band = "A1"  # Default
    for (min_score, max_score), band in SCORE_TO_CEFR.items():
        if min_score <= average_score <= max_score:
            detected_band = band
            break
    
    # Calculate confidence based on how many services provided scores
    confidence = total_weight / sum(score_weights.values())
    
    logger.info(f"Detected CEFR band: {detected_band} with confidence: {confidence:.2f}")
    
    return BandLevelDetectionResult(
        detected_band=detected_band,
        confidence_score=confidence,
        score_breakdown={
            "average_score": average_score,
            "individual_scores": scores,
            "total_weight": total_weight
        }
    )


async def call_openai_for_restructuring(transcript: str, current_band: str, target_band: str) -> str:
    """
    Call OpenAI API to restructure paragraph to target CEFR level
    
    Args:
        transcript: Original transcript text
        current_band: Current CEFR level
        target_band: Target CEFR level
        
    Returns:
        Restructured paragraph text
    """
    logger.info(f"Calling OpenAI to restructure from {current_band} to {target_band}")
    
    # Create CEFR-specific improvement prompt
    prompt = f"""
You are an expert English language teacher specializing in CEFR levels. Please improve the following paragraph from {current_band} level to {target_band} level.

IMPORTANT: Make REALISTIC, incremental improvements that a student progressing from {current_band} to {target_band} would actually make. Don't make it too advanced or sophisticated.

Original paragraph (current level: {current_band}):
"{transcript}"

Target level: {target_band}

{get_improvement_instructions(current_band, target_band)}

Please provide ONLY the improved paragraph. Do not include explanations or additional text. The improved paragraph should:
1. Keep the same basic meaning and natural tone
2. Make realistic improvements a {target_band} level student would write
3. Not sound too formal, academic, or overly sophisticated
4. Feel natural and conversational like the original

Improved paragraph:
"""
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are an expert English language teacher specializing in CEFR levels and language progression."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 500,
                "temperature": 0.3
            }
            
            async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    improved_text = data["choices"][0]["message"]["content"].strip()
                    logger.info(f"Successfully restructured paragraph (length: {len(improved_text)})")
                    return improved_text
                else:
                    error_text = await response.text()
                    logger.error(f"OpenAI API error {response.status}: {error_text}")
                    return transcript  # Return original if API fails
                    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return transcript  # Return original if error occurs


def get_improvement_instructions(current_band: str, target_band: str) -> str:
    """Get specific improvement instructions for CEFR level progression"""
    
    improvements = {
        ("A1", "A2"): """
Make these SIMPLE, natural improvements:
- Add basic connecting words like 'and', 'but', 'because'
- Use slightly more descriptive words (but keep them simple)
- Make one or two sentences a bit longer
- Keep the same natural, conversational tone
- Don't make it sound too formal or academic

Example: "I like food" becomes "I really like food because it's delicious"
""",
        ("A2", "B1"): """
Make these MODERATE, realistic improvements:
- Add some descriptive adjectives and simple adverbs
- Use connecting words like 'although', 'while', 'since' (sparingly)
- Include slightly more specific vocabulary
- Add simple reasoning or personal opinions
- Keep it conversational and natural
- Don't overuse complex structures

Example: "I like books" becomes "I enjoy reading books, especially mystery novels, because they're exciting and help me relax"
""",
        ("B1", "B2"): """
Make these realistic intermediate improvements:
- Use more varied vocabulary and some less common words
- Add some complex sentences (but not too many)
- Include better explanations and examples
- Use linking words like 'however', 'therefore', 'as a result'
- Show clearer organization of ideas
- Keep it natural, not overly formal

Example: Keep the improvement proportional and realistic for this level
""",
        ("B2", "C1"): """
Make these advanced but natural improvements:
- Use more sophisticated vocabulary and occasional idiomatic expressions
- Create more complex sentence structures
- Add nuanced reasoning and better examples
- Use advanced linking devices appropriately
- Show deeper analysis while staying natural
- Maintain good flow and readability
""",
        ("C1", "C2"): """
Make these expert-level improvements:
- Use precise, sophisticated vocabulary where appropriate
- Create well-structured, eloquent expressions
- Use advanced techniques naturally
- Demonstrate native-like fluency
- Include subtle implications and sophisticated reasoning
- Perfect grammar with stylistic variety
"""
    }
    
    return improvements.get((current_band, target_band), "Improve vocabulary and sentence complexity appropriately.")


async def restructure_paragraph(
    transcript: str, 
    current_band: Optional[str] = None,
    analysis_results: Optional[Dict[str, Any]] = None
) -> ParagraphRestructuringResult:
    """
    Main function to restructure a paragraph to the next CEFR level
    
    Args:
        transcript: Original transcript text
        current_band: Current CEFR level (if known)
        analysis_results: Analysis results for band detection (if current_band not provided)
        
    Returns:
        ParagraphRestructuringResult with original band, target band, and improved transcript
    """
    logger.info(f"Starting paragraph restructuring for transcript: {transcript[:100]}...")
    
    try:
        # Determine current band if not provided
        if current_band is None:
            if analysis_results:
                detection_result = determine_band_level_from_scores(analysis_results)
                current_band = detection_result.detected_band
                logger.info(f"Auto-detected band level: {current_band}")
            else:
                current_band = "A1"  # Default fallback
                logger.warning("No analysis results provided, defaulting to A1")
        
        # Get target band
        target_band = BAND_PROGRESSION.get(current_band, current_band)
        
        if current_band == target_band:
            logger.info(f"Already at highest level ({current_band}), returning original transcript")
            return ParagraphRestructuringResult(
                original_band=current_band,
                target_band=target_band,
                improved_transcript=transcript
            )
        
        # Generate improved transcript
        improved_transcript = await call_openai_for_restructuring(transcript, current_band, target_band)
        
        return ParagraphRestructuringResult(
            original_band=current_band,
            target_band=target_band,
            improved_transcript=improved_transcript
        )
        
    except Exception as e:
        logger.error(f"Error in paragraph restructuring: {str(e)}")
        # Return original transcript on error
        fallback_band = current_band or "A1"
        return ParagraphRestructuringResult(
            original_band=fallback_band,
            target_band=BAND_PROGRESSION.get(fallback_band, fallback_band),
            improved_transcript=transcript
        )


async def analyze_paragraph_restructuring(request: ParagraphRestructuringRequest) -> ParagraphRestructuringResult:
    """
    Analyze and restructure paragraph from request
    
    Args:
        request: ParagraphRestructuringRequest with transcript and optional current band
        
    Returns:
        ParagraphRestructuringResult
    """
    logger.info(f"Analyzing paragraph restructuring request")
    
    return await restructure_paragraph(
        transcript=request.transcript,
        current_band=request.current_band
    ) 