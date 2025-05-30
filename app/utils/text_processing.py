import re
from typing import List

def count_actual_words(text: str) -> int:
    """
    Count actual words in text, excluding punctuation and special characters.
    
    Args:
        text: Input text to count words from
        
    Returns:
        int: Number of actual words
    """
    # Remove extra whitespace and normalize
    text = text.strip()
    
    # Remove common punctuation that might be counted as words
    text = re.sub(r'[.,!?;:"\'\(\)\[\]\{\}]', ' ', text)
    
    # Split on whitespace and filter out empty strings
    words = [word for word in text.split() if word.strip()]
    
    return len(words)

def get_sentence_count(text: str) -> int:
    """
    Count the number of sentences in the text.
    
    Args:
        text: Input text
        
    Returns:
        int: Number of sentences
    """
    # Split on common sentence endings and filter empty ones
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    return len(sentences) 