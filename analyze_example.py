#!/usr/bin/env python3
"""
Example script to analyze your codebase and generate visualizations
"""

import os
from flowtracer.analyzer import CodebaseAnalyzer
from flowtracer.visualizer import FlowVisualizer

def main():
    # Configuration
    PROJECT_PATH = "."  # Current directory
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    if not OPENAI_API_KEY:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    print("🚀 FlowTracer - Analyzing your codebase...")
    print(f"📁 Project: {PROJECT_PATH}")
    
    try:
        # Step 1: Analyze codebase
        print("\n🔍 Step 1: Analyzing code structure...")
        analyzer = CodebaseAnalyzer(PROJECT_PATH, OPENAI_API_KEY)
        codebase_map = analyzer.analyze_codebase()
        
        print(f"✅ Found {len(codebase_map.functions)} functions")
        print(f"🎯 {len(codebase_map.entry_points)} entry points")
        
        # Step 2: Generate visualizations
        print("\n🎨 Step 2: Generating visualizations...")
        visualizer = FlowVisualizer(codebase_map, OPENAI_API_KEY)
        
        # Export dashboard data
        dashboard_data = visualizer.export_for_dashboard('./dashboard/data.json')
        
        # Generate flow scenarios
        scenarios = visualizer.generate_flow_scenarios()
        
        print(f"✅ Generated {len(scenarios)} flow scenarios")
        
        # Show sample results
        print("\n📊 Sample Results:")
        print("-" * 40)
        
        # Show top entry points
        print("🎯 Entry Points:")
        for entry in codebase_map.entry_points[:5]:
            func = codebase_map.functions.get(entry)
            if func:
                display_name = getattr(func, 'display_name', func.name)
                print(f"  • {display_name} ({func.file_path}:{func.line_number})")
        
        # Show sample scenarios
        print("\n🌊 Flow Scenarios:")
        for scenario in scenarios[:3]:
            print(f"  • {scenario['name']}")
            print(f"    Purpose: {scenario.get('business_purpose', 'Unknown')}")
            print(f"    Complexity: {scenario.get('estimated_complexity', 0)}")
        
        print(f"\n🎉 Analysis complete!")
        print(f"💡 Open dashboard/index.html to view interactive visualization")
        print(f"💾 Data saved to dashboard/data.json")
        
        # Generate a sample Mermaid diagram
        if scenarios:
            sample_scenario = scenarios[0]
            mermaid = visualizer.generate_mermaid_diagram(sample_scenario['id'])
            with open('sample_flow.mermaid', 'w') as f:
                f.write(mermaid)
            print(f"🧩 Sample Mermaid diagram saved to sample_flow.mermaid")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()