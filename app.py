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
import fluency

# Import our modules
import pronoun
import grammar
import fluency

import re

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
    "https://app.nativespeaking.ai",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL","https://drcsbokflpzbhuzsksws.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRyY3Nib2tmbHB6Ymh1enNrc3dzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDU5NDU5MDEsImV4cCI6MjA2MTUyMTkwMX0.yooduUfC1Xecr4LAaIeVA1-BLMe6STQHbzprNt2h6Zs")

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
    
    try:
        # Prepare per-question feedback list
        per_question_feedback = []
        
        # Process each audio file
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
            temp_file = None
            
            try:
                temp_file = await download_audio(url)
                
                # 1. Pronunciation analysis
                try:
                    pronun_result = await pronoun.analyze_audio_file(temp_file)
                    pronunciation_score = pronun_result.get("overall_pronunciation_score", 0)
                    pronunciation_issues = []
                    
                    # Add word-level feedback for all words
                    word_details = pronun_result.get("word_details", [])
                    if word_details:  # Only add if we have word details
                        word_feedback = []
                        for word in word_details:
                            word_feedback.append({
                                "word": word.get("word", ""),
                                "score": word.get("accuracy_score", 0),
                                "error_type": word.get("error_type", "None"),
                                "timestamp": word.get("offset", 0),
                                "duration": word.get("duration", 0)
                            })
                        
                        # Add word-level feedback as a single issue
                        pronunciation_issues.append({
                            "type": "word_scores",
                            "words": word_feedback
                        })
                        
                        # Add overall feedback
                        if pronun_result.get("improvement_suggestion"):
                            pronunciation_issues.append({
                                "type": "suggestion",
                                "message": pronun_result.get("improvement_suggestion")
                            })
                        
                        # Add prosody feedback if score is low
                        if pronun_result.get("prosody_score", 100) < 85:
                            pronunciation_issues.append({
                                "type": "prosody",
                                "score": pronun_result.get("prosody_score"),
                                "message": "Work on natural rhythm and intonation patterns in speech."
                            })
                        
                        # Add fluency feedback if score is low
                        if pronun_result.get("fluency_score", 100) < 85:
                            pronunciation_issues.append({
                                "type": "fluency",
                                "score": pronun_result.get("fluency_score"),
                                "message": "Focus on speaking more smoothly and reducing pauses between words."
                            })
                        
                        # Add overall performance feedback
                        if pronunciation_score >= 90:
                            pronunciation_issues.append({
                                "type": "positive",
                                "message": "Excellent pronunciation with clear articulation and accurate word stress."
                            })
                        elif pronunciation_score >= 80:
                            pronunciation_issues.append({
                                "type": "positive",
                                "message": "Good pronunciation with minor areas for improvement."
                            })
                    else:
                        # If no word details, add raw data for debugging
                        pronunciation_issues.append({
                            "type": "raw_data",
                            "data": pronun_result
                        })
                except Exception as e:
                    logger.error(f"Error in pronunciation analysis: {str(e)}")
                    pronunciation_score = 0
                    pronunciation_issues = [{
                        "type": "error",
                        "message": f"Azure Speech Service Error: {str(e)}"
                    }]
                
                audio_transcript = pronun_result.get("transcript", "") if 'pronun_result' in locals() else ""
                
                # 2. Grammar and lexical analysis
                grammar_issues = []
                lexical_issues = []
                lexical_grade = 100
                if audio_transcript:
                    gram_result = await grammar.analyze_grammar(audio_transcript)
                    
                    # Process grammar corrections
                    for sent_key, sent in gram_result["grammar_corrections"].items():
                        corrections = sent.get("corrections", [])
                        if corrections:
                            for correction in corrections:
                                grammar_issues.append({
                                    "original": sent.get("original", sent.get("sentence", "")),
                                    "correction": correction
                                })
                    
                    # Process vocabulary suggestions
                    if "vocabulary_suggestions" in gram_result:
                        for sent in gram_result["vocabulary_suggestions"].values():
                            for suggestion in sent.get("suggestions", []):
                                lexical_issues.append({
                                    "type": "vocabulary",
                                    "sentence": sent.get("sentence", ""),
                                    "suggestion": suggestion
                                })
                    
                    # Process lexical resources
                    if "lexical_resources" in gram_result:
                        for sent in gram_result["lexical_resources"].values():
                            for suggestion in sent.get("suggestions", []):
                                lexical_issues.append({
                                    "type": "lexical",
                                    "sentence": sent.get("sentence", ""),
                                    "suggestion": suggestion
                                })
                    
                    # Calculate lexical grade based on number of issues
                    lexical_grade = 100 - min(100, len(lexical_issues) * 10)
                
                # 3. Fluency analysis
                fluency_issues = []
                fluency_score = 0
                if audio_transcript:
                    word_details = pronun_result.get("word_details", [])
                    fluency_result = await fluency.analyze_fluency_coherence(audio_transcript, word_details)
                    fluency_metrics = fluency_result.get("fluency_metrics", {})
                    fluency_score = fluency_metrics.get("overall_fluency_score", 0)
                    fluency_issues = fluency_result.get("key_findings", [])
                
                # Per-question section feedback
                section_feedback = {
                    "pronunciation": {
                        "grade": int(pronunciation_score),
                        "issues": pronunciation_issues
                    },
                    "fluency": {
                        "grade": int(fluency_score),
                        "issues": fluency_issues
                    },
                    "grammar": {
                        "grade": 100 - min(100, len(grammar_issues) * 10),
                        "issues": grammar_issues
                    },
                    "lexical": {
                        "grade": lexical_grade,
                        "issues": lexical_issues
                    }
                }
                per_question_feedback.append({
                    "question_id": i + 1,
                    "audio_url": url,
                    "section_feedback": section_feedback,
                    "transcript": audio_transcript
                })
                
            except Exception as e:
                logger.error(f"Error processing {url}: {str(e)}")
            finally:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file: {str(e)}")
        
        # Validate the transcript (aggregate all transcripts)
        transcript = " ".join([q["transcript"] for q in per_question_feedback if q["transcript"]])
        sentences = re.split(r'[.!?]+', transcript)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentences_count = len(sentences)
        valid_transcript = sentences_count >= 2
        logger.info(f"Transcript validation: {sentences_count} sentences found, valid={valid_transcript}")
        
        # Calculate the final grade (average of per-question grades, or use your own logic)
        if per_question_feedback:
            final_grade = round(sum(q["section_feedback"]["pronunciation"]["grade"] * 0.7 + q["section_feedback"]["fluency"]["grade"] * 0.3 for q in per_question_feedback) / len(per_question_feedback))
        else:
            final_grade = 0
        
        # Store per-question feedback in section_feedback column
        try:
            update_result = supabase.table("submissions").update({
                "grade": final_grade,
                "valid_transcript": valid_transcript,
                "status": "graded",
                "section_feedback": per_question_feedback
            }).eq("id", submission_id).execute()
            logger.info(f"Updated submission {submission_id} with grade {final_grade} and feedback")
        except Exception as e:
            logger.error(f"Error updating submission in database: {str(e)}")
        
    except Exception as e:
        logger.error(f"Fatal error in process_submission: {str(e)}")

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Analyze audio files endpoint"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    if not request.submission_id:
        raise HTTPException(status_code=400, detail="No submission ID provided")
    
    # Start the background processing task
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
        "status": "healthyTESTTTTT",
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "supabase": supabase_status,
        "supabase_url": SUPABASE_URL
    }
    
    



@app.post("/test-grammar-lexical")
async def test_grammar_lexical(transcript: str):
    """
    Test endpoint to analyze grammar and lexical feedback for a given transcript
    
    Args:
        transcript: The text transcript to analyze
        
    Returns:
        Dict with grammar and lexical analysis results
    """
    try:
        logger.info(f"Testing grammar and lexical analysis with transcript of length: {len(transcript)}")
        
        if not transcript or len(transcript) < 10:
            return {
                "status": "error",
                "message": "Transcript is too short for analysis (minimum 10 characters)"
            }
        
        # Run the grammar analysis
        gram_result = await grammar.analyze_grammar(transcript)
        
        # Extract statistics
        grammar_count = len(gram_result["grammar_corrections"])
        vocab_count = len(gram_result["vocabulary_suggestions"])
        lexical_count = len(gram_result["lexical_resources"])
        
        # Create a summary of the analysis
        summary = {
            "status": "success",
            "transcript_length": len(transcript),
            "num_sentences": len(transcript.split('.')),
            "stats": {
                "grammar_issues_found": grammar_count,
                "vocabulary_suggestions_found": vocab_count,
                "lexical_resource_issues_found": lexical_count
            },
            "results": gram_result
        }
        
        logger.info(f"Analysis complete: {grammar_count} grammar issues, {vocab_count} vocabulary suggestions, {lexical_count} lexical issues")
        return summary
        
    except Exception as e:
        logger.error(f"Error in test_grammar_lexical: {str(e)}")
        return {
            "status": "error",
            "message": f"Error testing grammar and lexical analysis: {str(e)}"
        }
        
        
        
        
@app.post("/test-transcription-length")
async def test_transcription_length(url: str):
    """
    Test endpoint to diagnose potential truncation issues with long audio files
    
    Args:
        url: URL of the audio file to analyze
        
    Returns:
        Dict with detailed analysis of transcription process
    """
    try:
        logger.info(f"Testing transcription length with audio from URL: {url}")
        temp_file = None
        
        try:
            # Download the audio file
            temp_file = await download_audio(url)
            logger.info(f"Downloaded audio file to {temp_file}")
            
            # Get file size and duration using ffprobe
            file_info = {}
            try:
                import subprocess
                cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', 
                       '-of', 'json', temp_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    import json
                    probe_data = json.loads(result.stdout)
                    file_info = {
                        "file_size_bytes": int(probe_data.get("format", {}).get("size", 0)),
                        "duration_seconds": float(probe_data.get("format", {}).get("duration", 0))
                    }
                    logger.info(f"Audio file info: {file_info}")
            except Exception as e:
                logger.warning(f"Could not get audio file info: {str(e)}")
                file_info = {"error": str(e)}
            
            # Step 1: Only get AssemblyAI transcript
            if temp_file.lower().endswith('.webm'):
                temp_wav_file = await pronoun.convert_webm_to_wav(temp_file)
                file_to_process = temp_wav_file
            else:
                file_to_process = temp_file
                temp_wav_file = None
                
            try:
                upload_url = await pronoun.upload_to_assemblyai(file_to_process)
                assemblyai_result = await pronoun.get_assemblyai_transcript(upload_url)
                
                # Step 2: Get Azure pronunciation assessment with the AssemblyAI transcript
                transcript_text = assemblyai_result.get('text', '')
                
                azure_result = None
                if transcript_text:
                    azure_result = await pronoun.analyze_pronunciation(file_to_process, transcript_text)
                
                # Step 3: Compare the results
                return {
                    "status": "success",
                    "file_info": file_info,
                    "assemblyai": {
                        "transcript_text": transcript_text,
                        "transcript_word_count": len(transcript_text.split()) if transcript_text else 0,
                        "audio_duration_reported": assemblyai_result.get("audio_duration"),
                        "word_count_reported": len(assemblyai_result.get("words", [])),
                        "utterance_count": len(assemblyai_result.get("utterances", [])),
                        "confidence": assemblyai_result.get("confidence"),
                        "raw_result": assemblyai_result if assemblyai_result else {}
                    },
                    "azure": {
                        "transcript_used": azure_result.get("transcript") if azure_result else None,
                        "azure_transcript": azure_result.get("azure_transcript") if azure_result else None,
                        "word_count_processed": len(azure_result.get("word_details", [])) if azure_result else 0,
                        "audio_duration": azure_result.get("audio_duration") if azure_result else None,
                        "completeness_score": azure_result.get("completeness_score") if azure_result else None
                    }
                }
            finally:
                # Clean up temporary wav file if created
                if temp_wav_file and os.path.exists(temp_wav_file):
                    try:
                        os.unlink(temp_wav_file)
                    except Exception as e:
                        logger.warning(f"Failed to clean up temporary wav file {temp_wav_file}: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error processing audio from URL {url}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
            }
        
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except Exception as e:
                    logger.warning(f"Failed to delete temp file: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in test_transcription_length: {str(e)}")
        return {
            "status": "error",
            "message": f"Error testing transcription length: {str(e)}"
        }
        
        
        
        
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8082))
    uvicorn.run(app, host="0.0.0.0", port=8082)
    




