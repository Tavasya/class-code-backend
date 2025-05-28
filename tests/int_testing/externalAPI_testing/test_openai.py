"""
Simple integration test for OpenAI grammar and lexical services.
Just tests if the APIs work with our text data.
"""
import pytest
from app.services.grammar_service import analyze_grammar
from app.services.lexical_service import analyze_lexical_resources


class TestOpenAI:
    """Simple tests to verify OpenAI integration works."""

    async def test_grammar_analysis_works(self, skip_if_no_api_keys):
        """Test that OpenAI can analyze grammar."""
        test_text = "I are going to the store yesterday and buyed some grocery."
        
        result = await analyze_grammar(test_text)
        
        # Just verify we get a valid response
        assert "grade" in result
        assert "issues" in result
        assert isinstance(result["grade"], (int, float))
        assert 0 <= result["grade"] <= 100
        assert isinstance(result["issues"], list)
        print(f"✅ Grammar analysis worked. Grade: {result['grade']}, Issues: {len(result['issues'])}")

    async def test_lexical_analysis_works(self, skip_if_no_api_keys):
        """Test that OpenAI can analyze lexical resources."""
        test_sentences = ["I want to get some nice food from the big store."]
        
        result = await analyze_lexical_resources(test_sentences)
        
        # Just verify we get a valid response
        assert "grade" in result
        assert "issues" in result
        assert isinstance(result["grade"], (int, float))
        assert 0 <= result["grade"] <= 100
        assert isinstance(result["issues"], list)
        print(f"✅ Lexical analysis worked. Grade: {result['grade']}, Issues: {len(result['issues'])}")

    async def test_good_grammar_gets_high_score(self, skip_if_no_api_keys):
        """Test that good grammar gets a high score."""
        good_text = "I went to the store yesterday and bought some groceries for dinner."
        
        result = await analyze_grammar(good_text)
        
        # Just verify the system works as expected
        assert result["grade"] >= 70  # Should get decent score for good grammar
        print(f"✅ Good grammar scored: {result['grade']}")

    async def test_advanced_vocabulary_gets_high_score(self, skip_if_no_api_keys):
        """Test that advanced vocabulary gets a good score."""
        advanced_text = ["I intend to acquire some delicious cuisine from the spacious marketplace."]
        
        result = await analyze_lexical_resources(advanced_text)
        
        # Just verify the system recognizes good vocabulary
        assert result["grade"] >= 85  # Should get high score for advanced vocabulary
        print(f"✅ Advanced vocabulary scored: {result['grade']}") 