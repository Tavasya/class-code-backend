#!/usr/bin/env python3

import pytest
from app.services.grammar_service import analyze_grammar

class TestGrammarService:
    """Test suite for grammar analysis service"""
    
    @pytest.mark.asyncio
    async def test_basic_grammar_analysis(self):
        """Test grammar analysis with intentional errors"""
        
        test_text = "I are going to the store yesterday. Me and him was talking about it."
        
        print(f"\n📝 Testing: '{test_text}'")
        print("-" * 50)
        
        result = await analyze_grammar(test_text)
        
        # Assertions
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "grade" in result, "Result should contain grade"
        assert "grammar_corrections" in result, "Result should contain grammar_corrections"
        
        # Display results
        print("📊 GRAMMAR ANALYSIS RESULTS:")
        print(f"Grade: {result.get('grade', 'N/A')}")
        
        corrections_dict = result.get('grammar_corrections', {})
        print(f"Number of Corrections: {len(corrections_dict)}")
        
        if corrections_dict:
            print(f"\n🔍 CORRECTIONS FOUND:")
            for key, correction_data in corrections_dict.items():
                original_sentence = correction_data.get('original', 'N/A')
                corrections_list = correction_data.get('corrections', [])
                
                print(f"\nSentence: '{original_sentence}'")
                for correction in corrections_list:
                    original = correction.get('original_phrase', 'N/A')
                    suggested = correction.get('suggested_correction', 'N/A')
                    explanation = correction.get('explanation', 'N/A')
                    
                    print(f"  • '{original}' → '{suggested}'")
                    print(f"    Reason: {explanation}")
        else:
            print("✅ No grammar errors found!")
    
    @pytest.mark.asyncio
    async def test_perfect_grammar(self):
        """Test with grammatically correct text"""
        
        test_text = "The students are studying diligently for their upcoming examinations."
        
        print(f"\n📝 Testing perfect grammar: '{test_text}'")
        
        result = await analyze_grammar(test_text)
        
        assert isinstance(result, dict)
        print(f"Grade: {result.get('grade', 'N/A')}")
        print(f"Number of Corrections: {len(result.get('grammar_corrections', {}))}")
    
    @pytest.mark.asyncio
    async def test_complex_grammar_errors(self):
        """Test with multiple types of grammar errors"""
        
        test_text = "She don't have no money, and her friends doesn't either. If I was rich, I would of helped them."
        
        print(f"\n📝 Testing complex errors: '{test_text}'")
        
        result = await analyze_grammar(test_text)
        
        assert isinstance(result, dict)
        corrections_dict = result.get('grammar_corrections', {})
        
        print(f"Grade: {result.get('grade', 'N/A')}")
        print(f"Errors Found: {len(corrections_dict)}")
        
        # Show first few corrections
        count = 0
        for key, correction_data in corrections_dict.items():
            if count >= 3:
                break
            for correction in correction_data.get('corrections', []):
                print(f"  • '{correction.get('original_phrase')}' → '{correction.get('suggested_correction')}'")
                count += 1
                if count >= 3:
                    break 