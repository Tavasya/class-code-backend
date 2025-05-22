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

# Supabase Configuration
SUPABASE_URL = "https://zyaobehxpcwxlyljzknw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YW9iZWh4cGN3eGx5bGp6a253Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyMzQ1NjcsImV4cCI6MjA1NzgxMDU2N30.mUc1rpE_zecu3XLI8x_jH_QckrNNkLEnqOGp2SQOSdo"

# Initialize Supabase client
supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")

# API Keys
OPENAI_API_KEY = "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"
AZURE_SPEECH_KEY = "CPhzqHVeoa5YnFTLqimhoVB8tiM0aYdtnAnumfNJtVkv3AzHV18PJQQJ99BDACYeBjFXJ3w3AAAYACOGaN2q"
AZURE_SPEECH_REGION = "eastus"
ASSEMBLYAI_API_KEY = "793e69da37b04250a9473ff974eb7157"

# URLS
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
