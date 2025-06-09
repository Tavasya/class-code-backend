# app/core/config.py
from supabase import create_client, Client
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    "https://native-devserver.vercel.app"
]

# # Google Cloud Pub/Sub Configuration
# GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
# GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "path/to/your/credentials.json")

# # Default Pub/Sub topics and subscriptions
# DEFAULT_TOPIC = "audio-analysis"
# DEFAULT_SUBSCRIPTION = "audio-analysis-sub"
#delpy gclooud

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = None
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    else:
        logger.warning("Supabase credentials not found in environment variables")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")

# URLs
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

#v1
