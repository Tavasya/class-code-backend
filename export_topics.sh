# export_topics.sh
#!/bin/bash

REAL_PROJECT_ID="classconnect-455912"
FAKE_PROJECT_ID="fake-project"

# Pull list of topic names from real project
TOPICS=$(gcloud pubsub topics list --project=$REAL_PROJECT_ID --format="value(name)")

# Create each topic in the emulator under the fake project
for FULL_TOPIC in $TOPICS; do
  TOPIC_ID=$(basename $FULL_TOPIC)
  echo "Creating topic: $TOPIC_ID"
  gcloud pubsub topics create "$TOPIC_ID" --project="$FAKE_PROJECT_ID"
done