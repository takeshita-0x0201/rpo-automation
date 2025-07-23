"""
Run sync columns migration
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.utils.supabase_client import get_supabase_client

def run_migration():
    """Execute the sync columns migration"""
    print("Running sync columns migration...")
    
    # Read the SQL file
    migration_file = os.path.join(os.path.dirname(__file__), 'add_sync_columns.sql')
    with open(migration_file, 'r') as f:
        sql_content = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in sql_content.split(';') if s.strip()]
    
    supabase = get_supabase_client()
    
    for i, statement in enumerate(statements):
        try:
            print(f"Executing statement {i+1}/{len(statements)}...")
            # Use RPC to execute raw SQL
            result = supabase.rpc('exec_sql', {'query': statement + ';'}).execute()
            print(f"✓ Statement {i+1} executed successfully")
        except Exception as e:
            print(f"✗ Error executing statement {i+1}: {e}")
            # Continue with other statements even if one fails
            continue
    
    print("\nMigration completed!")
    
    # Test the sync_status view
    try:
        print("\nTesting sync_status view...")
        result = supabase.table('sync_status').select('*').execute()
        if result.data:
            status = result.data[0]
            print(f"✓ Sync status: {status}")
        else:
            print("✓ Sync status view created successfully (no data yet)")
    except Exception as e:
        print(f"✗ Error testing sync_status view: {e}")

if __name__ == "__main__":
    run_migration()