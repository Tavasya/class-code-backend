# Pronunciation Duration Feedback Plan

## Objective
For each submission, compare the actual speaking duration (from pronunciation analysis) to the expected time limit (from the assignment's questions). Use this ratio to generate feedback about whether the user spoke enough, too little, or too much.

---

## Steps

### 1. Retrieve Assignment ID from Submission
- Given a `submission_id`, query the `submissions` table to get the corresponding `assignment_id`.

### 2. Retrieve Questions from Assignment
- Use the `assignment_id` to query the `assignments` table.
- Get the `questions` column (JSON array) for that assignment.

### 3. Parse Time Limits
- Parse the `questions` JSON to extract each question's `timeLimit` (in minutes).

### 4. Get Actual Durations
- From the pronunciation service, get the actual duration spoken for each question (already available as `audio_duration` or per-question duration).

### 5. Calculate Ratio
- For each question, calculate:  
  `ratio = (actual_duration_in_seconds / (timeLimit * 60)) * 100`
- Interpret the ratio:
  - **< 50%**: "Did not speak that much."
  - **50% - 100%**: "User spoke longer."
  - **> 100%**: "User exceeded the time limit."

### 6. Generate Feedback
- For each question, generate a feedback message based on the ratio.

---

## Example Feedback Logic (Python Pseudocode)

```python
for i, question in enumerate(questions):
    time_limit_sec = int(question['timeLimit']) * 60
    actual_duration = durations[i]  # from pronunciation analysis
    ratio = (actual_duration / time_limit_sec) * 100

    if ratio < 50:
        feedback = "Did not speak that much."
    elif ratio <= 100:
        feedback = "User spoke longer."
    else:
        feedback = "User exceeded the time limit."
    print(f"Q{i+1}: {feedback} ({ratio:.1f}%)")
```

---

## Database Tables Used
- **submissions**: `id`, `assignment_id`
- **assignments**: `id`, `questions` (JSON)

---

## Next Steps
- Implement a function/service that, given a `submission_id`, performs the above steps and returns feedback for each question.
- Optionally, store this feedback in the database or return it as part of the API response.

---

## Implementation Sketch: Aggregation Step for Duration/TimeLimit Feedback

Below is a high-level sketch of how to implement the duration/timeLimit feedback logic in the aggregation step (e.g., in `AnalysisWebhook` after all question analyses are complete):

### 1. Fetch Assignment and Questions
- Use `submission_url` to look up the submission in the `submissions` table and get the `assignment_id`.
- Use `assignment_id` to look up the assignment in the `assignments` table and get the `questions` JSON.

### 2. Gather Actual Durations
- Collect the actual spoken durations for each question from the pronunciation analysis results (already aggregated per question).

### 3. Compare and Generate Feedback
- For each question:
    - Extract the `timeLimit` from the questions JSON (convert to seconds).
    - Get the actual duration from the analysis results.
    - Calculate the ratio: `(actual_duration / (timeLimit * 60)) * 100`.
    - Generate feedback based on the ratio:
        - `< 50%`: "Did not speak that much."
        - `50% - 100%`: "User spoke longer."
        - `> 100%`: "User exceeded the time limit."
    - Store this feedback in the results for that question.

### 4. Store or Return Feedback
- Add the feedback to the `section_feedback` or results structure that is saved to the database or returned by the API.

---

### Example Python-like Pseudocode

```python
# 1. Fetch assignment_id and questions
submission = db.get_submission(submission_url)  # returns dict with assignment_id
assignment = db.get_assignment(submission['assignment_id'])  # returns dict with questions JSON
questions = json.loads(assignment['questions'])

# 2. Gather actual durations (already in question_results)
# question_results: {question_number: { ... 'audio_duration': ... }}

feedback_per_question = []
for i, question in enumerate(questions):
    time_limit_sec = int(question['timeLimit']) * 60
    actual_duration = question_results[str(i+1)]['audio_duration']  # or similar key
    ratio = (actual_duration / time_limit_sec) * 100
    if ratio < 50:
        feedback = "Did not speak that much."
    elif ratio <= 100:
        feedback = "User spoke longer."
    else:
        feedback = "User exceeded the time limit."
    feedback_per_question.append({
        'question_number': i+1,
        'feedback': feedback,
        'ratio': ratio,
        'actual_duration': actual_duration,
        'time_limit_sec': time_limit_sec
    })

# 4. Store or return feedback
# Add feedback_per_question to section_feedback or results dict
results['duration_feedback'] = feedback_per_question
# Save results to database or return in API response
```

---

**This logic should be placed in the aggregation step, after all per-question analyses are complete and before saving the final results.**

**You can tweak the ratio thresholds or feedback messages as needed. Let me know if you want to adjust the logic or add more details!** 