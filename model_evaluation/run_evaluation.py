#!/usr/bin/env python3
"""
Simple script to run grammar evaluation with different transcript sets
"""
import asyncio
import json
import sys
from grammar_evaluation import GrammarAPIEvaluator

def load_test_transcripts():
    """Load test transcripts from JSON file"""
    try:
        with open('test_transcripts.json', 'r') as f:
            data = json.load(f)
            return data['test_transcripts']
    except FileNotFoundError:
        print("test_transcripts.json not found. Using basic test cases.")
        return []

async def run_basic_evaluation():
    """Run evaluation with basic test cases"""
    evaluator = GrammarAPIEvaluator()
    
    print("Testing API connectivity...")
    
    # Simple connectivity test
    test_result = await evaluator.test_api_endpoint("This is a test sentence.")
    if not test_result["success"]:
        print(f"❌ API connectivity failed: {test_result.get('error', 'Unknown error')}")
        print("Make sure your server is running with: uvicorn app.main:app --host 0.0.0.0 --port 8080")
        return
    
    print("✅ API is responsive")
    print("\nRunning comprehensive evaluation...")
    
    # Run full evaluation
    report = await evaluator.run_comprehensive_evaluation()
    
    # Print results
    print("\n" + "="*60)
    print("GRAMMAR API EVALUATION RESULTS")
    print("="*60)
    
    summary = report['summary']
    print(f"Tests Run: {summary['total_tests']}")
    print(f"Successful: {summary['successful_api_calls']}")
    print(f"Failed: {summary['failed_api_calls']}")
    print(f"Average Score: {summary['average_evaluation_score']}/10")
    
    if summary['evaluation_scores']:
        print(f"Score Range: {min(summary['evaluation_scores'])}-{max(summary['evaluation_scores'])}")
    
    print("\n📋 RECOMMENDATIONS:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    # Save detailed report
    timestamp = report['timestamp'].replace(':', '-').replace('.', '-')
    filename = f"evaluation_report_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved: {filename}")
    
    return report

async def run_custom_transcript_evaluation(transcripts):
    """Run evaluation with custom transcripts from JSON file"""
    evaluator = GrammarAPIEvaluator()
    
    print(f"Running evaluation on {len(transcripts)} custom transcripts...")
    
    results = []
    for i, test_case in enumerate(transcripts, 1):
        print(f"Testing {i}/{len(transcripts)}: {test_case['id']} ({test_case['complexity']})")
        
        result = await evaluator.evaluate_grammar_analysis(
            test_case["transcript"], 
            test_case["complexity"]
        )
        
        result["test_id"] = test_case["id"]
        result["expected_score_range"] = test_case["expected_score_range"]
        result["description"] = test_case["description"]
        results.append(result)
        
        # Brief pause between requests
        await asyncio.sleep(1)
    
    # Generate report
    report = evaluator.generate_evaluation_report(results)
    
    # Print summary
    print("\n" + "="*60)
    print("CUSTOM TRANSCRIPT EVALUATION RESULTS")
    print("="*60)
    
    successful = [r for r in results if r.get("api_success")]
    print(f"Total transcripts: {len(transcripts)}")
    print(f"Successful evaluations: {len(successful)}")
    
    if successful:
        scores = [r.get("evaluation", {}).get("score", 0) for r in successful]
        valid_scores = [s for s in scores if s > 0]
        if valid_scores:
            print(f"Average evaluation score: {sum(valid_scores)/len(valid_scores):.1f}/10")
            print(f"Score range: {min(valid_scores)}-{max(valid_scores)}")
    
    # Show per-complexity breakdown
    complexity_groups = {}
    for result in successful:
        complexity = result.get("expected_complexity", "Unknown")
        if complexity not in complexity_groups:
            complexity_groups[complexity] = []
        
        eval_score = result.get("evaluation", {}).get("score", 0)
        if eval_score > 0:
            complexity_groups[complexity].append(eval_score)
    
    print("\n📊 PERFORMANCE BY COMPLEXITY:")
    for complexity, scores in complexity_groups.items():
        if scores:
            avg_score = sum(scores) / len(scores)
            print(f"  {complexity}: {avg_score:.1f}/10 (n={len(scores)})")
    
    # Save report
    timestamp = report['timestamp'].replace(':', '-').replace('.', '-')
    filename = f"custom_evaluation_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Report saved: {filename}")
    return report

async def main():
    """Main execution function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        # Load and run custom transcripts
        transcripts = load_test_transcripts()
        if transcripts:
            await run_custom_transcript_evaluation(transcripts)
        else:
            print("No custom transcripts found, running basic evaluation...")
            await run_basic_evaluation()
    else:
        # Run basic evaluation
        await run_basic_evaluation()

if __name__ == "__main__":
    print("Grammar API Evaluation Tool")
    print("=" * 40)
    print("Usage:")
    print("  python run_evaluation.py          # Run basic evaluation")
    print("  python run_evaluation.py --custom # Use test_transcripts.json")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Evaluation stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")