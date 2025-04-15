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
                pronun_result["url"] = url
                results["pronunciation_analysis"].append(pronun_result)
                
                transcript = pronun_result.get("transcript", "")
                if transcript:
                    # 2. Grammar analysis (existing)
                    gram_result = await grammar.analyze_grammar(transcript)
                    results["grammar_analysis"].update(gram_result["grammar_corrections"])
                    results["vocabulary_suggestions"].update(gram_result["vocabulary_suggestions"])
                    results["lexical_resources"].update(gram_result["lexical_resources"])
                    # 3. NEW: Fluency and coherence analysis
                    # Get word details from pronunciation analysis if available
                    word_details = pronun_result.get("word_details", [])
                    
                    # Import the new fluency module
                    import fluency
                    
                    # Run fluency and coherence analysis
                    fluency_result = await fluency.analyze_fluency_coherence(transcript, word_details)
                    
                    # Add a unique identifier key based on URL or index
                    fluency_key = f"recording_{i+1}"
                    results["fluency_coherence_analysis"][fluency_key] = fluency_result
                
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
                    
                    # Update the grade for this specific submission
                    update_result = supabase.table("submissions").update({
                        "grade": final_grade,
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
        submissions_data = supabase.table("submissions")\
            .select("grade")\
            .eq("student_id", student_id)\
            .in_("assignment_id", assignment_ids)\
            .not_.is_("grade", "null")\
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
            # No submissions to grade - update to NULL
            result = supabase.table("students_classes").update({
                "overall_grade": None
            }).eq("student_id", student_id).eq("class_id", class_id).execute()
            
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
        
        
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    uvicorn.run(app, host="0.0.0.0", port=8081)
    




