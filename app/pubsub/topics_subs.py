from typing import Dict

# Topic Names - Define all available topics here
TOPICS: Dict[str, str] = {
    "ANALYSIS_COMPLETE": "analysis-complete-topic",
    "AUDIO_CONVERSION_DONE": "audio-conversion-done-topic",
    "FLUENCY_DONE": "fluency-done-topic",
    "GRAMMER_DONE": "grammer-done-topic",
    "LEXICAL_DONE": "lexical-done-topic",
    "PRONUNCIATION_DONE": "pronoun-done-topic",
    "QUESTION_ANALYSIS_READY": "question-analysis-ready-topic",
    "STUDENT_SUBMISSION": "student-submission-topic",
    "SUBMISSION_ANALYSIS_COMPLETE": "submission-analyis-complete-topic",
    "TRANSCRIPTION_DONE": "transcription-done-topic",
    "VOCABULARY_DONE": "vocabulary-done-topic"
}

# Subscription Names - Define all available subscriptions here
SUBSCRIPTIONS: Dict[str, str] = {
    "ANALYSIS_COMPLETE": "analysis-complete-topic-sub",
    "AUDIO_CONVERSION_DONE": "audio-conversion-service-sub",
    "FLUENCY_DONE": "fluency-done-topic-sub",
    "GRAMMER_DONE": "grammer-done-topic-sub",
    "LEXICAL_DONE": "lexical-done-topic-sub",
    "PRONUNCIATION_DONE": "pronoun-done-topic-sub",
    "QUESTION_ANALYSIS_READY": "question-analysis-ready-topic-sub",
    "STUDENT_SUBMISSION": "student-submission-topic-sub",
    "SUBMISSION_ANALYSIS_COMPLETE": "submission-analyis-complete-topic-sub",
    "TRANSCRIPTION_DONE": "transcription-service-sub",
    "VOCABULARY_DONE": "vocabulary-done-topic-sub"
}