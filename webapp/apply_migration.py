#!/usr/bin/env python3
"""
Apply database migration to add age and enrolled_company_count fields
"""
import os
from dotenv import load_dotenv
from core.utils.supabase_client import get_supabase_client

# Load environment variables
load_dotenv()

def apply_migration():
    """Apply the migration to add new fields to candidates table"""
    try:
        # Read the migration SQL
        migration_path = os.path.join(os.path.dirname(__file__), 'migrations', 'add_age_enrolled_company_fields.sql')
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        print(f"Applying migration from: {migration_path}")
        print(f"SQL:\n{sql}\n")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Note: Direct SQL execution through Supabase Python client is limited
        # You should run this SQL directly in Supabase dashboard SQL editor
        print("Please run the following SQL in your Supabase dashboard:")
        print("-" * 60)
        print(sql)
        print("-" * 60)
        print("\nAlternatively, you can use the Supabase CLI:")
        print("supabase db push")
        
        # Verify if columns exist (basic check)
        try:
            # Try to query with the new columns
            result = supabase.table('candidates').select('id, age, enrolled_company_count').limit(1).execute()
            print("\n✅ Migration appears to be already applied - columns exist!")
        except Exception as e:
            print("\n❌ Columns don't exist yet - please apply the migration")
            print(f"Error: {str(e)}")
        
    except FileNotFoundError:
        print(f"Error: Migration file not found at {migration_path}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    apply_migration()