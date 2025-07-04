import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Filler word patterns for removal
FILLER_PATTERNS = [
    r'\b(um|uh|ah|uhm|mmm|hmm)\b',
    r'\b(like)\b(?=\s+\w)',  # 'like' only when used as filler, not in "I like this"
    r'\b(you know)\b',
    r'\b(sort of|kind of)\b(?=\s+\w)',  # Only when used as hedging, not complete phrases
    r'\b(I mean)\b',
    r'\b(well)\b(?=\s*[,.])',  # 'well' at beginning of sentences
    r'\b(so)\b(?=\s*[,.])',  # 'so' as sentence starter filler
]

# Additional cleanup patterns
CLEANUP_PATTERNS = [
    r'\s+',  # Multiple spaces to single space
    r'\.{2,}',  # Multiple periods to single period
    r',{2,}',  # Multiple commas to single comma
    r'\s+([,.!?])',  # Space before punctuation
    r'([,.!?]){2,}',  # Repeated punctuation
    r'^[,\s]+',  # Leading commas and spaces
    r'[,\s]+$',  # Trailing commas and spaces
    r'\s*,\s*,',  # Double commas with spaces
]


def clean_transcript(text: str) -> str:
    """
    Clean transcript by removing filler words and fixing basic formatting issues.
    
    Args:
        text: Original transcript text
        
    Returns:
        Cleaned transcript with filler words removed and basic formatting fixed
    """
    if not text or not text.strip():
        return text
    
    logger.info(f"Cleaning transcript of length: {len(text)}")
    
    # Store original for comparison
    original_text = text
    cleaned_text = text
    
    # Remove filler words using patterns
    removed_fillers = []
    for pattern in FILLER_PATTERNS:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        if matches:
            # Flatten matches (some patterns return tuples)
            flat_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    flat_matches.extend([m for m in match if m])
                else:
                    flat_matches.append(match)
            removed_fillers.extend(flat_matches)
        
        cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.IGNORECASE)
    
    # Apply cleanup patterns
    for pattern in CLEANUP_PATTERNS:
        if pattern == r'\s+':
            cleaned_text = re.sub(pattern, ' ', cleaned_text)
        elif pattern == r'\.{2,}':
            cleaned_text = re.sub(pattern, '.', cleaned_text)
        elif pattern == r',{2,}':
            cleaned_text = re.sub(pattern, ',', cleaned_text)
        elif pattern == r'\s+([,.!?])':
            cleaned_text = re.sub(pattern, r'\1', cleaned_text)
        elif pattern == r'([,.!?]){2,}':
            cleaned_text = re.sub(pattern, r'\1', cleaned_text)
        elif pattern == r'^[,\s]+':
            cleaned_text = re.sub(pattern, '', cleaned_text)
        elif pattern == r'[,\s]+$':
            cleaned_text = re.sub(pattern, '', cleaned_text)
        elif pattern == r'\s*,\s*,':
            cleaned_text = re.sub(pattern, ',', cleaned_text)
    
    # Remove excessive repetitions (words repeated 3+ times)
    cleaned_text = remove_excessive_repetitions(cleaned_text)
    
    # Final cleanup
    cleaned_text = cleaned_text.strip()
    
    # Log what was removed
    if removed_fillers:
        logger.info(f"Removed filler words: {removed_fillers}")
    
    original_word_count = len(original_text.split())
    cleaned_word_count = len(cleaned_text.split())
    logger.info(f"Cleaned transcript: {original_word_count} -> {cleaned_word_count} words")
    
    return cleaned_text


def remove_excessive_repetitions(text: str) -> str:
    """
    Remove excessive word repetitions (3+ consecutive identical words).
    
    Args:
        text: Text to process
        
    Returns:
        Text with excessive repetitions reduced
    """
    # Pattern to match 3+ consecutive identical words
    pattern = r'\b(\w+)(\s+\1){2,}\b'
    
    def replace_repetition(match):
        word = match.group(1)
        # Keep only 2 instances maximum
        return f"{word} {word}"
    
    return re.sub(pattern, replace_repetition, text, flags=re.IGNORECASE)


def get_cleaning_summary(original: str, cleaned: str) -> Dict[str, Any]:
    """
    Get summary of what was cleaned from the transcript.
    
    Args:
        original: Original transcript
        cleaned: Cleaned transcript
        
    Returns:
        Dictionary with cleaning statistics
    """
    if not original or not cleaned:
        return {}
    
    original_words = original.split()
    cleaned_words = cleaned.split()
    
    # Find removed words (simplified approach)
    removed_words = []
    for pattern in FILLER_PATTERNS:
        matches = re.findall(pattern, original, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                removed_words.extend([m for m in match if m])
            else:
                removed_words.append(match)
    
    return {
        "original_word_count": len(original_words),
        "cleaned_word_count": len(cleaned_words),
        "words_removed": len(original_words) - len(cleaned_words),
        "filler_words_removed": list(set(removed_words)) if removed_words else [],
        "character_reduction": len(original) - len(cleaned)
    }


def batch_clean_transcripts(transcripts: List[str]) -> List[str]:
    """
    Clean multiple transcripts efficiently.
    
    Args:
        transcripts: List of transcript strings to clean
        
    Returns:
        List of cleaned transcript strings
    """
    logger.info(f"Batch cleaning {len(transcripts)} transcripts")
    
    cleaned_transcripts = []
    for i, transcript in enumerate(transcripts):
        try:
            cleaned = clean_transcript(transcript)
            cleaned_transcripts.append(cleaned)
        except Exception as e:
            logger.error(f"Error cleaning transcript {i}: {str(e)}")
            # Return original transcript on error
            cleaned_transcripts.append(transcript)
    
    logger.info(f"Completed batch cleaning of {len(cleaned_transcripts)} transcripts")
    return cleaned_transcripts