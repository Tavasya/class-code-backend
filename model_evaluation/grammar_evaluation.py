import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GrammarAPIEvaluator:
    def __init__(self, base_url: str = "http://0.0.0.0:8080"):
        self.base_url = base_url
        self.api_endpoint = f"{base_url}/api/v1/grammar/analysis"
        
    async def test_api_endpoint(self, transcript: str) -> Dict[str, Any]:
        """Test the grammar API with a single transcript"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"transcript": transcript}
                async with session.post(self.api_endpoint, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "response": result,
                            "status_code": 200
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": error_text,
                            "status_code": response.status
                        }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "status_code": None
            }

    async def evaluate_grammar_analysis(self, transcript: str, expected_complexity: str) -> Dict[str, Any]:
        """Evaluate the grammar analysis quality using GPT-4"""
        api_result = await self.test_api_endpoint(transcript)
        
        if not api_result["success"]:
            return {
                "transcript": transcript,
                "expected_complexity": expected_complexity,
                "api_success": False,
                "error": api_result.get("error", "Unknown error"),
                "evaluation_score": 0
            }
        
        grammar_response = api_result["response"]
        corrections = grammar_response.get("grammar_corrections", {})
        grade = grammar_response.get("grade", 0)
        
        # Create evaluation prompt for GPT-4
        evaluation_prompt = f"""
You are an expert English teacher evaluating a grammar analysis system. 

Original transcript: "{transcript}"
Expected complexity level: {expected_complexity}

The grammar analysis system found {len(corrections)} corrections and gave a grade of {grade}/100.

Corrections found:
{json.dumps(corrections, indent=2)}

Rate the analysis quality on a scale of 1-10 considering:
1. Did it catch the major grammar errors?
2. Are the corrections accurate and appropriate?
3. Did it avoid over-correcting natural speech patterns?
4. Are the explanations clear and educational?
5. Is the grade reasonable for this level of transcript?

Provide ONLY a JSON response with this format:
{{
    "score": 8,
    "reasoning": "Brief explanation of why this score was given",
    "missed_errors": ["list", "of", "obvious", "errors", "missed"],
    "false_positives": ["list", "of", "incorrect", "corrections"],
    "grade_assessment": "Is the grade of {grade} appropriate? Why?"
}}
"""
        
        # Call OpenAI for evaluation
        evaluation_result = await self.call_openai_evaluation(evaluation_prompt)
        
        return {
            "transcript": transcript,
            "expected_complexity": expected_complexity,
            "api_success": True,
            "api_response": grammar_response,
            "corrections_count": len(corrections),
            "api_grade": grade,
            "evaluation": evaluation_result
        }

    async def call_openai_evaluation(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI API for evaluation"""
        try:
            # You'll need to add your OpenAI API key here or import from config
            from app.core.config import OPENAI_API_KEY, OPENAI_API_URL
            
            if not OPENAI_API_KEY:
                return {"error": "No OpenAI API key available for evaluation"}
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-5-nano",
                "messages": [{"role": "user", "content": prompt}]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Try to parse JSON response
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            return {"error": "Failed to parse evaluation JSON", "raw_response": content}
                    else:
                        error_text = await response.text()
                        return {"error": f"API error: {response.status}, {error_text}"}
                        
        except Exception as e:
            return {"error": f"Evaluation failed: {str(e)}"}

    async def run_comprehensive_evaluation(self):
        """Run evaluation on all test transcripts"""
        test_cases = [
            {
                "transcript": "I went to the store yesterday. I bought some apples and oranges. The cashier was very friendly. I had a good experience shopping there.",
                "expected_complexity": "Easy",
                "expected_score_range": (8, 10)
            },
            {
                "transcript": "Yesterday I go to the store and I buyed some fruits. The store it was very busy and I wait in line for long time. But the staff they was helpful and I get everything I need.",
                "expected_complexity": "Medium", 
                "expected_score_range": (6, 8)
            },
            {
                "transcript": "Me and my friend we goes to store yesterday but we doesn't have enough money so we can't bought nothing. The store were very expensive and they was many peoples waiting in the lines.",
                "expected_complexity": "Hard",
                "expected_score_range": (4, 6)
            },
            {
                "transcript": "Um so like yesterday me and my friends we was going to store but like we doesn't had no money and the store it don't take no cards so we couldn't bought nothing and we was very disappointing because we really need some foods for the party we was having.",
                "expected_complexity": "Very Hard",
                "expected_score_range": (1, 4)
            },
            {
                "transcript": "So basically what happened was I'm trying to explain to my boss about this project but he don't understand what I'm saying and I keeps repeating myself but nothing I say don't make no sense to him and I'm getting frustrated because this is really important and I needs to get this done by tomorrow.",
                "expected_complexity": "Complex Conversational",
                "expected_score_range": (3, 6)
            }
        ]
        
        logger.info("Starting comprehensive grammar API evaluation...")
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Evaluating test case {i}/{len(test_cases)}: {test_case['expected_complexity']}")
            
            result = await self.evaluate_grammar_analysis(
                test_case["transcript"], 
                test_case["expected_complexity"]
            )
            
            result["expected_score_range"] = test_case["expected_score_range"]
            results.append(result)
            
            # Add delay between requests to be respectful to API
            await asyncio.sleep(2)
        
        return self.generate_evaluation_report(results)

    def generate_evaluation_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a comprehensive evaluation report"""
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("api_success", False))
        
        evaluation_scores = []
        for result in results:
            if result.get("api_success") and result.get("evaluation", {}).get("score"):
                evaluation_scores.append(result["evaluation"]["score"])
        
        avg_evaluation_score = sum(evaluation_scores) / len(evaluation_scores) if evaluation_scores else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "successful_api_calls": successful_tests,
                "failed_api_calls": total_tests - successful_tests,
                "average_evaluation_score": round(avg_evaluation_score, 2),
                "evaluation_scores": evaluation_scores
            },
            "detailed_results": results,
            "recommendations": self.generate_recommendations(results)
        }
        
        return report

    def generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on evaluation results"""
        recommendations = []
        
        # Analyze common issues
        missed_errors_count = 0
        false_positives_count = 0
        
        for result in results:
            if result.get("evaluation"):
                eval_data = result["evaluation"]
                if eval_data.get("missed_errors"):
                    missed_errors_count += len(eval_data["missed_errors"])
                if eval_data.get("false_positives"):
                    false_positives_count += len(eval_data["false_positives"])
        
        if missed_errors_count > 3:
            recommendations.append("Consider improving error detection - system is missing obvious grammar mistakes")
        
        if false_positives_count > 2:
            recommendations.append("Reduce false positives - system is over-correcting natural speech patterns")
        
        # Check score consistency
        evaluation_scores = [r.get("evaluation", {}).get("score", 0) for r in results if r.get("api_success")]
        if evaluation_scores and min(evaluation_scores) < 6:
            recommendations.append("Overall performance needs improvement - consider refining prompts")
        
        if not recommendations:
            recommendations.append("Grammar analysis system is performing well overall")
        
        return recommendations

async def main():
    """Run the evaluation"""
    evaluator = GrammarAPIEvaluator()
    
    print("Starting Grammar API Evaluation...")
    print("Make sure your API server is running on http://localhost:8000")
    print("-" * 50)
    
    try:
        report = await evaluator.run_comprehensive_evaluation()
        
        # Save report to file
        report_filename = f"grammar_evaluation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w') as f:
            json.dump(report, indent=2, fp=f)
        
        # Print summary
        print("\n" + "="*50)
        print("EVALUATION COMPLETE")
        print("="*50)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"Successful API Calls: {report['summary']['successful_api_calls']}")
        print(f"Average Evaluation Score: {report['summary']['average_evaluation_score']}/10")
        print(f"Individual Scores: {report['summary']['evaluation_scores']}")
        
        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"- {rec}")
        
        print(f"\nDetailed report saved to: {report_filename}")
        
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())