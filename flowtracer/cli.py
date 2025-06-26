#!/usr/bin/env python3
"""
FlowTracer CLI - Analyze your codebase and generate flow visualizations
"""

import argparse
import os
import json
from pathlib import Path
from .analyzer import CodebaseAnalyzer
from .visualizer import FlowVisualizer


def main():
    parser = argparse.ArgumentParser(description='FlowTracer - AI-powered codebase flow analysis')
    parser.add_argument('project_path', help='Path to your Python project')
    parser.add_argument('--openai-key', required=True, help='OpenAI API key')
    parser.add_argument('--output', '-o', default='./flow_analysis.json', help='Output file path')
    parser.add_argument('--dashboard', '-d', action='store_true', help='Generate dashboard data')
    parser.add_argument('--mermaid', '-m', help='Generate Mermaid diagram for specific scenario')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.project_path):
        print(f"❌ Project path does not exist: {args.project_path}")
        return 1
    
    print("🚀 FlowTracer - Analyzing your codebase...")
    print(f"📁 Project: {args.project_path}")
    
    try:
        # Step 1: Analyze codebase
        print("\n" + "="*50)
        analyzer = CodebaseAnalyzer(args.project_path, args.openai_key)
        codebase_map = analyzer.analyze_codebase()
        
        print(f"✅ Analysis complete!")
        print(f"   📊 Functions found: {len(codebase_map.functions)}")
        print(f"   🎯 Entry points: {len(codebase_map.entry_points)}")
        print(f"   💾 Data sources: {len(codebase_map.data_sources)}")
        print(f"   📤 Data sinks: {len(codebase_map.data_sinks)}")
        
        # Step 2: Generate visualizations
        print("\n" + "="*50)
        visualizer = FlowVisualizer(codebase_map, args.openai_key)
        
        if args.dashboard:
            print("🎨 Generating dashboard data...")
            dashboard_data = visualizer.export_for_dashboard(args.output)
            print(f"✅ Dashboard data saved to: {args.output}")
            
            # Also save a summary
            summary_path = args.output.replace('.json', '_summary.txt')
            save_summary(codebase_map, dashboard_data, summary_path)
            print(f"📄 Summary saved to: {summary_path}")
            
        elif args.mermaid:
            print(f"🧩 Generating Mermaid diagram for: {args.mermaid}")
            scenarios = visualizer.generate_flow_scenarios()
            mermaid_diagram = visualizer.generate_mermaid_diagram(args.mermaid)
            
            if mermaid_diagram != "Scenario not found":
                mermaid_path = args.output.replace('.json', '.mermaid')
                with open(mermaid_path, 'w') as f:
                    f.write(mermaid_diagram)
                print(f"✅ Mermaid diagram saved to: {mermaid_path}")
            else:
                print(f"❌ Scenario '{args.mermaid}' not found")
                print("Available scenarios:")
                for scenario in scenarios:
                    print(f"  - {scenario['id']}: {scenario['name']}")
        
        else:
            # Save raw analysis data
            output_data = {
                'functions': {name: func.__dict__ for name, func in codebase_map.functions.items()},
                'call_graph': codebase_map.call_graph,
                'entry_points': codebase_map.entry_points,
                'data_sources': codebase_map.data_sources,
                'data_sinks': codebase_map.data_sinks
            }
            
            with open(args.output, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            print(f"✅ Analysis data saved to: {args.output}")
        
        print("\n🎉 FlowTracer analysis complete!")
        print(f"   💡 Tip: Use --dashboard to generate web visualization")
        print(f"   💡 Tip: Use --mermaid <scenario_id> to generate diagrams")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return 1


def save_summary(codebase_map, dashboard_data, output_path):
    """Save a human-readable summary of the analysis"""
    with open(output_path, 'w') as f:
        f.write("FlowTracer Analysis Summary\n")
        f.write("=" * 50 + "\n\n")
        
        # Overview
        f.write(f"📊 Total Functions: {len(codebase_map.functions)}\n")
        f.write(f"🎯 Entry Points: {len(codebase_map.entry_points)}\n")
        f.write(f"💾 Data Sources: {len(codebase_map.data_sources)}\n")
        f.write(f"📤 Data Sinks: {len(codebase_map.data_sinks)}\n\n")
        
        # Entry Points
        f.write("🎯 Entry Points (API endpoints, main functions):\n")
        f.write("-" * 40 + "\n")
        for entry_point in codebase_map.entry_points[:10]:  # Show top 10
            func = codebase_map.functions.get(entry_point)
            if func:
                f.write(f"  • {func.name} ({entry_point})\n")
                f.write(f"    File: {func.file_path}:{func.line_number}\n")
                if hasattr(func, 'display_name'):
                    f.write(f"    Purpose: {func.display_name}\n")
                f.write("\n")
        
        # Complex Functions
        f.write("🔥 Most Complex Functions:\n")
        f.write("-" * 40 + "\n")
        complex_funcs = sorted(codebase_map.functions.values(), 
                              key=lambda f: f.complexity_score, 
                              reverse=True)[:10]
        
        for func in complex_funcs:
            f.write(f"  • {func.name} (Complexity: {func.complexity_score})\n")
            f.write(f"    File: {func.file_path}:{func.line_number}\n")
            if hasattr(func, 'display_name'):
                f.write(f"    Purpose: {func.display_name}\n")
            f.write("\n")
        
        # Flow Scenarios
        if 'scenarios' in dashboard_data:
            f.write("🌊 Flow Scenarios:\n")
            f.write("-" * 40 + "\n")
            for scenario in dashboard_data['scenarios']:
                f.write(f"  • {scenario['name']}\n")
                f.write(f"    Purpose: {scenario.get('business_purpose', 'Unknown')}\n")
                f.write(f"    Complexity: {scenario.get('estimated_complexity', 0)}\n")
                f.write(f"    Bottlenecks: {len(scenario.get('potential_bottlenecks', []))}\n")
                f.write("\n")


if __name__ == '__main__':
    exit(main())