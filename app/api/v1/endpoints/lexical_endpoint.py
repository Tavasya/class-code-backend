from fastapi import APIRouter, HTTPException
from typing import List
from app.models.lexical_model import LexicalAnalysisResponse, LexicalFeedback
from app.services.lexical_service import analyze_lexical_resources

router = APIRouter()

@router.post("/analyze", response_model=LexicalAnalysisResponse)
async def analyze_lexical(text: str):
    """
    Analyze lexical resources in the provided text.
    
    Args:
        text: The text to analyze
        
    Returns:
        LexicalAnalysisResponse containing feedback for each sentence
    """
    try:
        # Split text into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if not sentences:
            return LexicalAnalysisResponse(
                lexical_feedback=[],
                error="No valid sentences found in the input text"
            )
        
        # Get lexical feedback from the service
        service_output = await analyze_lexical_resources(sentences)
        
        # Transform service_output["enhanced_lexical_analysis"]
        # which is List[List[LexicalCorrectionDictFromService]] (or similar)
        # to List[LexicalFeedback]
        
        processed_feedback: List[LexicalFeedback] = []
        # The service returns a dict, 'enhanced_lexical_analysis' contains the list of lists of corrections
        enhanced_analysis_results = service_output.get("enhanced_lexical_analysis", [])

        for i, sentence_corrections_list in enumerate(enhanced_analysis_results):
            if i < len(sentences): # Ensure we have the original sentence to associate
                # sentence_corrections_list is List[LexicalCorrection]
                # LexicalFeedback expects: sentence: str, corrections: List[LexicalCorrection]
                processed_feedback.append(
                    LexicalFeedback(
                        sentence=sentences[i],
                        corrections=sentence_corrections_list
                    )
                )
            # else: Mismatch in length between original sentences and analyzed sentence corrections.
            # Might want to log this or handle it if it occurs.

        return LexicalAnalysisResponse(lexical_feedback=processed_feedback)
        
    except Exception as e:
        # Log the exception for more detailed error information
        # logger.exception(f"Error in analyze_lexical endpoint: {str(e)}") # Assuming logger is configured
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing lexical resources: {str(e)}"
        ) 