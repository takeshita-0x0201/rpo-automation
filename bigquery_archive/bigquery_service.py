"""
BigQueryサービス - 候補者データのアップロード処理
"""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account
import asyncio

# BigQueryクライアントの初期化
def get_bigquery_client():
    """BigQueryクライアントを初期化して返す"""
    try:
        # 環境変数から認証情報を取得
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')
        if credentials_json:
            # JSON文字列から認証情報を作成
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info
            )
        else:
            # ファイルパスから認証情報を取得
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                raise ValueError("Google Cloud credentials not found")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        
        # プロジェクトID
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT', 'rpo-automation')
        
        return bigquery.Client(
            credentials=credentials,
            project=project_id
        )
    except Exception as e:
        print(f"Error initializing BigQuery client: {e}")
        raise

async def upload_candidates_to_bigquery(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    候補者データをBigQueryにアップロード
    
    Args:
        candidates: 候補者データのリスト
        
    Returns:
        アップロード結果
    """
    try:
        # 非同期でBigQueryクライアントを取得
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(None, get_bigquery_client)
        
        # データセットとテーブルの設定
        dataset_id = 'recruitment_data'  # 実際のデータセット名
        table_id = 'candidates'  # 実際のテーブル名
        
        # テーブル参照
        table_ref = client.dataset(dataset_id).table(table_id)
        try:
            table = client.get_table(table_ref)
            print(f"Found BigQuery table: {dataset_id}.{table_id}")
        except Exception as e:
            print(f"BigQuery table not found: {dataset_id}.{table_id}")
            print(f"Error: {e}")
            # テーブルが存在しない場合は作成を試みる
            from google.cloud import bigquery
            schema = [
                bigquery.SchemaField("candidate_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("current_company", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("current_position", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("experience", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("skills", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("education", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("bizreach_url", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("platform", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("client_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("requirement_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("session_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("scraped_by", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="NULLABLE"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("html", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("full_text", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("age", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("current_salary", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("tenure_years", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("job_changes", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("last_login", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("desired_location", "STRING", mode="NULLABLE"),
            ]
            table = bigquery.Table(table_ref, schema=schema)
            table = client.create_table(table)
            print(f"Created BigQuery table: {dataset_id}.{table_id}")
        
        # データを整形（BigQueryのスキーマに合わせる）
        rows_to_insert = []
        for candidate in candidates:
            row = {
                'id': candidate.get('candidate_id'),  # candidate_id を id にマップ
                'search_id': candidate.get('session_id'),  # session_id を search_id にマップ
                'bizreach_id': candidate.get('bizreach_url'),  # URLをIDとして使用
                'name': candidate.get('name'),
                'current_title': candidate.get('current_position'),  # current_position を current_title にマップ
                'current_company': candidate.get('current_company'),
                'experience_years': None,  # 文字列から数値への変換が必要な場合は後で実装
                'skills': candidate.get('skills', []),  # REPEATEDフィールドなので配列のまま
                'education': candidate.get('education'),
                'profile_url': candidate.get('bizreach_url'),  # bizreach_urlをprofile_urlとして使用
                'profile_summary': candidate.get('experience'),  # experienceをsummaryとして使用
                'scraped_at': candidate.get('scraped_at'),
                'scraped_data': {  # 追加のデータは scraped_data として保存
                    'education': candidate.get('education'),
                    'experience': candidate.get('experience'),
                    'age': candidate.get('age'),
                    'current_salary': candidate.get('current_salary'),
                    'tenure_years': candidate.get('tenure_years'),
                    'job_changes': candidate.get('job_changes'),
                    'last_login': candidate.get('last_login'),
                    'desired_location': candidate.get('desired_location'),
                    'full_text': candidate.get('full_text'),
                    'platform': candidate.get('platform'),
                    'client_id': candidate.get('client_id'),
                    'requirement_id': candidate.get('requirement_id'),
                    'scraped_by': candidate.get('scraped_by')
                }
            }
            rows_to_insert.append(row)
        
        # バッチ挿入
        errors = await loop.run_in_executor(
            None,
            client.insert_rows_json,
            table,
            rows_to_insert
        )
        
        if errors:
            print(f"BigQuery insert errors: {errors}")
            return {
                'success': False,
                'error': 'Failed to insert some rows',
                'details': errors,
                'inserted': 0
            }
        
        return {
            'success': True,
            'inserted': len(rows_to_insert),
            'table': f"{dataset_id}.{table_id}"
        }
        
    except Exception as e:
        print(f"Error uploading to BigQuery: {e}")
        return {
            'success': False,
            'error': str(e),
            'inserted': 0
        }

def create_bigquery_table_if_not_exists():
    """
    BigQueryテーブルが存在しない場合は作成する
    """
    try:
        client = get_bigquery_client()
        
        dataset_id = os.getenv('BIGQUERY_DATASET_ID', 'rpo_automation')
        table_id = os.getenv('BIGQUERY_TABLE_ID', 'scraped_candidates')
        
        # スキーマ定義
        schema = [
            bigquery.SchemaField("candidate_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("current_company", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("current_position", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("experience", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("skills", "STRING", mode="NULLABLE"),  # JSON文字列として保存
            bigquery.SchemaField("education", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("bizreach_url", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("platform", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("client_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("requirement_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("scraped_by", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="NULLABLE"),
            bigquery.SchemaField("html", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("full_text", "STRING", mode="NULLABLE"),  # 要素全体のテキスト
            bigquery.SchemaField("age", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("current_salary", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("tenure_years", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("job_changes", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("last_login", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("desired_location", "STRING", mode="NULLABLE"),
        ]
        
        # テーブル作成
        table_ref = client.dataset(dataset_id).table(table_id)
        table = bigquery.Table(table_ref, schema=schema)
        
        # パーティショニング設定（scraped_atで日別パーティション）
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="scraped_at"
        )
        
        # テーブル作成（既存の場合はスキップ）
        table = client.create_table(table, exists_ok=True)
        print(f"BigQuery table {dataset_id}.{table_id} is ready")
        
        return True
        
    except Exception as e:
        print(f"Error creating BigQuery table: {e}")
        return False