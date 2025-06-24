# Grammar API Model Evaluation

This folder contains tools to evaluate the performance of your grammar analysis API using automated testing and AI-powered assessment.

## Files

- `grammar_evaluation.py` - Main evaluation class with API testing and GPT-4 assessment
- `test_transcripts.json` - Collection of test transcripts with varying complexity levels
- `run_evaluation.py` - Simple CLI tool to run evaluations
- `README.md` - This file

## Quick Start

1. **Start your API server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8080
   ```

2. **Run basic evaluation:**
   ```bash
   cd model_evaluation
   python run_evaluation.py
   ```

3. **Run with custom transcripts:**
   ```bash
   python run_evaluation.py --custom
   ```

## How It Works

1. **API Testing**: Sends test transcripts to your grammar analysis endpoint
2. **Response Analysis**: Examines the corrections and grades returned by your API  
3. **AI Evaluation**: Uses GPT-4 to assess the quality of the grammar analysis on a 1-10 scale
4. **Report Generation**: Creates detailed reports with recommendations

## Test Transcript Categories

- **Easy** (8-10 expected): Clean, grammatically correct text
- **Medium** (6-8 expected): Minor grammar errors, mixed tenses
- **Hard** (4-6 expected): Multiple grammar issues, subject-verb disagreement
- **Very Hard** (1-4 expected): Severe grammatical errors throughout
- **Complex Conversational** (3-6 expected): Natural speech patterns with embedded errors

## Evaluation Criteria

The AI evaluator considers:
- Did it catch major grammar errors?
- Are corrections accurate and appropriate?
- Did it avoid over-correcting natural speech?
- Are explanations clear and educational?
- Is the grade reasonable for the transcript complexity?

## Output

The evaluation generates:
- Overall performance scores
- Detailed analysis of each test case
- Recommendations for improvement
- JSON reports for further analysis

## Customizing Tests

Edit `test_transcripts.json` to add your own test cases:

```json
{
  "id": "your_test",
  "complexity": "Medium",
  "expected_score_range": [6, 8],
  "transcript": "Your test transcript here...",
  "description": "Description of what this tests"
}
```

## Troubleshooting

- Ensure your API server is running on the correct host/port
- Check that the OpenAI API key is configured in your environment
- Review API endpoint paths in `grammar_evaluation.py` if needed