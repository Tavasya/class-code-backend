import asyncio
import aiohttp
import time
import uuid
import json
from datetime import datetime
import random
from typing import Dict, Any, List

# Configuration
BASE_URL = "https://classconnect-staging-107872842385.us-west2.run.app"  # Production Cloud Run service URL
ANALYZE_ENDPOINT = "/analyze"
TEST_AUDIO_URL = "https://zyaobehxpcwxlyljzknw.supabase.co/storage/v1/object/public/audio_recordings/1f65f05e-7796-4a0a-bdae-c5b518849da6/177/1_1745594975092.webm"  # Replace with a test audio URL
TOTAL_REQUESTS = 20
MAX_CONCURRENT_REQUESTS = 5  # Adjust based on your needs

# Supabase check configuration
SUPABASE_URL = "https://zyaobehxpcwxlyljzknw.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5YW9iZWh4cGN3eGx5bGp6a253Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyMzQ1NjcsImV4cCI6MjA1NzgxMDU2N30.mUc1rpE_zecu3XLI8x_jH_QckrNNkLEnqOGp2SQOSdo"  # Replace with your Supabase anon key
CHECK_INTERVAL = 30  # Check every 30 seconds
MAX_CHECK_TIME = 100000  # Give up after 10 minutes (600 seconds)

async def send_analyze_request(session, request_id):
    """Send a request to the analyze endpoint and track the result"""
    start_time = time.time()
    submission_id = f"test-{uuid.uuid4()}"
    
    try:
        async with session.post(
            f"{BASE_URL}{ANALYZE_ENDPOINT}",
            json={"urls": [TEST_AUDIO_URL], "submission_id": submission_id},
            timeout=90  # Increased to 90 seconds for initial response
        ) as response:
            status = response.status
            try:
                result = await response.json()
            except:
                result = await response.text()
            
            initial_response_time = time.time() - start_time
            
            return {
                "request_id": request_id,
                "submission_id": submission_id,
                "initial_status_code": status,
                "initial_response_time": initial_response_time,
                "initial_success": 200 <= status < 300,
                "initial_result": result,
                "complete": False,  # Will be updated when processing finishes
                "processing_time": None,  # Will be updated when processing finishes
                "final_result": None  # Will be updated when processing finishes
            }
    except asyncio.TimeoutError:
        return {
            "request_id": request_id,
            "submission_id": submission_id,
            "initial_status_code": None,
            "initial_response_time": time.time() - start_time,
            "initial_success": False,
            "initial_result": "Request timed out",
            "complete": False,
            "processing_time": None,
            "final_result": None
        }
    except Exception as e:
        return {
            "request_id": request_id,
            "submission_id": submission_id,
            "initial_status_code": None,
            "initial_response_time": time.time() - start_time,
            "initial_success": False,
            "initial_result": str(e),
            "complete": False,
            "processing_time": None,
            "final_result": None
        }

async def check_processing_status(session, results):
    """
    Periodically check Supabase for the status of submissions.
    Updates the results list in-place as submissions complete.
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    start_time = time.time()
    all_complete = False
    check_count = 0
    
    # Keep checking until all are complete or we exceed the maximum time
    while not all_complete and (time.time() - start_time) < MAX_CHECK_TIME:
        check_count += 1
        print(f"\nStatus check #{check_count} - {datetime.now().strftime('%H:%M:%S')}")
        
        # Get list of submission IDs that are not yet complete
        pending_submissions = [r for r in results if not r["complete"]]
        if not pending_submissions:
            all_complete = True
            break
            
        completed_this_round = 0
        
        # Check status for each incomplete submission
        for result in pending_submissions:
            submission_id = result["submission_id"]
            
            try:
                # Query Supabase to check if analysis is complete
                # Check in the storage bucket instead of REST API
                async with session.get(
                    f"{SUPABASE_URL}/storage/v1/object/public/analysis-results/{submission_id}.json",
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data:
                            # Found a result - mark as complete
                            result["complete"] = True
                            result["processing_time"] = time.time() - result["initial_response_time"] - start_time
                            result["final_result"] = "success"
                            completed_this_round += 1
            except Exception as e:
                print(f"Error checking status for {submission_id}: {str(e)}")
        
        # Print progress
        pending_count = len([r for r in results if not r["complete"]])
        complete_count = len(results) - pending_count
        print(f"Completed: {complete_count}/{len(results)} ({complete_count/len(results)*100:.1f}%)")
        print(f"Completed this round: {completed_this_round}")
        print(f"Still pending: {pending_count}")
        
        if pending_count == 0:
            all_complete = True
            break
            
        # Wait before next check
        if not all_complete:
            await asyncio.sleep(CHECK_INTERVAL)
    
    # Mark any remaining submissions as timed out
    for result in results:
        if not result["complete"]:
            result["final_result"] = "processing_timeout"
            
    return check_count

async def main():
    """Run the load test against the analyze endpoint"""
    print(f"Starting load test: {TOTAL_REQUESTS} requests to {BASE_URL}{ANALYZE_ENDPOINT}")
    print(f"Using test audio URL: {TEST_AUDIO_URL}")
    print(f"Maximum concurrent requests: {MAX_CONCURRENT_REQUESTS}")
    print(f"Will check processing status every {CHECK_INTERVAL} seconds")
    print(f"Maximum wait time for processing: {MAX_CHECK_TIME} seconds ({MAX_CHECK_TIME/60} minutes)")
    print("-" * 80)
    
    start_time = time.time()
    
    # Store all results
    results = []
    
    # Create client session with increased connection limits and timeout
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    timeout = aiohttp.ClientTimeout(total=180)  # 3-minute timeout for initial request
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Create all the tasks
        tasks = [send_analyze_request(session, i+1) for i in range(TOTAL_REQUESTS)]
        
        # Process in batches for better control
        for i in range(0, len(tasks), MAX_CONCURRENT_REQUESTS):
            batch = tasks[i:i+MAX_CONCURRENT_REQUESTS]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            
            # Print progress
            completed = i + len(batch)
            print(f"Sent {completed}/{TOTAL_REQUESTS} requests ({completed/TOTAL_REQUESTS*100:.1f}%)")
            
            # Small delay between batches to avoid overwhelming the server
            if i + MAX_CONCURRENT_REQUESTS < TOTAL_REQUESTS:
                await asyncio.sleep(1)
        
        # All requests sent, now monitor for completion
        print("\nAll requests sent. Monitoring processing status...")
        check_count = await check_processing_status(session, results)
    
    # Calculate summary statistics
    total_duration = time.time() - start_time
    initial_success = sum(1 for r in results if r["initial_success"])
    complete_success = sum(1 for r in results if r["complete"] and r["final_result"] == "success")
    
    # Calculate response time statistics for initial responses
    initial_durations = [r["initial_response_time"] for r in results if r["initial_success"]]
    if initial_durations:
        avg_initial = sum(initial_durations) / len(initial_durations)
        min_initial = min(initial_durations)
        max_initial = max(initial_durations)
    else:
        avg_initial = min_initial = max_initial = 0
    
    # Calculate processing time statistics
    processing_times = [r["processing_time"] for r in results if r["complete"] and r["processing_time"] is not None]
    if processing_times:
        avg_processing = sum(processing_times) / len(processing_times)
        min_processing = min(processing_times)
        max_processing = max(processing_times)
    else:
        avg_processing = min_processing = max_processing = 0
    
    # Print the summary
    print("\n" + "=" * 80)
    print(f"LOAD TEST SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print(f"Total requests:               {TOTAL_REQUESTS}")
    print(f"Initial success:              {initial_success} ({initial_success/TOTAL_REQUESTS*100:.1f}%)")
    print(f"Complete processing success:  {complete_success} ({complete_success/TOTAL_REQUESTS*100:.1f}%)")
    print(f"Status checks performed:      {check_count}")
    print(f"Total test duration:          {total_duration:.2f} seconds ({total_duration/60:.1f} minutes)")
    
    print("\nInitial Response Time Statistics:")
    if initial_durations:
        print(f"  Average:                   {avg_initial:.2f} seconds")
        print(f"  Minimum:                   {min_initial:.2f} seconds")
        print(f"  Maximum:                   {max_initial:.2f} seconds")
    else:
        print("  No successful initial responses")
    
    print("\nProcessing Time Statistics:")
    if processing_times:
        print(f"  Average:                   {avg_processing:.2f} seconds ({avg_processing/60:.1f} minutes)")
        print(f"  Minimum:                   {min_processing:.2f} seconds ({min_processing/60:.1f} minutes)")
        print(f"  Maximum:                   {max_processing:.2f} seconds ({max_processing/60:.1f} minutes)")
    else:
        print("  No successfully completed processing")
    
    # Count failure types
    initial_failures = sum(1 for r in results if not r["initial_success"])
    processing_failures = sum(1 for r in results if r["initial_success"] and not r["complete"])
    processing_timeouts = sum(1 for r in results if r["initial_success"] and not r["complete"])
    
    if initial_failures > 0 or processing_failures > 0:
        print("\nFailure Analysis:")
        if initial_failures > 0:
            print(f"  Initial request failures:   {initial_failures} ({initial_failures/TOTAL_REQUESTS*100:.1f}%)")
        if processing_failures > 0:
            print(f"  Processing failures:        {processing_failures} ({processing_failures/TOTAL_REQUESTS*100:.1f}%)")
            print(f"  Processing timeouts:        {processing_timeouts} ({processing_timeouts/TOTAL_REQUESTS*100:.1f}%)")
    
    # Save detailed results to file
    filename = f"load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump({
            "config": {
                "total_requests": TOTAL_REQUESTS,
                "max_concurrent": MAX_CONCURRENT_REQUESTS,
                "base_url": BASE_URL,
                "test_audio_url": TEST_AUDIO_URL,
                "check_interval": CHECK_INTERVAL,
                "max_check_time": MAX_CHECK_TIME
            },
            "summary": {
                "total_duration": total_duration,
                "initial_success": initial_success,
                "complete_success": complete_success,
                "initial_success_rate": initial_success / TOTAL_REQUESTS * 100,
                "complete_success_rate": complete_success / TOTAL_REQUESTS * 100,
                "avg_initial_response": avg_initial,
                "avg_processing_time": avg_processing,
                "status_checks_performed": check_count
            },
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to {filename}")

if __name__ == "__main__":
    asyncio.run(main())