from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import aiohttp
import tempfile
import json
import os
from datetime import datetime
import logging
from supabase import create_client, Client
import uvicorn

# Import our modules
import pronoun
import grammar

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Audio Analysis API")

# Configure CORS
origins = [
    "https://class-code-nu.vercel.app",  
    "https://www.class-code-nu.vercel.app",  
    "http://localhost:8080",
    "http://localhost:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
else:
    logger.warning("Missing Supabase credentials in environment variables")

class AnalysisRequest(BaseModel):
    urls: List[str]
    submission_id: str

class AnalysisResponse(BaseModel):
    status: str
    message: str
    submission_id: str

def _save_locally(data: Dict[str, Any], filename: str):
    """Helper function to save data locally"""
    try:
        local_dir = os.environ.get("LOCAL_BACKUP_DIR", "output")
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results locally to {local_path}")
    except Exception as e:
        logger.error(f"Failed to save locally: {str(e)}")

async def upload_to_supabase(data: Dict[str, Any], filename: str) -> bool:
    """
    Upload results to Supabase
    
    Args:
        data: The data to upload
        filename: The filename to use
        
    Returns:
        bool: True if upload was successful, False otherwise
    """
    if not filename.endswith('.json'):
        filename = f"{filename}.json"
    
    # Check if Supabase client is available
    if not supabase:
        logger.error("Supabase client not initialized. Check environment variables.")
        # Fall back to local storage
        _save_locally(data, filename)
        return False
    
    json_data = json.dumps(data, ensure_ascii=False)
    temp_path = None
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
            temp_path = tmp_file.name
            tmp_file.write(json_data)
        
        # Upload to Supabase
        with open(temp_path, 'rb') as f:
            response = supabase.storage.from_('analysis-results').upload(
                path=filename,
                file=f,
                file_options={"content-type": "application/json"},
                # Add upsert option to overwrite existing files with same name
                
            )
        
        logger.info(f"Successfully uploaded {filename} to Supabase")
        return True
        
    except Exception as e:
        logger.error(f"Supabase upload error for {filename}: {str(e)}")
        # Fall back to local storage
        _save_locally(data, filename)
        return False
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_path}: {str(e)}")

async def download_audio(url: str) -> str:
    """Download audio to temp file"""
    file_extension = os.path.splitext(url)[1].lower() or '.webm'
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_path = temp.name
    temp.close()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status, 
                        detail=f"Failed to download audio: {response.reason}"
                    )
                
                with open(temp_path, 'wb') as f:
                    f.write(await response.read())
                
        return temp_path
    
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise Exception(f"Failed to download audio: {str(e)}")

async def process_submission(urls: List[str], submission_id: str):
    """Background task to process audio files"""
    logger.info(f"Starting analysis for submission {submission_id}")
    
    # Ensure submission_id is clean and suitable for a filename
    clean_submission_id = "".join(c for c in submission_id if c.isalnum() or c in "-_").strip()
    if not clean_submission_id:
        clean_submission_id = f"submission_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    results = {
        "submission_id": submission_id,  # Keep original ID in the data
        "timestamp": datetime.now().isoformat(),
        "status": "processing",
        "file_count": len(urls),
        "pronunciation_analysis": [],
        "grammar_analysis": {},
        "vocabulary_suggestions": {}
    }
    
    try:
        # Upload initial processing status
        await upload_to_supabase(results, f"{clean_submission_id}_status")
        
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            temp_file = None
            
            try:
                temp_file = await download_audio(url)
                pronun_result = await pronoun.analyze_audio_file(temp_file)
                pronun_result["url"] = url
                results["pronunciation_analysis"].append(pronun_result)
                
                transcript = pronun_result.get("transcript", "")
                if transcript:
                    gram_result = await grammar.analyze_grammar(transcript)
                    results["grammar_analysis"].update(gram_result["grammar_corrections"])
                    results["vocabulary_suggestions"].update(gram_result["vocabulary_suggestions"])
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                results["pronunciation_analysis"].append({
                    "url": url,
                    "error": str(e),
                    "status": "failed"
                })
            
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file: {str(e)}")
        
        # Update final status
        results["status"] = "completed"
        success = await upload_to_supabase(results, clean_submission_id)
        
        if success:
            logger.info(f"Completed analysis for submission {submission_id}")
        else:
            logger.warning(f"Analysis completed but upload may have failed for {submission_id}")
        
    except Exception as e:
        logger.error(f"Fatal error in process_submission: {str(e)}")
        error_report = {
            "submission_id": submission_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
        await upload_to_supabase(error_report, f"{clean_submission_id}_error")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze audio files endpoint"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    if not request.submission_id:
        raise HTTPException(status_code=400, detail="No submission ID provided")
    
    # Validate submission_id format
    clean_submission_id = "".join(c for c in request.submission_id if c.isalnum() or c in "-_").strip()
    if not clean_submission_id:
        raise HTTPException(status_code=400, detail="Invalid submission ID format")
    
    background_tasks.add_task(process_submission, request.urls, request.submission_id)
    
    return {
        "status": "processing",
        "message": f"Analysis started for {len(request.urls)} audio files",
        "submission_id": request.submission_id
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    supabase_status = "connected" if supabase else "not connected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "supabase": supabase_status
    }

@app.get("/test-upload")
async def test_upload():
    """Test Supabase upload functionality"""
    test_data = {
        "test": True,
        "timestamp": datetime.now().isoformat()
    }
    
    test_filename = f"test_upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    success = await upload_to_supabase(test_data, test_filename)
    
    if success:
        return {
            "status": "success",
            "message": f"Test upload successful: {test_filename}.json"
        }
    else:
        return {
            "status": "error",
            "message": "Test upload failed. Check logs for details."
        }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)