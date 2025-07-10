import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class SentenceExtractionService:
    """Service for extracting sentences from transcript for practice"""
    
    def __init__(self):
        logger.info("SentenceExtractionService initialized")
    
    def extract_sentences(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Extract sentences from transcript for practice
        
        Args:
            transcript: The transcript text
            
        Returns:
            List of sentence dictionaries with practice metadata
        """
        try:
            logger.info(f"🔍 Extracting sentences from transcript: {transcript[:100]}...")
            
            # Clean the transcript
            cleaned_transcript = self._clean_transcript(transcript)
            
            # Split into sentences
            raw_sentences = self._split_into_sentences(cleaned_transcript)
            
            # Process each sentence
            practice_sentences = []
            for index, sentence_text in enumerate(raw_sentences):
                if sentence_text.strip():  # Only process non-empty sentences
                    practice_sentence = self._create_practice_sentence(index, sentence_text)
                    practice_sentences.append(practice_sentence)
            
            logger.info(f"✅ Extracted {len(practice_sentences)} practice sentences")
            return practice_sentences
            
        except Exception as e:
            logger.error(f"❌ Error extracting sentences: {str(e)}")
            return []
    
    def _clean_transcript(self, transcript: str) -> str:
        """Clean transcript for sentence extraction"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', transcript.strip())
        
        # Ensure proper sentence endings
        cleaned = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', cleaned)
        
        return cleaned
    
    def _split_into_sentences(self, transcript: str) -> List[str]:
        """Split transcript into individual sentences"""
        # Use regex to split on sentence boundaries
        # This handles periods, exclamation marks, and question marks
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        
        sentences = re.split(sentence_pattern, transcript)
        
        # Filter out empty sentences and clean each one
        return [sentence.strip() for sentence in sentences if sentence.strip()]
    
    def _create_practice_sentence(self, index: int, sentence_text: str) -> Dict[str, Any]:
        """Create a practice sentence object with metadata"""
        # Extract individual words
        words = self._extract_words(sentence_text)
        
        return {
            "index": index,
            "text": sentence_text.strip(),
            "words": words,
            "completed": False,
            "passed": False,
            "attempts": 0,
            "best_score": 0
        }
    
    def _extract_words(self, sentence: str) -> List[str]:
        """Extract individual words from sentence"""
        # Remove punctuation and split by whitespace
        words = re.findall(r'\b[a-zA-Z]+\b', sentence)
        return [word.lower() for word in words]
    
    def get_sentence_by_index(self, sentences: List[Dict[str, Any]], index: int) -> Dict[str, Any]:
        """Get a specific sentence by index"""
        if 0 <= index < len(sentences):
            return sentences[index]
        return None
    
    def get_total_sentences(self, sentences: List[Dict[str, Any]]) -> int:
        """Get total number of sentences"""
        return len(sentences)
    
    def get_words_for_sentence(self, sentence: Dict[str, Any]) -> List[str]:
        """Get words for a specific sentence"""
        return sentence.get("words", [])