#!/usr/bin/env python3

import pytest
from unittest.mock import patch, AsyncMock
from app.services.paragraph_restructuring_service import (
    determine_band_level_from_scores,
    restructure_paragraph,
    analyze_paragraph_restructuring,
    call_openai_for_restructuring,
    get_improvement_instructions,
    BAND_PROGRESSION,
    SCORE_TO_CEFR
)
from app.models.paragraph_restructuring_model import (
    ParagraphRestructuringRequest,
    BandLevelDetectionResult
)


class TestParagraphRestructuringService:
    """Test suite for paragraph restructuring service"""
    
    def test_band_level_detection_with_valid_scores(self):
        """Test CEFR band level detection with valid analysis scores"""
        
        print("\n🎯 Testing Band Level Detection")
        print("-" * 50)
        
        test_cases = [
            # (analysis_results, expected_band, description)
            (
                {
                    "pronunciation": {"grade": 25},
                    "fluency": {"grade": 20},
                    "grammar": {"grade": 30},
                    "lexical": {"grade": 25},
                    "vocabulary": {"grade": 20}
                },
                "A1",
                "Low scores should detect A1"
            ),
            (
                {
                    "pronunciation": {"grade": 45},
                    "fluency": {"grade": 40},
                    "grammar": {"grade": 50},
                    "lexical": {"grade": 42},
                    "vocabulary": {"grade": 38}
                },
                "A2",
                "Medium-low scores should detect A2"
            ),
            (
                {
                    "pronunciation": {"grade": 65},
                    "fluency": {"grade": 60},
                    "grammar": {"grade": 70},
                    "lexical": {"grade": 62},
                    "vocabulary": {"grade": 58}
                },
                "B1",
                "Medium scores should detect B1"
            ),
            (
                {
                    "pronunciation": {"grade": 80},
                    "fluency": {"grade": 75},
                    "grammar": {"grade": 85},
                    "lexical": {"grade": 78},
                    "vocabulary": {"grade": 72}
                },
                "B2",
                "High scores should detect B2"
            ),
            (
                {
                    "pronunciation": {"grade": 90},
                    "fluency": {"grade": 88},
                    "grammar": {"grade": 92},
                    "lexical": {"grade": 85},
                    "vocabulary": {"grade": 87}
                },
                "C1",
                "Very high scores should detect C1"
            ),
            (
                {
                    "pronunciation": {"grade": 98},
                    "fluency": {"grade": 96},
                    "grammar": {"grade": 100},
                    "lexical": {"grade": 95},
                    "vocabulary": {"grade": 97}
                },
                "C2",
                "Excellent scores should detect C2"
            )
        ]
        
        for analysis_results, expected_band, description in test_cases:
            result = determine_band_level_from_scores(analysis_results)
            
            print(f"Test: {description}")
            print(f"Average Score: {result.score_breakdown['average_score']:.1f}")
            print(f"Expected Band: {expected_band}, Detected: {result.detected_band}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print()
            
            assert result.detected_band == expected_band, f"Expected {expected_band}, got {result.detected_band}"
            assert 0.0 <= result.confidence_score <= 1.0, "Confidence should be between 0 and 1"
    
    def test_band_level_detection_with_missing_scores(self):
        """Test band level detection with missing or invalid scores"""
        
        print("\n⚠️  Testing Band Level Detection with Missing Data")
        print("-" * 50)
        
        test_cases = [
            ({}, "A1", "Empty results should default to A1"),
            ({"pronunciation": {"invalid": "data"}}, "A1", "Invalid data should default to A1"),
            ({"pronunciation": {"grade": "not_a_number"}}, "A1", "Non-numeric grades should default to A1"),
            ({"pronunciation": {"grade": 75}}, "B2", "Single valid score should work"),
            ({"pronunciation": {"grade": 150}}, "A1", "Out of range scores should be ignored")
        ]
        
        for analysis_results, expected_band, description in test_cases:
            result = determine_band_level_from_scores(analysis_results)
            
            print(f"Test: {description}")
            print(f"Input: {analysis_results}")
            print(f"Detected Band: {result.detected_band}")
            print(f"Confidence: {result.confidence_score:.2f}")
            print()
            
            assert result.detected_band == expected_band, f"Expected {expected_band}, got {result.detected_band}"
    
    def test_band_progression_mapping(self):
        """Test CEFR band progression mapping"""
        
        print("\n📈 Testing Band Progression Mapping")
        print("-" * 50)
        
        expected_progressions = {
            "A1": "A2",
            "A2": "B1", 
            "B1": "B2",
            "B2": "C1",
            "C1": "C2",
            "C2": "C2"  # C2 stays at C2
        }
        
        for current_band, expected_target in expected_progressions.items():
            actual_target = BAND_PROGRESSION.get(current_band)
            print(f"{current_band} → {actual_target} (expected: {expected_target})")
            assert actual_target == expected_target, f"Expected {current_band} → {expected_target}, got {actual_target}"
    
    def test_improvement_instructions(self):
        """Test improvement instructions for different CEFR progressions"""
        
        print("\n📚 Testing Improvement Instructions")
        print("-" * 50)
        
        test_progressions = [("A1", "A2"), ("A2", "B1"), ("B1", "B2"), ("B2", "C1"), ("C1", "C2")]
        
        for current_band, target_band in test_progressions:
            instructions = get_improvement_instructions(current_band, target_band)
            
            print(f"{current_band} → {target_band}:")
            print(f"Instructions: {instructions[:100]}...")
            print()
            
            assert isinstance(instructions, str), "Instructions should be a string"
            assert len(instructions) > 0, "Instructions should not be empty"
    
    @pytest.mark.asyncio
    async def test_mock_openai_restructuring(self):
        """Test OpenAI API call with mocked response"""
        
        print("\n🤖 Testing Mocked OpenAI Restructuring")
        print("-" * 50)
        
        original_transcript = "I like to eat food. Food is good. I eat every day."
        improved_transcript = "I have a strong appreciation for culinary experiences. Nutritious meals are essential for well-being. I maintain regular dining habits to support my health."
        
        # Mock the OpenAI API response
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": improved_transcript
                    }
                }
            ]
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Configure mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await call_openai_for_restructuring(original_transcript, "A1", "A2")
            
            print(f"Original: {original_transcript}")
            print(f"Improved: {result}")
            
            assert result == improved_transcript, "Should return the improved transcript from API"
            mock_post.assert_called_once()  # Verify API was called
    
    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self):
        """Test OpenAI API error handling"""
        
        print("\n⚠️  Testing OpenAI API Error Handling")
        print("-" * 50)
        
        original_transcript = "Test transcript for error handling."
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock API error
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await call_openai_for_restructuring(original_transcript, "A1", "A2")
            
            print(f"Original: {original_transcript}")
            print(f"Result (should be original): {result}")
            
            assert result == original_transcript, "Should return original text on API error"
    
    @pytest.mark.asyncio
    async def test_restructure_paragraph_with_known_band(self):
        """Test paragraph restructuring with known band level"""
        
        print("\n🔄 Testing Paragraph Restructuring with Known Band")
        print("-" * 50)
        
        transcript = "I like school. School is good. I learn many things."
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            mock_openai.return_value = "I have a genuine appreciation for my educational institution. The academic environment provides valuable learning opportunities. I acquire extensive knowledge through various subjects."
            
            result = await restructure_paragraph(
                transcript=transcript,
                current_band="A1"
            )
            
            print(f"Original Band: {result.original_band}")
            print(f"Target Band: {result.target_band}")
            print(f"Original: {transcript}")
            print(f"Improved: {result.improved_transcript}")
            
            assert result.original_band == "A1"
            assert result.target_band == "A2"
            assert result.improved_transcript != transcript
            mock_openai.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_restructure_paragraph_with_analysis_results(self):
        """Test paragraph restructuring with analysis results for band detection"""
        
        print("\n🔄 Testing Paragraph Restructuring with Analysis Results")
        print("-" * 50)
        
        transcript = "Technology is important. We use it every day. It helps us work."
        analysis_results = {
            "pronunciation": {"grade": 65},
            "fluency": {"grade": 60},
            "grammar": {"grade": 70},
            "lexical": {"grade": 62},
            "vocabulary": {"grade": 58}
        }
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            mock_openai.return_value = "Technology plays a crucial role in modern society. We integrate it into our daily routines seamlessly. It significantly enhances our productivity and efficiency."
            
            result = await restructure_paragraph(
                transcript=transcript,
                analysis_results=analysis_results
            )
            
            print(f"Analysis Scores: {analysis_results}")
            print(f"Detected Band: {result.original_band}")
            print(f"Target Band: {result.target_band}")
            print(f"Original: {transcript}")
            print(f"Improved: {result.improved_transcript}")
            
            assert result.original_band == "B1"  # Should detect B1 based on scores
            assert result.target_band == "B2"
            assert result.improved_transcript != transcript
    
    @pytest.mark.asyncio
    async def test_restructure_paragraph_at_highest_level(self):
        """Test paragraph restructuring when already at highest CEFR level"""
        
        print("\n🎯 Testing Paragraph Restructuring at Highest Level")
        print("-" * 50)
        
        transcript = "The intricate ramifications of technological advancement necessitate comprehensive evaluation."
        
        result = await restructure_paragraph(
            transcript=transcript,
            current_band="C2"
        )
        
        print(f"Original Band: {result.original_band}")
        print(f"Target Band: {result.target_band}")
        print(f"Transcript (should be unchanged): {result.improved_transcript}")
        
        assert result.original_band == "C2"
        assert result.target_band == "C2"
        assert result.improved_transcript == transcript  # Should remain unchanged
    
    @pytest.mark.asyncio
    async def test_analyze_paragraph_restructuring_request(self):
        """Test the main analyze function with ParagraphRestructuringRequest"""
        
        print("\n📝 Testing Analyze Paragraph Restructuring Request")
        print("-" * 50)
        
        request = ParagraphRestructuringRequest(
            transcript="I study English. English is difficult. But I practice every day.",
            current_band="A2"
        )
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            mock_openai.return_value = "I am studying English language acquisition. Although English presents considerable challenges, I maintain consistent daily practice to improve my proficiency."
            
            result = await analyze_paragraph_restructuring(request)
            
            print(f"Request Band: {request.current_band}")
            print(f"Result Original Band: {result.original_band}")
            print(f"Result Target Band: {result.target_band}")
            print(f"Original: {request.transcript}")
            print(f"Improved: {result.improved_transcript}")
            
            assert result.original_band == "A2"
            assert result.target_band == "B1"
            assert result.improved_transcript != request.transcript
    
    @pytest.mark.asyncio
    async def test_error_handling_in_restructure_paragraph(self):
        """Test error handling in paragraph restructuring"""
        
        print("\n⚠️  Testing Error Handling in Restructure Paragraph")
        print("-" * 50)
        
        transcript = "Test transcript for error handling."
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            # Mock an exception in the OpenAI call
            mock_openai.side_effect = Exception("API call failed")
            
            result = await restructure_paragraph(
                transcript=transcript,
                current_band="A1"
            )
            
            print(f"Original: {transcript}")
            print(f"Result (should be original): {result.improved_transcript}")
            print(f"Original Band: {result.original_band}")
            print(f"Target Band: {result.target_band}")
            
            # Should return original transcript on error but still provide band info
            assert result.improved_transcript == transcript
            assert result.original_band == "A1"
            assert result.target_band == "A2" 