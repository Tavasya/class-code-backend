#!/usr/bin/env python3
"""
Simple script to view question tracking in a clean format
"""
import json
import sys
from datetime import datetime

def view_tracking():
    try:
        with open('/tmp/question_tracking.json', 'r') as f:
            data = json.load(f)
        
        print("=" * 60)
        print("QUESTION TRACKING SUMMARY")
        print("=" * 60)
        
        if 'start_time' in data:
            print(f"Session started: {data['start_time']}")
            print()
        
        for submission_url, submission_data in data.get('sessions', {}).items():
            print(f"📋 SUBMISSION: {submission_url}")
            print("-" * 50)
            
            questions = submission_data.get('questions', {})
            question_numbers = sorted([int(q) for q in questions.keys()])
            
            print(f"Questions found: {question_numbers}")
            print(f"Total questions: {len(question_numbers)}")
            print()
            
            # Summary table
            print("QUESTION STATUS SUMMARY:")
            print("Q#  | Events")
            print("----|----------------------------------------")
            
            for q_num in range(1, 11):  # Assuming 10 questions
                q_key = str(q_num)
                if q_key in questions:
                    events = [event['event'] for event in questions[q_key]['events']]
                    events_str = " → ".join(events)
                    status = "✅" if "QUESTION_COMPLETED" in events else "❌"
                    print(f"Q{q_num:2d} | {status} {events_str}")
                else:
                    print(f"Q{q_num:2d} | ❌ NO EVENTS")
            
            print()
            print("DETAILED EVENTS:")
            print("-" * 30)
            
            for q_num in question_numbers:
                q_key = str(q_num)
                print(f"\n🔹 QUESTION {q_num}:")
                
                for event in questions[q_key]['events']:
                    time = event['timestamp'].split('T')[1][:8]  # Just time part
                    event_name = event['event']
                    data = event.get('data', {})
                    
                    print(f"  {time} | {event_name}")
                    if data and event_name in ['ANALYSIS_READY', 'PROCESSING_START', 'QUESTION_COMPLETED']:
                        if 'completed_count' in data:
                            print(f"           └─ Progress: {data['completed_count']}/{data.get('total_questions', '?')}")
                        elif 'transcript_length' in data:
                            print(f"           └─ Transcript: {data['transcript_length']} chars")
                    elif event_name == 'COMPLETION_CHECK' and data:
                        # Show which analyses are missing
                        missing = [k for k, v in data.items() if not v]
                        if missing:
                            print(f"           └─ Missing: {', '.join(missing)}")
                        else:
                            print(f"           └─ All complete!")
            
            print("\n" + "=" * 60)
    
    except FileNotFoundError:
        print("❌ No tracking file found at /tmp/question_tracking.json")
        print("Run a submission first to generate tracking data.")
    except Exception as e:
        print(f"❌ Error reading tracking file: {e}")

if __name__ == "__main__":
    view_tracking()