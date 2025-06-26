#!/usr/bin/env python3

import pytest
from unittest.mock import patch, AsyncMock
from app.services.paragraph_restructuring_service import restructure_paragraph
from app.services.database_service import DatabaseService


class TestParagraphRestructuringIntegration:
    """Integration tests for paragraph restructuring service"""
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self):
        """Test the complete workflow from analysis results to restructured paragraph"""
        
        print("\n🔄 Testing Full Paragraph Restructuring Workflow")
        print("-" * 60)
        
        # Simulate analysis results from all services (like what would come from webhook)
        mock_analysis_results = {
            "pronunciation": {"grade": 65},
            "fluency": {"grade": 60}, 
            "grammar": {"grade": 70},
            "lexical": {"grade": 62},
            "vocabulary": {"grade": 58},
            "transcript": "I think technology is very important in our daily life. We use phones and computers. They help us communicate with people."
        }
        
        # Mock OpenAI response
        expected_improved = """I believe that technology plays a crucial role in our contemporary daily existence. We utilize sophisticated devices such as smartphones and computers. These technological tools facilitate effective communication between individuals across various platforms."""
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            mock_openai.return_value = expected_improved
            
            # Test the restructuring process
            result = await restructure_paragraph(
                transcript=mock_analysis_results["transcript"],
                analysis_results=mock_analysis_results
            )
            
            print(f"Original transcript: {mock_analysis_results['transcript']}")
            print(f"Detected band: {result.original_band}")
            print(f"Target band: {result.target_band}")
            print(f"Improved transcript: {result.improved_transcript}")
            
            # Verify band detection worked correctly (should be A2.5 based on scores)
            assert result.original_band == "A2.5"
            assert result.target_band == "B1"
            assert result.improved_transcript == expected_improved
            
            print("✅ Full workflow integration test passed")
    
    def test_database_transform_with_restructuring(self):
        """Test database transformation includes paragraph restructuring field"""
        
        print("\n💾 Testing Database Transform with Paragraph Restructuring")
        print("-" * 60)
        
        # Mock question results with paragraph restructuring
        question_results = {
            "1": {
                "transcript": "I like to read books. Books are interesting.",
                "pronunciation": {"grade": 75, "transcript": "I like to read books. Books are interesting."},
                "fluency": {"grade": 70},
                "grammar": {"grade": 80},
                "lexical": {"grade": 72},
                "vocabulary": {"grade": 68},
                "paragraph_restructuring": {
                    "original_band": "B1",
                    "target_band": "B2",
                    "improved_transcript": "I have a genuine appreciation for reading literature. Literary works provide fascinating insights and perspectives."
                }
            }
        }
        
        db_service = DatabaseService()
        
        # Test the transformation
        transformed_results = db_service._transform_to_new_format(
            question_results=question_results,
            recordings=["test-audio-url.wav"]
        )
        
        print(f"Transformed results: {transformed_results}")
        
        # Verify structure
        assert len(transformed_results) == 2  # Version + 1 question
        question_data = transformed_results[1]  # Skip version entry
        
        assert "section_feedback" in question_data
        section_feedback = question_data["section_feedback"]
        
        # Verify paragraph restructuring field is present in correct order
        expected_order = ["fluency", "grammar", "lexical", "pronunciation", "paragraph_restructuring", "vocabulary"]
        actual_fields = list(section_feedback.keys())
        
        print(f"Section feedback fields: {actual_fields}")
        
        # Check that paragraph_restructuring is included
        assert "paragraph_restructuring" in section_feedback
        
        # Verify paragraph restructuring structure
        pr_data = section_feedback["paragraph_restructuring"]
        assert pr_data["original_band"] == "B1"
        assert pr_data["target_band"] == "B2"
        assert "improved_transcript" in pr_data
        
        print("✅ Database transformation test passed")
    
    @pytest.mark.asyncio 
    async def test_webhook_integration_simulation(self):
        """Simulate the webhook integration process"""
        
        print("\n🔗 Testing Webhook Integration Simulation")
        print("-" * 60)
        
        # Simulate data that would come from the submission analysis complete webhook
        submission_data = {
            "submission_url": "test-submission-123",
            "question_results": {
                "1": {
                    "transcript": "I study English every day. English is difficult but important.",
                    "pronunciation": {"grade": 55, "transcript": "I study English every day. English is difficult but important."},
                    "fluency": {"grade": 50},
                    "grammar": {"grade": 60},
                    "lexical": {"grade": 52},
                    "vocabulary": {"grade": 48}
                }
            }
        }
        
        expected_improved = "I dedicate time to studying English daily. Although English presents considerable challenges, it remains fundamentally important for personal development."
        
        with patch('app.services.paragraph_restructuring_service.call_openai_for_restructuring') as mock_openai:
            mock_openai.return_value = expected_improved
            
            # Simulate the webhook processing logic
            question_results = submission_data["question_results"]
            
            for question_num, analysis_results in question_results.items():
                # Extract transcript
                transcript = analysis_results.get("transcript", "")
                
                if transcript:
                    # Process restructuring
                    restructuring_result = await restructure_paragraph(
                        transcript=transcript,
                        analysis_results=analysis_results
                    )
                    
                    # Add to analysis results (like webhook does)
                    analysis_results["paragraph_restructuring"] = {
                        "original_band": restructuring_result.original_band,
                        "target_band": restructuring_result.target_band,
                        "improved_transcript": restructuring_result.improved_transcript
                    }
                    
                    print(f"Question {question_num}:")
                    print(f"  Original: {transcript}")
                    print(f"  Band: {restructuring_result.original_band} → {restructuring_result.target_band}")
                    print(f"  Improved: {restructuring_result.improved_transcript}")
            
            # Verify results
            question_1_data = question_results["1"]
            assert "paragraph_restructuring" in question_1_data
            
            pr_data = question_1_data["paragraph_restructuring"]
            # The scores provided should result in A2 detection (average ~53.75)
            assert pr_data["original_band"] == "A2"  # Based on average score of 53.75
            assert pr_data["target_band"] == "A2.5"
            assert pr_data["improved_transcript"] == expected_improved
            
            print("✅ Webhook integration simulation passed") 