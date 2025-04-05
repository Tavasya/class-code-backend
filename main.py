from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import aiohttp
import tempfile
import json
import os
from datetime import datetime
import logging
from supabase import create_client, Client

# Import our modules
import pronoun
import grammar

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL","https://zyaobehxpcwxlyljzknw.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YW9iZWh4cGN3eGx5bGp6a253Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyMzQ1NjcsImV4cCI6MjA1NzgxMDU2N30.mUc1rpE_zecu3XLI8x_jH_QckrNNkLEnqOGp2SQOSdo")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

class AnalysisRequest(BaseModel):
    urls: List[str]
    submission_id: str

class AnalysisResponse(BaseModel):
    status: str
    message: str
    submission_id: str

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    API endpoint to analyze audio files for pronunciation and grammar
    """
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    if not request.submission_id:
        raise HTTPException(status_code=400, detail="No submission ID provided")
    
    # Process in background to avoid timeout
    background_tasks.add_task(process_submission, request.urls, request.submission_id)
    
    return {
        "status": "processing",
        "message": f"Analysis started for {len(request.urls)} audio files",
        "submission_id": request.submission_id
    }

async def process_submission(urls: List[str], submission_id: str):
    """
    Process all audio files in a submission
    """
    results = {
        "submission_id": submission_id,
        "timestamp": datetime.now().isoformat(),
        "pronunciation_analysis": [],
        "grammar_analysis": {},
        "vocabulary_suggestions": {}
    }
    
    try:
        # Process each URL
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            temp_file = None
            
            try:
                # Download the audio file
                temp_file = await download_audio(url)
                
                # Analyze pronunciation (this function now handles WebM conversion internally)
                pronun_result = await pronoun.analyze_audio_file(temp_file)
                
                # Add URL to result for reference
                pronun_result["url"] = url
                
                # Add to results
                results["pronunciation_analysis"].append(pronun_result)
                
                # Extract transcript and analyze grammar
                transcript = pronun_result.get("transcript", "")
                if transcript:
                    gram_result = await grammar.analyze_grammar(transcript)
                    
                    # Merge results
                    results["grammar_analysis"].update(gram_result["grammar_corrections"])
                    results["vocabulary_suggestions"].update(gram_result["vocabulary_suggestions"])
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
                # Add error to results
                results["pronunciation_analysis"].append({
                    "url": url,
                    "error": str(e),
                    "status": "failed"
                })
            
            finally:
                # Clean up temp file
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
        
        # Upload results to Supabase
        await upload_to_supabase(results, submission_id)
        logger.info(f"Completed analysis for submission {submission_id}")
        
    except Exception as e:
        logger.error(f"Fatal error in process_submission: {str(e)}")
        # Create error report
        error_report = {
            "submission_id": submission_id,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e)
        }
        await upload_to_supabase(error_report, f"{submission_id}_error")

async def download_audio(url: str) -> str:
    """
    Download audio file from URL to a temporary file
    """
    # Determine file extension from URL
    file_extension = os.path.splitext(url)[1].lower()
    if not file_extension:
        file_extension = '.webm'  # Default to .webm if no extension found
    
    # Create temporary file with correct extension
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_path = temp.name
    temp.close()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, 
                                       detail=f"Failed to download audio: {response.reason}")
                
                with open(temp_path, 'wb') as f:
                    f.write(await response.read())
                
        logger.info(f"Downloaded audio file to {temp_path}")
        return temp_path
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise Exception(f"Failed to download audio: {str(e)}")

async def upload_to_supabase(data: Dict[str, Any], filename: str):
    """
    Upload results to Supabase Storage
    """
    try:
        # Ensure filename has .json extension
        if not filename.endswith('.json'):
            filename = f"{filename}.json"
        
        # Convert data to JSON string
        json_data = json.dumps(data, ensure_ascii=False)
        
        if supabase:
            try:
                # Create a temporary file to store the JSON data
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    tmp_file.write(json_data)
                
                try:
                    # Upload the temporary file to Supabase
                    logger.info(f"Uploading results to Supabase bucket 'analysis-results', path: {filename}")
                    with open(tmp_path, 'rb') as f:
                        response = supabase.storage.from_('analysis-results').upload(
                            path=filename,
                            file=f,
                            file_options={"content-type": "application/json"}
                        )
                    
                    logger.info(f"Uploaded results to Supabase: {filename}")
                    return response
                finally:
                    # Clean up the temporary file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                        
            except Exception as supabase_error:
                logger.error(f"Supabase upload error: {str(supabase_error)}")
                # Fall through to local file saving
        else:
            logger.warning("No Supabase client available, saving locally")
        
        # Save locally (either as fallback or if Supabase failed)
        with open(f"{filename}", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results locally to {filename}")
        
    except Exception as e:
        logger.error(f"Failed to handle results: {str(e)}")
        # Final fallback - try to save locally
        try:
            with open(f"{filename}", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved results locally to {filename} after error")
        except Exception as local_error:
            logger.error(f"Could not save results anywhere: {str(local_error)}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)