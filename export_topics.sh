PROJECT_ID="local-dev"  # or any fake project ID

TOPICS=('student-submission-topic', 'transcription-done-topic', 'fluency-done-topic', 'pronoun-done-topic', 'submission-analyis-complete-topic', 'audio-conversion-done-topic', 'analysis-complete-topic', 'question-analysis-ready-topic', 'lexical-done-topic', 'grammer-done-topic')

for TOPIC in "${TOPICS[@]}"; do
  gcloud pubsub topics create "$TOPIC" --project="$PROJECT_ID"
done