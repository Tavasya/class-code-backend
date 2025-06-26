#!/usr/bin/env python3
"""
Complete FlowTracer example showing both static analysis and runtime tracing
"""

import os
from flowtracer import (
    init_tracer, 
    CodebaseAnalyzer, 
    FlowVisualizer, 
    AutoTracer,
    start_flow, 
    trace_flow
)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'your-supabase-url')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your-supabase-key')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-openai-key')

def demo_static_analysis():
    """Demonstrate static codebase analysis"""
    print("🔍 STATIC ANALYSIS DEMO")
    print("=" * 50)
    
    # Analyze current codebase
    analyzer = CodebaseAnalyzer(".", OPENAI_API_KEY)
    codebase_map = analyzer.analyze_codebase()
    
    print(f"📊 Found {len(codebase_map.functions)} functions")
    print(f"🎯 {len(codebase_map.entry_points)} entry points")
    
    # Generate visualizations
    visualizer = FlowVisualizer(codebase_map, OPENAI_API_KEY)
    scenarios = visualizer.generate_flow_scenarios()
    
    print(f"🌊 Generated {len(scenarios)} flow scenarios")
    
    # Export for dashboard
    visualizer.export_for_dashboard('./dashboard/demo_data.json')
    print("✅ Dashboard data exported")
    
    return codebase_map

def demo_auto_instrumentation():
    """Demonstrate automatic code instrumentation"""
    print("\n🤖 AUTO-INSTRUMENTATION DEMO")
    print("=" * 50)
    
    # Create auto-tracer
    auto_tracer = AutoTracer(".", SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY)
    
    # Create instrumented copy (safer than modifying original)
    results = auto_tracer.create_instrumented_copy("./demo_instrumented")
    
    print(f"🎯 Instrumented {results['successfully_instrumented']} functions")
    print(f"📁 Modified {results['files_modified']} files")
    print("✅ Instrumented code saved to ./demo_instrumented")

def demo_runtime_tracing():
    """Demonstrate runtime tracing of actual function calls"""
    print("\n⚡ RUNTIME TRACING DEMO")
    print("=" * 50)
    
    # Initialize tracer
    init_tracer(SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY)
    
    # Example business logic with tracing
    @trace_flow("User Registration")
    def register_user(email: str, name: str):
        user_data = validate_user_input(email, name)
        user_id = save_user_to_database(user_data)
        send_welcome_email(user_id, email)
        return user_id
    
    @trace_flow()
    def validate_user_input(email: str, name: str):
        # Simulate validation
        if '@' not in email:
            raise ValueError("Invalid email")
        return {'email': email, 'name': name, 'validated': True}
    
    @trace_flow()
    def save_user_to_database(user_data):
        # Simulate database save
        import time
        time.sleep(0.1)  # Simulate DB latency
        return 12345  # Mock user ID
    
    @trace_flow()
    def send_welcome_email(user_id: int, email: str):
        # Simulate email sending
        import time
        time.sleep(0.05)  # Simulate email service latency
        print(f"📧 Welcome email sent to {email}")
    
    # Simulate API request with flow tracking
    request_id = "req_demo_123"
    endpoint = "/api/demo/register"
    
    print(f"🚀 Simulating API request: {endpoint}")
    
    with start_flow(request_id, endpoint) as flow_id:
        print(f"📍 Started flow: {flow_id}")
        
        try:
            user_id = register_user("demo@example.com", "Demo User")
            print(f"✅ User registered with ID: {user_id}")
        except Exception as e:
            print(f"❌ Registration failed: {e}")
    
    print("✅ Runtime tracing complete - check your Supabase database!")

def main():
    """Run complete FlowTracer demonstration"""
    print("🚀 FlowTracer Complete Demo")
    print("=" * 60)
    
    # Check environment
    if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY]):
        print("⚠️  Please set environment variables:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_KEY") 
        print("   - OPENAI_API_KEY")
        return
    
    try:
        # Demo 1: Static Analysis
        codebase_map = demo_static_analysis()
        
        # Demo 2: Auto-instrumentation
        demo_auto_instrumentation()
        
        # Demo 3: Runtime Tracing
        demo_runtime_tracing()
        
        print("\n🎉 DEMO COMPLETE!")
        print("=" * 60)
        print("What you got:")
        print("📊 Static analysis of your codebase")
        print("🎨 Interactive dashboard (open dashboard/index.html)")
        print("🤖 Auto-instrumented code in ./demo_instrumented")
        print("⚡ Runtime flow data in your Supabase database")
        print("💡 AI-powered human-readable function descriptions")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()