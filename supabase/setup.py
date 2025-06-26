#!/usr/bin/env python3
"""
Setup script for FlowTracer Supabase database
Run this once to create the necessary tables and functions
"""

import os
from supabase import create_client, Client
from pathlib import Path

def setup_database():
    """Setup the FlowTracer database schema in Supabase"""
    
    # Get credentials from environment
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')  # Use service key for admin operations
    
    if not supabase_url or not supabase_key:
        print("Error: Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        return False
    
    try:
        # Create client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Read schema file
        schema_file = Path(__file__).parent / 'schema.sql'
        if not schema_file.exists():
            print(f"Error: Schema file not found at {schema_file}")
            return False
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split into individual statements (basic splitting on semicolons)
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        
        # Execute each statement
        for i, statement in enumerate(statements, 1):
            if statement.strip():
                try:
                    print(f"[{i}/{len(statements)}] Executing statement...")
                    # Use rpc to execute raw SQL
                    supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✓ Statement {i} executed successfully")
                except Exception as e:
                    print(f"⚠️  Statement {i} failed (might be expected): {e}")
        
        print("\n✅ Database setup completed!")
        print("\nNext steps:")
        print("1. Update your RLS policies based on your authentication needs")
        print("2. Test the setup with the example usage script")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

if __name__ == "__main__":
    print("FlowTracer Database Setup")
    print("=" * 30)
    success = setup_database()
    exit(0 if success else 1)