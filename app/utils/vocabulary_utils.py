import json
from typing import Dict, Any
import spacy
from pathlib import Path
import logging

# Setup logging
logger = logging.getLogger(__name__)

class VocabularyTools:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VocabularyTools, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.nlp_processor = None
            self.oxford_data_cache = {}
            self.cefr_progression_map = {"A2": "B1", "B1": "B2", "B2": "C1"}
            self._initialized = True
    
    def initialize(self, oxford_json_path: str = "assets/full-word.json"):
        """Initialize the NLP processor and load Oxford data."""
        try:
            if self.nlp_processor is None:
                logger.info("Loading spaCy model...")
                self.nlp_processor = spacy.load("en_core_web_sm")
                logger.info("Successfully loaded spaCy model")
                
            if not self.oxford_data_cache:
                logger.info("Loading Oxford data...")
                self.oxford_data_cache = self._load_oxford_data(file_path=oxford_json_path)
                logger.info("Successfully loaded Oxford data")
                
            if not self.nlp_processor:
                raise RuntimeError("NLP processor failed to initialize")
                
            if not self.oxford_data_cache:
                raise RuntimeError("Oxford data cache failed to initialize")
                
        except Exception as e:
            logger.error(f"Error initializing vocabulary tools: {str(e)}")
            # Reset state to ensure clean state on next attempt
            self.nlp_processor = None
            self.oxford_data_cache = {}
            raise RuntimeError(f"Failed to initialize vocabulary tools: {str(e)}")
    
    def _load_oxford_data(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """Load and process the Oxford 5000 word data."""
        if not self.nlp_processor:
            raise ValueError("NLP processor must be initialized first")
            
        oxford_data = {}
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Oxford 5000 data file not found at {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                
            for entry in raw_data:
                if not isinstance(entry, dict) or 'value' not in entry:
                    continue
                    
                word_data = entry['value']
                if not isinstance(word_data, dict) or 'word' not in word_data or 'level' not in word_data:
                    continue
                    
                word = word_data['word']
                lemma = self.get_lemma(word)
                
                # Store both the lemma form and original word form
                oxford_data[lemma] = {
                    'level': word_data['level'],
                    'original_form': word,
                }
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in Oxford 5000 data file: {e}")
        except Exception as e:
            raise Exception(f"Error loading Oxford 5000 data: {e}")
            
        return oxford_data
    
    def get_lemma(self, word_text: str) -> str:
        """Get the lemma form of a word using spaCy."""
        if not self.nlp_processor:
            raise ValueError("NLP processor must be initialized first")
            
        doc = self.nlp_processor(word_text.lower())
        if doc and len(doc) > 0:
            return doc[0].lemma_
        return word_text.lower()  # Fallback for empty or unlemmatizable input

# Create a singleton instance
vocabulary_tools = VocabularyTools()

def initialize_vocabulary_tools(oxford_json_path: str = "assets/full-word.json"):
    """Initialize the vocabulary tools singleton."""
    return vocabulary_tools.initialize(oxford_json_path)

# Export commonly used attributes
NLP_PROCESSOR = vocabulary_tools.nlp_processor
OXFORD_DATA_CACHE = vocabulary_tools.oxford_data_cache
CEFR_PROGRESSION_MAP = vocabulary_tools.cefr_progression_map
get_lemma = vocabulary_tools.get_lemma 