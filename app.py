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
import asyncio
import re

# Import our modules
import pronoun
import grammar
import fluency

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
SUPABASE_URL = os.environ.get("SUPABASE_URL","https://zyaobehxpcwxlyljzknw.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YW9iZWh4cGN3eGx5bGp6a253Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyMzQ1NjcsImV4cCI6MjA1NzgxMDU2N30.mUc1rpE_zecu3XLI8x_jH_QckrNNkLEnqOGp2SQOSdo")

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

# Create a lock for processing submissions
# Using a global semaphore with a value of 1 effectively creates a "lock"
processing_lock = asyncio.Semaphore(1)

# Queue for tracking pending submissions
submission_queue = asyncio.Queue()

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
                file_options={"content-type": "application/json", "upsert": "true"},
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

# The main submission processing function
async def process_submission(urls: List[str], submission_id: str):
    """Process a single submission"""
    # Acquire the lock to ensure only one submission is processed at a time
    async with processing_lock:
        logger.info(f"Starting analysis for submission {submission_id}")
        
        # Ensure submission_id is clean and suitable for a filename
        clean_submission_id = "".join(c for c in submission_id if c.isalnum() or c in "-_").strip()
        if not clean_submission_id:
            clean_submission_id = f"submission_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add a global sentence counter
        sentence_idx = 1
        
        results = {
            "submission_id": submission_id,  # Keep original ID in the data
            "timestamp": datetime.now().isoformat(),
            "status": "processing",
            "file_count": len(urls),
            "pronunciation_analysis": [],
            "grammar_analysis": {},
            "vocabulary_suggestions": {},
            "lexical_resources": {},
            "fluency_coherence_analysis": {}  # New section for fluency/coherence
        }
        
        try:
            # Upload initial processing status
            await upload_to_supabase(results, f"{clean_submission_id}_status")
            
            for i, url in enumerate(urls):
                logger.info(f"Processing URL {i+1}/{len(urls)}: {url}")
                temp_file = None
                
                try:
                    temp_file = await download_audio(url)
                    
                    # 1. Pronunciation analysis (existing)
                    pronun_result = await pronoun.analyze_audio_file(temp_file)
                    
                    # ---------- NORMALISE PRONUNCIATION SHAPE ----------
                    pronun_result.setdefault(
                        "overall_pronunciation_score",
                        round(sum(w["accuracy_score"] for w in pronun_result.get("word_details", [])) /
                              max(len(pronun_result.get("word_details", [])), 1))
                    )
                    pronun_result.setdefault("accuracy_score",    pronun_result["overall_pronunciation_score"])
                    pronun_result.setdefault("fluency_score",     0)
                    pronun_result.setdefault("prosody_score",     0)
                    pronun_result.setdefault("completeness_score",0)
                    pronun_result.setdefault("critical_errors",   [])
                    pronun_result.setdefault("filler_words",      [])
                    # ---------------------------------------------------
                    
                    pronun_result["url"] = url
                    results["pronunciation_analysis"].append(pronun_result)
                    
                    transcript = pronun_result.get("transcript", "")
                    if transcript:
                        # 2. Grammar analysis (existing)
                        gram_result = await grammar.analyze_grammar(transcript)
                        
                        # Add a local sentence counter for this recording
                        local_sent_idx = 1
                        
                        # ----- 1️⃣ GRAMMAR -------------------------------------------------
                        for sent_key, sent in gram_result["grammar_corrections"].items():
                            results["grammar_analysis"][f"recording_{i+1}_sentence_{local_sent_idx}"] = {
                                "original": sent.get("original", sent.get("sentence", "")),
                                "corrections": sent.get("corrections", [])
                            }
                            local_sent_idx += 1
                            sentence_idx += 1  # Keep global counter for backward compatibility
                        
                        # Reset local counter for vocabulary
                        local_sent_idx = 1
                        
                        # ----- 2️⃣ VOCABULARY ----------------------------------------------
                        for sent_key, sent in gram_result["vocabulary_suggestions"].items():
                            results["vocabulary_suggestions"][f"recording_{i+1}_sentence_{local_sent_idx}"] = {
                                "original": sent.get("original", sent.get("sentence", "")),
                                "suggestions": sent.get("suggestions", [])
                            }
                            local_sent_idx += 1
                            sentence_idx += 1  # Keep global counter for backward compatibility
                        
                        # Reset local counter for lexical
                        local_sent_idx = 1
                        
                        # ----- 3️⃣ LEXICAL -------------------------------------------------
                        for sent_key, sent in gram_result["lexical_resources"].items():
                            results["lexical_resources"][f"recording_{i+1}_sentence_{local_sent_idx}"] = {
                                "original": sent.get("original", sent.get("sentence", "")),
                                "suggestions": sent.get("suggestions", [])
                            }
                            local_sent_idx += 1
                            sentence_idx += 1  # Keep global counter for backward compatibility
                    
                        # 3. NEW: Fluency and coherence analysis
                        # Get word details from pronunciation analysis if available
                        word_details = pronun_result.get("word_details", [])
                        
                        # Run fluency and coherence analysis
                        fluency_result = await fluency.analyze_fluency_coherence(transcript, word_details)
                        
                        results["fluency_coherence_analysis"][f"recording_{i+1}"] = {
                            "fluency_metrics":           fluency_result.get("fluency_metrics",   {}),
                            "coherence_metrics":         fluency_result.get("coherence_metrics", {}),
                            "key_findings":              fluency_result.get("key_findings",      []),
                            "improvement_suggestions":   fluency_result.get("improvement_suggestions", [])
                        }
                    
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
                
                # Calculate and update grade for this specific assignment
                try:
                    # Extract scores from analysis
                    pronunciation_score = 0
                    fluency_score = 0
                    
                    # Get pronunciation score
                    for analysis in results.get("pronunciation_analysis", []):
                        if "overall_pronunciation_score" in analysis:
                            pronunciation_score = analysis["overall_pronunciation_score"]
                            logger.info(f"Found pronunciation score: {pronunciation_score}")
                            break
                    
                    # Get fluency score
                    fluency_data = results.get("fluency_coherence_analysis", {})
                    if fluency_data:
                        first_key = next(iter(fluency_data))
                        fluency_metrics = fluency_data[first_key].get("fluency_metrics", {})
                        fluency_score = fluency_metrics.get("overall_fluency_score", 0)
                        logger.info(f"Found fluency score: {fluency_score}")
                    
                    # Calculate weighted score (70% pronunciation, 30% fluency)
                    assignment_score = (pronunciation_score * 0.7) + (fluency_score * 0.3)
                    final_grade = round(assignment_score)
                    
                    logger.info(f"Calculated grade for submission {submission_id}: {final_grade}")
                    
                    # Find the submission in the database
                    submission_data = supabase.table("submissions").select("*").eq("submission_uid", submission_id).execute()
                    
                    if submission_data.data and len(submission_data.data) > 0:
                        submission = submission_data.data[0]
                        
                        # Check if transcript has at least 2 sentences
                        transcript = ""
                        for analysis in results.get("pronunciation_analysis", []):
                            if "transcript" in analysis:
                                transcript += analysis["transcript"] + " "
                        # Split by .,?,!
                        sentences = re.split(r'[.!?]+', transcript)
                        # Filter empty sentences
                        sentences = [s.strip() for s in sentences if s.strip()]
                        sentences_count = len(sentences)
                        valid_transcript = sentences_count >= 2
                        
                        logger.info(f"Transcript validation: {sentences_count} sentences found, valid_transcript={valid_transcript}")
                        
                        # Update the grade for this specific submission
                        update_result = supabase.table("submissions").update({
                            "grade": final_grade,
                            "valid_transcript": valid_transcript
                        }).eq("submission_uid", submission_id).execute()
                        
                        logger.info(f"Updated grade for submission {submission_id} to {final_grade}")
                        
                        # Also update the overall grade for the student in this class
                        assignment_id = submission["assignment_id"]
                        student_id = submission["student_id"]
                        
                        # Find the class ID for this assignment
                        assignment_data = supabase.table("assignments").select("course_id").eq("id", assignment_id).execute()
                        
                        if assignment_data.data and len(assignment_data.data) > 0:
                            class_id = assignment_data.data[0]["course_id"]
                            
                            # Update the student's overall class grade
                            await update_class_grade_for_student(student_id, class_id)
                            logger.info(f"Successfully updated overall grade for student {student_id} in class {class_id}")
                        else:
                            logger.warning(f"Could not find class for assignment {assignment_id}")
                    else:
                        logger.warning(f"Could not find submission record for {submission_id}")
                except Exception as e:
                    logger.error(f"Error updating grade after analysis: {str(e)}")
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
        
        finally:
            # Process the next item in the queue if there is one
            if not submission_queue.empty():
                try:
                    next_submission = await submission_queue.get()
                    asyncio.create_task(process_submission(next_submission["urls"], next_submission["submission_id"]))
                except Exception as e:
                    logger.error(f"Error starting next submission: {str(e)}")

# Function to manage the submission queue
async def queue_submission(urls: List[str], submission_id: str):
    """Add submission to queue and start processing if no active processing"""
    # Add to queue
    await submission_queue.put({"urls": urls, "submission_id": submission_id})
    
    # If the lock is available, start processing
    if processing_lock.locked():
        logger.info(f"Submission {submission_id} added to queue. Current queue size: {submission_queue.qsize()}")
    else:
        # Start processing the first item in the queue
        next_submission = await submission_queue.get()
        asyncio.create_task(process_submission(next_submission["urls"], next_submission["submission_id"]))

async def update_class_grade_for_student(student_id, class_id):
    try:
        logger.info(f"Starting grade calculation for student {student_id} in class {class_id}")
        
        # Get all assignments for this class
        assignments_data = supabase.table("assignments").select("id").eq("course_id", class_id).execute()
        assignment_ids = [a["id"] for a in assignments_data.data]
        
        if not assignment_ids:
            logger.info(f"No assignments found for class {class_id}")
            return None
        
        # Get all submissions for this student in these assignments
        # Modified query to properly handle NULL values
        submissions_data = supabase.table("submissions") \
            .select("grade") \
            .eq("student_id", student_id) \
            .in_("assignment_id", assignment_ids) \
            .not_.is_("grade", "null") \
            .execute()
            
        # Calculate average from the grades
        grades = [s["grade"] for s in submissions_data.data if s["grade"] is not None]
        
        if grades:
            average_grade = round(sum(grades) / len(grades))
            logger.info(f"Calculated average grade: {average_grade} from {len(grades)} submissions")
            
            # Update the overall grade in students_classes
            result = supabase.table("students_classes").update({
                "overall_grade": average_grade
            }).eq("student_id", student_id).eq("class_id", class_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated grade to {average_grade}")
            else:
                logger.warning("No rows updated in students_classes table")
                
            return {
                "percentage": average_grade,
                "completedAssignments": len(grades),
                "totalAssignments": len(assignment_ids)
            }
        else:
            logger.info("No graded submissions found")
            # No submissions to grade - update to NULL using proper SQL syntax
            result = supabase.table("students_classes") \
                .update({"overall_grade": None}) \
                .eq("student_id", student_id) \
                .eq("class_id", class_id) \
                .execute()
            
            if result.data:
                logger.info("Successfully cleared grade (set to NULL)")
            else:
                logger.warning("No rows updated in students_classes table")
                
            return {
                "percentage": None,
                "completedAssignments": 0,
                "totalAssignments": len(assignment_ids)
            }
    
    except Exception as e:
        logger.error(f"Error updating class grade: {str(e)}")
        return None

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
    
    # Add task to queue instead of directly adding to background_tasks
    background_tasks.add_task(queue_submission, request.urls, request.submission_id)
    
    return {
        "status": "processing",
        "message": f"Analysis queued for {len(request.urls)} audio files",
        "submission_id": request.submission_id
    }

@app.get("/queue-status")
async def queue_status():
    """Get status of the processing queue"""
    return {
        "status": "success",
        "queue_size": submission_queue.qsize(),
        "is_processing": processing_lock.locked()
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    supabase_status = "connected" if supabase else "not connected"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "supabase": supabase_status,
        "queue_size": submission_queue.qsize(),
        "active_processing": processing_lock.locked()
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

@app.get("/test-fluency")
async def test_fluency():
    """Test fluency module functionality"""
    try:
        test_transcript = "This is a test transcript to check if the fluency module is working properly."
        result = await fluency.analyze_fluency_coherence(test_transcript)
        return {
            "status": "success",
            "message": "Fluency module is working correctly",
            "test_result": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error testing fluency module: {str(e)}"
        }

@app.get("/student-performance/{class_id}")
async def student_performance(class_id: str):
    try:
        # Get class enrollments with grades - already correct, using execute()
        enrollments = supabase.table("students_classes").select("student_id,overall_grade").eq("class_id", class_id).execute()
        
        # Get assignments for this class - add execute()
        assignments = supabase.table("assignments").select("id").eq("course_id", class_id).execute()
        assignment_ids = [a["id"] for a in assignments.data]
        
        # Get student data - add execute()
        student_ids = [e["student_id"] for e in enrollments.data]
        users = supabase.table("users").select("id,name").in_("id", student_ids).execute()
        
        # Get all submissions for these assignments - add execute()
        submissions = supabase.table("submissions").select("student_id,assignment_id,status").in_("assignment_id", assignment_ids).execute()
        
        # Build the result
        result = []
        for user in users.data:
            # Find enrollment for this student
            enrollment = next((e for e in enrollments.data if e["student_id"] == user["id"]), None)
            
            if enrollment:
                # Get completion stats
                student_submissions = [s for s in submissions.data if s["student_id"] == user["id"]]
                completed = sum(1 for s in student_submissions if s["status"] == "submitted")
                
                # Use stored grade or calculate if needed
                grade = enrollment.get("overall_grade")
                if grade is None and completed > 0:
                    # No stored grade but has submissions - calculate it now
                    performance = await update_class_grade_for_student(user["id"], class_id)
                    if performance:
                        grade = performance["percentage"]
                        completed = performance["completedAssignments"]
                
                result.append({
                    "id": user["id"],
                    "name": user["name"],
                    "percentage": grade,  # This can be null now if no submissions
                    "completedAssignments": completed,
                    "totalAssignments": len(assignment_ids)
                })
        
        return result
    except Exception as e:
        logger.error(f"Error in student_performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test-update-grade/{class_id}/{student_id}/{grade}")
async def test_update_grade(class_id: str, student_id: str, grade: float):
    try:
        # The issue is here - we need to execute() first, then get the result
        # The execute() returns the APIResponse which is not awaitable
        result = supabase.table("students_classes").update({
            "overall_grade": float(grade)
        }).eq("student_id", student_id).eq("class_id", class_id).execute()
        
        # Check if the record was found and updated
        if result.data:
            return {
                "status": "success",
                "message": f"Updated grade for student {student_id} in class {class_id} to {grade}",
                "data": result.data
            }
        else:
            return {
                "status": "error",
                "message": "No matching record found for the given student and class"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error updating grade: {str(e)}"
        }

@app.get("/test-grading")
async def test_grading(
    pronunciation_score: float = 80.0,
    fluency_score: float = 70.0,
    total_assignments: int = 5,
    completed_assignments: int = 3
):
    """
    Test the grading algorithm with custom values
    
    Args:
        pronunciation_score: Simulated pronunciation score (0-100)
        fluency_score: Simulated fluency score (0-100)
        total_assignments: Total number of assignments in the class
        completed_assignments: Number of completed assignments by the student
    
    Returns:
        Dict with calculated grade and assignment statistics
    """
    try:
        # Calculate weighted score (70% pronunciation, 30% fluency)
        submission_score = (pronunciation_score * 0.7) + (fluency_score * 0.3)
        
        # Round to nearest integer
        final_grade = round(submission_score)
        
        return {
            "status": "success",
            "inputs": {
                "pronunciation_score": pronunciation_score,
                "fluency_score": fluency_score,
                "total_assignments": total_assignments,
                "completed_assignments": completed_assignments
            },
            "calculation": {
                "weighted_score": f"({pronunciation_score} × 0.7) + ({fluency_score} × 0.3) = {submission_score}"
            },
            "result": {
                "final_grade": final_grade,
                "percentage": final_grade,
                "completedAssignments": completed_assignments,
                "totalAssignments": total_assignments,
                "completion_rate": f"{(completed_assignments / total_assignments) * 100:.1f}%"
            }
        }
    except Exception as e:
        logger.error(f"Error in test_grading: {str(e)}")
        return {
            "status": "error",
            "message": f"Error testing grading algorithm: {str(e)}"
        }

@app.get("/test-update-submission-grade/{submission_uid}/{grade}")
async def test_update_submission_grade(submission_uid: str, grade: float):
    """
    Test endpoint to directly update a submission's grade
    
    Args:
        submission_uid: The unique ID of the submission
        grade: The grade value to set (0-100)
    
    Returns:
        Result of the update operation
    """
    try:
        logger.info(f"Attempting to update submission {submission_uid} with grade {grade}")
        
        # Validate the grade is within range
        if not (0 <= float(grade) <= 100):
            return {
                "status": "error",
                "message": "Grade must be between 0 and 100"
            }
        
        # Execute the update
        update_result = supabase.table("submissions").update({
            "grade": float(grade),
        }).eq("submission_uid", submission_uid).execute()
        
        # Log detailed information about the update
        logger.info(f"Update result data: {update_result.data}")
        logger.info(f"Update result count: {len(update_result.data) if update_result.data else 0}")
        
        # Check if the update was successful
        if update_result.data and len(update_result.data) > 0:
            # Also update the student's overall class grade
            try:
                submission_data = update_result.data[0]
                student_id = submission_data.get("student_id")
                assignment_id = submission_data.get("assignment_id")
                
                # Get the class ID
                assignment_result = supabase.table("assignments").select("course_id").eq("id", assignment_id).execute()
                
                if assignment_result.data and len(assignment_result.data) > 0:
                    class_id = assignment_result.data[0]["course_id"]
                    # Update overall grade
                    await update_class_grade_for_student(student_id, class_id)
                    logger.info(f"Updated overall grade for student {student_id} in class {class_id}")
            except Exception as e:
                logger.error(f"Error updating overall grade: {str(e)}")
            
            return {
                "status": "success",
                "message": f"Successfully updated grade for submission {submission_uid} to {grade}",
                "data": update_result.data[0]
            }
        else:
            return {
                "status": "error",
                "message": f"Update operation completed but no rows affected. Submission {submission_uid} may not exist."
            }
            
    except Exception as e:
        logger.error(f"Error in test_update_submission_grade: {str(e)}")
        return {
            "status": "error",
            "message": f"Error updating submission grade: {str(e)}"
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

# Start background task to process the queue on app startup
@app.on_event("startup")
async def start_queue_processor():
    """Start background task to process the queue"""
    logger.info("Starting queue processor")
    
    # This function doesn't do anything on startup,
    # but it's here to show that we can add startup tasks if needed in the future
    pass
        
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=port)