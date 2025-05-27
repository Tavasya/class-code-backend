# app/core/config.py
from supabase import create_client, Client
import logging
#import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CORS Configuration
CORS_ORIGINS = [
    "https://class-code-nu.vercel.app",
    "https://www.class-code-nu.vercel.app",
    "http://localhost:8080",
    "http://localhost:8081",
    "https://app.nativespeaking.ai",
    "http://localhost:5173",
]

# # Google Cloud Pub/Sub Configuration
# GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
# GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "path/to/your/credentials.json")

# # Default Pub/Sub topics and subscriptions
# DEFAULT_TOPIC = "audio-analysis"
# DEFAULT_SUBSCRIPTION = "audio-analysis-sub"
#delpy gclooud

# Supabase Configuration
SUPABASE_URL = "https://drcsbokflpzbhuzsksws.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyY3Nib2tmbHB6Ymh1enNrc3dzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU5NDU5MDEsImV4cCI6MjA2MTUyMTkwMX0.yooduUfC1Xecr4LAaIeVA1-BLMe6STQHbzprNt2h6Zs"

# Initialize Supabase client
supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")

# API Keys
OPENAI_API_KEY = "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"
AZURE_SPEECH_KEY = "CA4BV9f9rvEKQL22h6L383ucFVNHl9HvkS9bYsBR8xI6cdJm85fHJQQJ99BEACYeBjFXJ3w3AAAYACOGS9sl"
AZURE_SPEECH_REGION = "eastus"
ASSEMBLYAI_API_KEY = "2dbe40dc3dc0413ebf929da37dd61441"

# URLS
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
