import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os
from openai import OpenAI
from app.core.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

@dataclass
class IELTSScore:
    fluency_and_coherence: float
    lexical_resource: float
    grammatical_range_and_accuracy: float
    pronunciation: float
    overall: float

class IELTSScoringService:
    """Service for calculating IELTS band scores based on analysis results"""
    
    def __init__(self):
        """Initialize the IELTS scoring service"""
        # Initialize OpenAI client if API key is available
        self.client = None
        if OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized for IELTS scoring")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {str(e)}")
        else:
            logger.warning("No OpenAI API key available, will use fallback scoring")
    
    def calculate_ielts_score(self, question_results: Dict[str, Any], questions: List[Dict]) -> IELTSScore:
        """
        Calculate IELTS band score based on analysis results
        
        Args:
            question_results: Dictionary of question analysis results
            questions: List of question objects from assignment
            
        Returns:
            IELTSScore object with all band scores
        """
        try:
            logger.info(f"Starting IELTS score calculation for {len(question_results)} questions")
            
            # Process all questions to extract assessment data
            processed_data = []
            
            for q_num, q_data in question_results.items():
                if not q_data or not isinstance(q_data, dict):
                    continue
                
                # Extract transcript
                transcript = ""
                if "transcript" in q_data:
                    transcript = q_data["transcript"] or ""
                elif "pronunciation" in q_data and isinstance(q_data["pronunciation"], dict):
                    transcript = q_data["pronunciation"].get("transcript", "")
                
                # Extract section feedback
                section_feedback = {}
                if "section_feedback" in q_data:
                    section_feedback = q_data["section_feedback"]
                else:
                    # Fallback to direct analysis results
                    section_feedback = {
                        "fluency": q_data.get("fluency", {}),
                        "grammar": q_data.get("grammar", {}),
                        "lexical": q_data.get("lexical", {}),
                        "vocabulary": q_data.get("vocabulary", {}),
                        "pronunciation": q_data.get("pronunciation", {})
                    }
                
                # Get question text
                question_text = ""
                try:
                    q_idx = int(q_num) - 1
                    if 0 <= q_idx < len(questions):
                        question_text = questions[q_idx].get("question", "")
                except (ValueError, IndexError):
                    pass
                
                assessment_data = {
                    "transcript": transcript,
                    "question": question_text,
                    "question_id": int(q_num),
                    "section_feedback": section_feedback,
                    "duration_feedback": q_data.get("duration_feedback", {})
                }
                processed_data.append(assessment_data)
            
            if not processed_data:
                logger.warning("No valid assessment data found for IELTS scoring")
                return self._create_default_score()
            
            # Calculate IELTS scores using the algorithm
            return self._predict_ielts_band_score(processed_data)
            
        except Exception as e:
            logger.error(f"Error calculating IELTS score: {str(e)}")
            return self._create_default_score()
    
    def _predict_ielts_band_score(self, assessment_data: List[Dict]) -> IELTSScore:
        """Predict IELTS band score based on assessment data using the provided algorithm"""
        try:
            # Initialize scores
            fluency_scores = []
            grammar_scores = []
            lexical_scores = []
            pronunciation_scores = []
            
            total_responses = len(assessment_data)
            problematic_responses = 0
            empty_responses = 0
            very_short_responses = 0
            total_words = 0
            low_cohesive_count = 0
            
            # Process each response
            for data in assessment_data:
                feedback = data['section_feedback']
                transcript = data.get('transcript', '').strip()
                
                # Check for empty or extremely minimal responses
                word_count = len(transcript.split()) if transcript else 0
                is_minimal_response = word_count < 3
                is_empty_response = word_count == 0
                
                # Extract existing grades/scores
                fluency_data = feedback.get('fluency', {})
                grammar_data = feedback.get('grammar', {})
                lexical_data = feedback.get('lexical', {})
                vocabulary_data = feedback.get('vocabulary', {})
                pronunciation_data = feedback.get('pronunciation', {})
                
                # Apply severe penalties for empty/minimal responses
                if is_empty_response:
                    fluency_score = 1.0
                    grammar_score = 1.0
                    lexical_score = 1.0
                    pronunciation_score = 1.0
                    empty_responses += 1
                elif is_minimal_response:
                    fluency_score = 2.0
                    grammar_score = 2.5
                    lexical_score = 2.5
                    pronunciation_score = 2.5
                    very_short_responses += 1
                else:
                    # Normal scoring for substantial responses
                    fluency_score = self._convert_to_ielts_band(fluency_data.get('grade', 50))
                    grammar_score = self._convert_to_ielts_band(grammar_data.get('grade', 50))
                    lexical_score = self._convert_to_ielts_band(lexical_data.get('grade', 50))
                    vocabulary_score = self._convert_to_ielts_band(vocabulary_data.get('grade', 50))
                    pronunciation_score = self._convert_to_ielts_band(pronunciation_data.get('grade', 50))
                    
                    # Apply length penalties for very short responses
                    if word_count < 5:
                        fluency_score = min(fluency_score, 3.0)
                        lexical_score = min(lexical_score, 3.0)
                    elif word_count < 8:
                        fluency_score = min(fluency_score, 4.0)
                        lexical_score = min(lexical_score, 4.0)
                    
                    # Detect potentially irrelevant responses
                    vocab_grade = vocabulary_data.get('grade', 50)
                    lexical_grade = lexical_data.get('grade', 50)
                    
                    if vocab_grade < 20 and lexical_grade > 80:
                        fluency_score = min(fluency_score, 3.0)
                        lexical_score = min(lexical_score, 3.5)
                        grammar_score = min(grammar_score, 4.0)
                
                # Use LLM for nuanced fluency assessment (skip for empty/minimal responses)
                if not (is_empty_response or is_minimal_response):
                    llm_fluency_score = self._llm_assess_fluency(transcript, data['question'])
                    fluency_score = self._adjust_fluency_score(
                        fluency_score, fluency_data, data.get('duration_feedback', {}), 
                        feedback.get('paragraph_restructuring', {}), llm_fluency_score
                    )
                
                # Apply detailed adjustments
                fluency_score = self._adjust_fluency_score(
                    fluency_score, fluency_data, data.get('duration_feedback', {}), 
                    feedback.get('paragraph_restructuring', {}), fluency_score
                )
                grammar_score = self._adjust_grammar_score(grammar_score, grammar_data)
                lexical_score = self._adjust_lexical_score(lexical_score, lexical_data, vocabulary_data)
                pronunciation_score = self._adjust_pronunciation_score(pronunciation_score, pronunciation_data)
                
                # Collect scores
                fluency_scores.append(fluency_score)
                grammar_scores.append(grammar_score)
                lexical_scores.append(lexical_score)
                pronunciation_scores.append(pronunciation_score)
                
                # Track problematic responses
                total_words += word_count
                vocab_grade = vocabulary_data.get('grade', 50)
                
                if (word_count == 0 or 
                    (word_count < 3 and vocab_grade < 50) or 
                    vocab_grade < 20):
                    problematic_responses += 1
                
                # Check cohesive device levels
                cohesive_level = fluency_data.get('cohesive_device_band_level', 3)
                if cohesive_level <= 1:
                    low_cohesive_count += 1
            
            # Calculate averages
            avg_fluency = sum(fluency_scores) / len(fluency_scores) if fluency_scores else 0
            avg_grammar = sum(grammar_scores) / len(grammar_scores) if grammar_scores else 0
            avg_lexical = sum(lexical_scores) / len(lexical_scores) if lexical_scores else 0
            avg_pronunciation = sum(pronunciation_scores) / len(pronunciation_scores) if pronunciation_scores else 0
            
            # Calculate overall score
            overall_score = (avg_fluency + avg_grammar + avg_lexical + avg_pronunciation) / 4
            
            # Apply Band 2.5 detection
            problematic_ratio = problematic_responses / total_responses if total_responses > 0 else 0
            empty_ratio = empty_responses / total_responses if total_responses > 0 else 0
            very_short_ratio = very_short_responses / total_responses if total_responses > 0 else 0
            avg_words_per_response = total_words / total_responses if total_responses > 0 else 0
            low_cohesive_ratio = low_cohesive_count / total_responses if total_responses > 0 else 0
            
            # Band 2.5 detection: multiple severe indicators
            band25_indicators = 0
            if empty_ratio > 0.15: band25_indicators += 1
            if very_short_ratio > 0.3: band25_indicators += 1
            if avg_words_per_response < 8: band25_indicators += 1
            if low_cohesive_ratio > 0.4: band25_indicators += 1
            
            if band25_indicators >= 2 or empty_ratio > 0.2:
                overall_score = min(overall_score, 2.5)
            elif problematic_ratio > 0.35:
                overall_score = min(overall_score, 3.0)
            elif problematic_ratio > 0.2:
                overall_score = min(overall_score, 4.0)
            
            # Address Band 6 over-scoring
            band6_indicators = 0
            for data in assessment_data:
                fluency_data = data.get('section_feedback', {}).get('fluency', {})
                cohesive_level = fluency_data.get('cohesive_device_band_level', 3)
                wpm = fluency_data.get('wpm', 0)
                if 80 <= wpm <= 110 and 5 <= cohesive_level <= 6:
                    band6_indicators += 1
            
            band6_ratio = band6_indicators / total_responses if total_responses > 0 else 0
            if band6_ratio > 0.6 and overall_score > 6.5:
                overall_score = min(overall_score, 6.5)
            
            # Standard compression for very high/low scores
            if overall_score > 8.5:
                overall_score = 8.5 + (overall_score - 8.5) * 0.5
            elif overall_score < 2.0:
                overall_score = max(1.5, overall_score)
            
            # Round to nearest 0.5
            overall_score = round(overall_score * 2) / 2
            avg_fluency = round(avg_fluency * 2) / 2
            avg_grammar = round(avg_grammar * 2) / 2
            avg_lexical = round(avg_lexical * 2) / 2
            avg_pronunciation = round(avg_pronunciation * 2) / 2
            
            logger.info(f"IELTS scores calculated - Overall: {overall_score}, Fluency: {avg_fluency}, Grammar: {avg_grammar}, Lexical: {avg_lexical}, Pronunciation: {avg_pronunciation}")
            
            return IELTSScore(
                fluency_and_coherence=avg_fluency,
                lexical_resource=avg_lexical,
                grammatical_range_and_accuracy=avg_grammar,
                pronunciation=avg_pronunciation,
                overall=overall_score
            )
            
        except Exception as e:
            logger.error(f"Error in IELTS band score prediction: {str(e)}")
            return self._create_default_score()
    
    def _convert_to_ielts_band(self, grade: float) -> float:
        """Convert percentage grade to IELTS band score (1-9) - Universal accuracy calibration"""
        if grade >= 95:
            return 9.0
        elif grade >= 88:
            return 8.5
        elif grade >= 82:
            return 8.0
        elif grade >= 76:
            return 7.5
        elif grade >= 70:
            return 7.0
        elif grade >= 65:
            return 6.5
        elif grade >= 60:
            return 6.0
        elif grade >= 55:
            return 5.5
        elif grade >= 50:
            return 5.0
        elif grade >= 45:
            return 4.5
        elif grade >= 40:
            return 4.0
        elif grade >= 35:
            return 3.5
        elif grade >= 30:
            return 3.0
        elif grade >= 25:
            return 2.5
        elif grade >= 15:
            return 2.0
        else:
            return 1.5
    
    def _llm_assess_fluency(self, transcript: str, question: str) -> float:
        """Use LLM to assess fluency with universal accuracy calibration"""
        if not self.client:
            return 7.0  # Default fallback
        
        prompt = f"""
You are an expert IELTS examiner. Rate ONLY fluency and coherence (1-9).

QUESTION: {question}
RESPONSE: {transcript}

IELTS BAND DESCRIPTORS:
BAND 9: Perfect fluency, natural speech
BAND 8: Very fluent with minimal hesitation, natural flow
BAND 7: Fluent without noticeable effort, occasional language-related hesitation
BAND 6: Willing to speak at length, some loss of coherence
BAND 5: Maintains flow but repetition/self-correction needed
BAND 4: Basic fluency on familiar topics, frequent pauses
BAND 3: Frequent pauses, limited fluency
BAND 2: Long pauses, very limited speech
BAND 1: Minimal communication

Assessment criteria:
- Natural speech rhythm and pace
- Effort required to maintain communication
- Coherence and logical development
- Use of linking devices appropriately

Be precise and use the full 1-9 range. Respond with ONLY a number.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an IELTS examiner. Be generous for natural, fluent speech. Respond with only a number."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=10
            )
            
            score_text = response.choices[0].message.content.strip()
            score = float(score_text)
            return max(1.0, min(9.0, score))
        except Exception as e:
            logger.warning(f"LLM fluency assessment failed: {str(e)}")
            return 7.0  # Default to Band 7
    
    def _adjust_fluency_score(self, base_score: float, fluency_data: Dict, duration_data: Dict, paragraph_data: Dict, llm_score: float) -> float:
        """Adjust fluency score with universal accuracy calibration"""
        # Balanced weighting between LLM and algorithmic assessment
        combined_score = (llm_score * 0.6) + (base_score * 0.4)
        adjustments = 0
        
        # WPM assessment calibrated for all bands
        wpm = fluency_data.get('wpm', 0)
        if wpm > 130:
            adjustments += 0.75
        elif wpm > 110:
            adjustments += 0.5
        elif wpm > 90:
            adjustments += 0.25
        elif wpm < 50:
            adjustments -= 0.5
        elif wpm < 70:
            adjustments -= 0.25
            
        # Filler words assessment
        filler_count = fluency_data.get('filler_word_count', 0)
        if filler_count == 0:
            adjustments += 0.75
        elif filler_count <= 2:
            adjustments += 0.5
        elif filler_count <= 4:
            adjustments += 0.25
        elif filler_count > 8:
            adjustments -= 0.5
            
        # Cohesive device band level bonus
        cohesive_band = fluency_data.get('cohesive_device_band_level', 3)
        if cohesive_band >= 7:
            adjustments += 0.5
        elif cohesive_band >= 6:
            adjustments += 0.25
        elif cohesive_band <= 2:
            adjustments -= 0.5
            
        final_score = combined_score + adjustments
        
        # Minimal compression to preserve accuracy
        if final_score > 9.0:
            final_score = 9.0
        elif final_score < 1.0:
            final_score = 1.0
            
        return max(1.0, min(9.0, round(final_score * 2) / 2))
    
    def _adjust_grammar_score(self, base_score: float, grammar_data: Dict) -> float:
        """Adjust grammar score with universal accuracy calibration"""
        adjustments = 0
        corrections = grammar_data.get('grammar_corrections', {})
        correction_count = len(corrections)
        
        # Calibrated for all band levels
        if correction_count == 0:
            adjustments += 1.0
        elif correction_count <= 1:
            adjustments += 0.75
        elif correction_count <= 2:
            adjustments += 0.5
        elif correction_count <= 4:
            adjustments += 0.0
        elif correction_count <= 7:
            adjustments -= 0.25
        else:
            adjustments -= 0.75
        
        adjusted_score = base_score + adjustments
        return max(1.0, min(9.0, round(adjusted_score * 2) / 2))
    
    def _adjust_lexical_score(self, base_score: float, lexical_data: Dict, vocabulary_data: Dict) -> float:
        """Adjust lexical score with universal accuracy calibration"""
        adjustments = 0
        
        # Lexical corrections assessment
        lexical_corrections = lexical_data.get('total_corrections', 0)
        if lexical_corrections == 0:
            adjustments += 0.75
        elif lexical_corrections <= 1:
            adjustments += 0.5
        elif lexical_corrections <= 3:
            adjustments += 0.25
        elif lexical_corrections > 6:
            adjustments -= 0.5
            
        # Vocabulary suggestions assessment
        vocab_suggestions = vocabulary_data.get('vocabulary_suggestions', {})
        suggestion_count = len(vocab_suggestions)
        if suggestion_count == 0:
            adjustments += 0.75
        elif suggestion_count <= 1:
            adjustments += 0.5
        elif suggestion_count <= 3:
            adjustments += 0.25
        elif suggestion_count > 7:
            adjustments -= 0.5
        
        adjusted_score = base_score + adjustments
        return max(1.0, min(9.0, round(adjusted_score * 2) / 2))
    
    def _adjust_pronunciation_score(self, base_score: float, pronunciation_data: Dict) -> float:
        """Adjust pronunciation score based on detailed feedback"""
        adjustments = 0
        
        accuracy_score = pronunciation_data.get('accuracy_score', 0)
        fluency_score = pronunciation_data.get('fluency_score', 0)
        prosody_score = pronunciation_data.get('prosody_score', 0)
        
        if accuracy_score > 0:
            if accuracy_score >= 95:
                adjustments += 0.5
            elif accuracy_score >= 90:
                adjustments += 0.25
            elif accuracy_score < 75:
                adjustments -= 0.5
                
        critical_errors = pronunciation_data.get('critical_errors', [])
        if len(critical_errors) > 3:
            adjustments -= 0.5
        elif len(critical_errors) == 0:
            adjustments += 0.25
        
        adjusted_score = base_score + adjustments
        return max(1.0, min(9.0, round(adjusted_score * 2) / 2))
    
    def _create_default_score(self) -> IELTSScore:
        """Create a default IELTS score when calculation fails"""
        return IELTSScore(
            fluency_and_coherence=5.0,
            lexical_resource=5.0,
            grammatical_range_and_accuracy=5.0,
            pronunciation=5.0,
            overall=5.0
        ) 