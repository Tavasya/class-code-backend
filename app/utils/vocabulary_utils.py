import json
from typing import Dict, Any
import spacy
from pathlib import Path

# Global variables
OXFORD_DATA_CACHE: Dict[str, Dict[str, Any]] = {}
NLP_PROCESSOR: Any = None
CEFR_PROGRESSION_MAP: Dict[str, str] = {"A2": "B1", "B1": "B2", "B2": "C1"}

def get_lemma(word_text: str, nlp_processor_instance) -> str:
    """
    Get the lemma form of a word using spaCy.
    
    Args:
        word_text (str): The word to lemmatize
        nlp_processor_instance: The spaCy NLP model instance
        
    Returns:
        str: The lemmatized form of the word in lowercase
    """
    doc = nlp_processor_instance(word_text.lower())
    if doc and len(doc) > 0:
        return doc[0].lemma_
    return word_text.lower()  # Fallback for empty or unlemmatizable input

def load_oxford_data(file_path: str = "assets/full-word.json", nlp_processor=None) -> Dict[str, Dict[str, Any]]:
    """
    Load and process the Oxford 5000 word data.
    
    Args:
        file_path (str): Path to the Oxford 5000 JSON file
        nlp_processor: The spaCy NLP model instance for lemmatization
        
    Returns:
        Dict[str, Dict[str, Any]]: Dictionary mapping lemmatized words to their data
    """
    if not nlp_processor:
        raise ValueError("NLP processor must be provided")
        
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
            lemma = get_lemma(word, nlp_processor)
            
            # Store both the lemma form and original word form
            oxford_data[lemma] = {
                'level': word_data['level'],
                'original_form': word,
                # Store any other relevant data from the word_data dictionary
            }
            
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in Oxford 5000 data file: {e}")
    except Exception as e:
        raise Exception(f"Error loading Oxford 5000 data: {e}")
        
    return oxford_data

def initialize_vocabulary_tools(oxford_json_path: str = "assets/full-word.json"):
    """
    Initialize the NLP processor and load Oxford data.
    This should be called once at application startup.
    
    Args:
        oxford_json_path (str): Path to the Oxford 5000 JSON file
    """
    global NLP_PROCESSOR, OXFORD_DATA_CACHE
    
    try:
        if NLP_PROCESSOR is None:
            NLP_PROCESSOR = spacy.load("en_core_web_sm")
            
        if not OXFORD_DATA_CACHE:
            OXFORD_DATA_CACHE = load_oxford_data(file_path=oxford_json_path, nlp_processor=NLP_PROCESSOR)
            
        if not NLP_PROCESSOR or not OXFORD_DATA_CACHE:
            raise RuntimeError("Failed to initialize essential vocabulary tools.")
            
    except Exception as e:
        raise RuntimeError(f"Error initializing vocabulary tools: {e}") 