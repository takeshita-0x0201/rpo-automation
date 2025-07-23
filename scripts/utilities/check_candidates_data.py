#!/usr/bin/env python3
"""
候補者データの存在確認スクリプト
"""
import os
from dotenv import load_dotenv

load_dotenv()

def check_candidates_data():
    """候補者データの存在を確認"""
    try:
        from core.utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        print("=== 候補者データ確認 ===")
        
        # 候補者テーブルの存在確認
        try:
            candidates_response = supabase.table('candidates').select('*').limit(5).execute()
            candidates = candidates_response.data or []
            
            print(f"✓ candidatesテーブル: {len(candidates)}件のデータが見つかりました")
            
            if candidates:
                print("\n最初の候補者データ:")
                for i, candidate in enumerate(candidates[:2]):
                    print(f"  {i+1}. ID: {candidate.get('id')}")
                    print(f"     candidate_id: {candidate.get('candidate_id')}")
                    print(f"     client_id: {candidate.get('client_id')}")
                    print(f"     requirement_id: {candidate.get('requirement_id')}")
                    print(f"     scraped_at: {candidate.get('scraped_at')}")
                    print()
            else:
                print("  候補者データが存在しません")
                
        except Exception as e:
            print(f"✗ candidatesテーブルアクセスエラー: {e}")
        
        # ジョブテーブルの確認
        try:
            jobs_response = supabase.table('jobs').select('*').limit(5).execute()
            jobs = jobs_response.data or []
            
            print(f"✓ jobsテーブル: {len(jobs)}件のデータが見つかりました")
            
            if jobs:
                print("\n最初のジョブデータ:")
                for i, job in enumerate(jobs[:2]):
                    print(f"  {i+1}. ID: {job.get('id')}")
                    print(f"     job_id: {job.get('job_id')}")
                    print(f"     client_id: {job.get('client_id')}")
                    print(f"     requirement_id: {job.get('requirement_id')}")
                    print(f"     status: {job.get('status')}")
                    print()
                    
        except Exception as e:
            print(f"✗ jobsテーブルアクセスエラー: {e}")
        
        # クライアントテーブルの確認
        try:
            clients_response = supabase.table('clients').select('*').limit(5).execute()
            clients = clients_response.data or []
            
            print(f"✓ clientsテーブル: {len(clients)}件のデータが見つかりました")
            
            if clients:
                print("\n最初のクライアントデータ:")
                for i, client in enumerate(clients[:2]):
                    print(f"  {i+1}. ID: {client.get('id')}")
                    print(f"     name: {client.get('name')}")
                    print(f"     is_active: {client.get('is_active')}")
                    print()
                    
        except Exception as e:
            print(f"✗ clientsテーブルアクセスエラー: {e}")
        
        # 採用要件テーブルの確認
        try:
            requirements_response = supabase.table('job_requirements').select('*').limit(5).execute()
            requirements = requirements_response.data or []
            
            print(f"✓ job_requirementsテーブル: {len(requirements)}件のデータが見つかりました")
            
            if requirements:
                print("\n最初の採用要件データ:")
                for i, req in enumerate(requirements[:2]):
                    print(f"  {i+1}. ID: {req.get('id')}")
                    print(f"     title: {req.get('title')}")
                    print(f"     client_id: {req.get('client_id')}")
                    print(f"     is_active: {req.get('is_active')}")
                    print()
                    
        except Exception as e:
            print(f"✗ job_requirementsテーブルアクセスエラー: {e}")
            
    except Exception as e:
        print(f"✗ データベース接続エラー: {e}")

def create_sample_data():
    """サンプルデータを作成"""
    try:
        from core.utils.supabase_client import get_supabase_client
        import uuid
        from datetime import datetime
        
        supabase = get_supabase_client()
        
        print("\n=== サンプルデータ作成 ===")
        
        # サンプルクライアントを作成
        client_data = {
            "id": str(uuid.uuid4()),
            "name": "サンプル企業",
            "industry": "IT",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        client_result = supabase.table('clients').insert(client_data).execute()
        client_id = client_result.data[0]['id'] if client_result.data else None
        
        if client_id:
            print(f"✓ サンプルクライアント作成: {client_id}")
            
            # サンプル採用要件を作成
            requirement_data = {
                "id": str(uuid.uuid4()),
                "client_id": client_id,
                "title": "サンプル求人",
                "description": "サンプル求人の説明",
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            req_result = supabase.table('job_requirements').insert(requirement_data).execute()
            requirement_id = req_result.data[0]['id'] if req_result.data else None
            
            if requirement_id:
                print(f"✓ サンプル採用要件作成: {requirement_id}")
                
                # サンプル候補者を作成
                for i in range(3):
                    candidate_data = {
                        "id": str(uuid.uuid4()),
                        "candidate_id": f"sample-candidate-{i+1}",
                        "candidate_link": f"https://example.com/candidate/{i+1}",
                        "candidate_company": f"サンプル企業{i+1}",
                        "candidate_resume": f"サンプル候補者{i+1}のレジュメ内容...",
                        "platform": "bizreach",
                        "client_id": client_id,
                        "requirement_id": requirement_id,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "created_at": datetime.utcnow().isoformat()
                    }
                    
                    cand_result = supabase.table('candidates').insert(candidate_data).execute()
                    if cand_result.data:
                        print(f"✓ サンプル候補者{i+1}作成: {cand_result.data[0]['id']}")
                
                print(f"\nサンプルデータ作成完了:")
                print(f"  クライアントID: {client_id}")
                print(f"  採用要件ID: {requirement_id}")
                
        else:
            print("✗ サンプルクライアント作成失敗")
            
    except Exception as e:
        print(f"✗ サンプルデータ作成エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("候補者データ確認スクリプト")
    print("=" * 50)
    
    check_candidates_data()
    
    # サンプルデータを作成するかユーザーに確認
    create_sample = input("\nサンプルデータを作成しますか？ (y/N): ").lower().strip()
    if create_sample == 'y':
        create_sample_data()
        print("\nサンプルデータ作成後の状況:")
        check_candidates_data()