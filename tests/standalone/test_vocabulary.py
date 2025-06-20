#!/usr/bin/env python3

import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.vocabulary_service import analyze_vocabulary
from app.utils.vocabulary_utils import initialize_vocabulary_tools

class TestVocabularyService:
    """Test suite for vocabulary analysis service"""
    
    @classmethod
    def setup_class(cls):
        """Initialize vocabulary tools once for the entire test class"""
        print("🔧 Initializing vocabulary tools...")
        initialize_vocabulary_tools()
        print("✅ Vocabulary tools initialized")
    
    @pytest.mark.asyncio
    async def test_basic_vocabulary_analysis(self):
        """Test vocabulary analysis with mixed difficulty words"""
        
        test_text = "The cat sat on the sophisticated velvet chair"
        
        print(f"\n📚 Testing: '{test_text}'")
        print("-" * 50)
        
        result = await analyze_vocabulary(test_text)
        
        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "grade" in result, "Result should contain grade"
        assert "vocabulary_suggestions" in result, "Result should contain vocabulary_suggestions"
        assert isinstance(result["grade"], int), "Grade should be an integer"
        assert 0 <= result["grade"] <= 100, "Grade should be between 0 and 100"
        
        # Display results
        print("📊 RESULTS:")
        print(f"Grade: {result['grade']}")
        
        suggestions = result.get('vocabulary_suggestions', {})
        print(f"Number of Suggestions: {len(suggestions)}")
        
        if suggestions:
            print("\n🔍 VOCABULARY SUGGESTIONS:")
            for key, suggestion in suggestions.items():
                original = suggestion.get('original_word', 'N/A')
                suggested = suggestion.get('suggested_word', 'N/A')
                original_level = suggestion.get('original_level', 'N/A')
                suggested_level = suggestion.get('suggested_level', 'N/A')
                explanation = suggestion.get('explanation', 'N/A')
                
                print(f"  '{original}' ({original_level}) → '{suggested}' ({suggested_level})")
                print(f"    Reason: {explanation}")
        else:
            print("✅ No vocabulary improvements suggested!")
    
    @pytest.mark.asyncio
    async def test_simple_vocabulary(self):
        """Test with very basic vocabulary to see more suggestions"""
        
        test_text = "I like cats and dogs. They are nice."
        
        print(f"\n📚 Testing simple text: '{test_text}'")
        
        result = await analyze_vocabulary(test_text)
        
        assert isinstance(result, dict)
        assert "grade" in result
        
        print(f"Grade: {result['grade']}")
        print(f"Suggestions: {len(result.get('vocabulary_suggestions', {}))}")
    
    @pytest.mark.asyncio  
    async def test_advanced_vocabulary(self):
        """Test with advanced vocabulary to see fewer suggestions"""
        
        test_text = "The perspicacious scholar demonstrated exceptional erudition while elucidating complex theoretical paradigms."
        
        print(f"\n📚 Testing advanced text: '{test_text}'")
        
        result = await analyze_vocabulary(test_text)
        
        assert isinstance(result, dict)
        assert "grade" in result
        
        print(f"Grade: {result['grade']}")
        print(f"Suggestions: {len(result.get('vocabulary_suggestions', {}))}") 