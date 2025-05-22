import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Cloud Pub/Sub Configuration

GCLOUD_PROJECT_ID = "classconnect-455912"

GOOGLE_CLOUD_PROJECT = GCLOUD_PROJECT_ID

# Retry Configuration
# MAX_RETRIES = 3
# RETRY_DELAY = 1.0  # seconds 