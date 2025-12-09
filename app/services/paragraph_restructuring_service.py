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

# CEFR Band mappings with 0.5 increments
CEFR_BANDS = ["A1", "A1.5", "A2", "A2.5", "B1", "B1.5", "B2", "B2.5", "C1", "C1.5", "C2"]
BAND_PROGRESSION = {
    "A1": "A1.5",
    "A1.5": "A2",
    "A2": "A2.5", 
    "A2.5": "B1",
    "B1": "B1.5",
    "B1.5": "B2",
    "B2": "B2.5",
    "B2.5": "C1",
    "C1": "C1.5",
    "C1.5": "C2",
    "C2": "C2"  # C2 is the highest level
}

SCORE_TO_CEFR = {
    (0, 25): "A1",
    (26, 40): "A1.5",
    (41, 55): "A2", 
    (56, 65): "A2.5",
    (66, 75): "B1",
    (76, 82): "B1.5",
    (83, 88): "B2",
    (89, 93): "B2.5",
    (94, 97): "C1",
    (98, 99): "C1.5",
    (100, 100): "C2"
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
    
    # Count original word count for length constraint
    original_word_count = len(transcript.split())
    
    # Create simple, realistic improvement prompt
    prompt = f"""Improve this transcript with simple, natural enhancements.

CRITICAL REQUIREMENTS:
- Keep the SAME LENGTH as the original (around {original_word_count} words)
- Make only SMALL, REALISTIC improvements
- Keep it natural and conversational
- Do NOT make it overly formal or academic
- Remove filler words like 'um', 'uh', 'like', 'you know'
- Fix obvious grammar mistakes
- Add simple connecting words where helpful

Original transcript:
"{transcript}"

Instructions: Make small, natural improvements to make the transcript clearer and more fluent. Focus on removing disfluencies, fixing basic grammar, and adding simple connecting words. Keep the same meaning and approximate length. Make it sound more natural and polished.

Improved transcript:"""
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-5-nano",
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are a helpful language assistant. You specialize in making simple, natural improvements to transcripts by removing disfluencies, fixing basic grammar, and adding connecting words. Keep improvements realistic and conversational."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
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
        ("A1", "A1.5"): """
Make these VERY SIMPLE improvements:
- Remove filler words like 'um', 'uh', 'like'
- Fix basic grammar mistakes
- Add simple connecting words like 'and', 'but'
- Keep sentences short and clear
- Maintain natural tone

Example: "Um I like food and uh it's good" becomes "I like food and it's good"
""",
        ("A1.5", "A2"): """
Make these SIMPLE improvements:
- Remove disfluencies and filler words
- Add basic descriptive words
- Use simple connecting words like 'because', 'so'
- Fix obvious grammar errors
- Keep it conversational

Example: "I like food because it's delicious"
""",
        ("A2", "A2.5"): """
Make these MODERATE improvements:
- Remove all disfluencies
- Add some descriptive adjectives
- Use connecting words like 'although', 'while'
- Fix grammar mistakes
- Add simple explanations

Example: "I enjoy reading books, especially mystery novels, because they're exciting"
""",
        ("A2.5", "B1"): """
Make these INTERMEDIATE improvements:
- Use more varied vocabulary
- Add some complex sentences
- Include better explanations
- Use linking words like 'however', 'therefore'
- Show clearer organization

Example: Keep improvements proportional and realistic
""",
        ("B1", "B1.5"): """
Make these ADVANCED INTERMEDIATE improvements:
- Use more sophisticated vocabulary
- Create varied sentence structures
- Add nuanced explanations
- Use advanced linking devices
- Show better flow and organization
""",
        ("B1.5", "B2"): """
Make these UPPER INTERMEDIATE improvements:
- Use sophisticated vocabulary appropriately
- Create complex but clear sentences
- Add detailed explanations and examples
- Use advanced linking devices naturally
- Show excellent organization and flow
""",
        ("B2", "B2.5"): """
Make these ADVANCED improvements:
- Use precise, sophisticated vocabulary
- Create well-structured expressions
- Add nuanced reasoning
- Use advanced techniques naturally
- Demonstrate excellent fluency
""",
        ("B2.5", "C1"): """
Make these UPPER ADVANCED improvements:
- Use highly sophisticated vocabulary
- Create eloquent, well-structured expressions
- Add sophisticated reasoning and analysis
- Use advanced techniques masterfully
- Demonstrate near-native fluency
""",
        ("C1", "C1.5"): """
Make these EXPERT improvements:
- Use precise, academic vocabulary
- Create masterful sentence structures
- Add sophisticated analysis and reasoning
- Use advanced techniques flawlessly
- Demonstrate native-like fluency
""",
        ("C1.5", "C2"): """
Make these MASTERY improvements:
- Use the most appropriate vocabulary for context
- Create perfectly structured expressions
- Add masterful analysis and reasoning
- Use all techniques with perfect timing
- Demonstrate complete mastery of the language
"""
    }
    
    return improvements.get((current_band, target_band), "Make simple, natural improvements to vocabulary and sentence structure.")


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