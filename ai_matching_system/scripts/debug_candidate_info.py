#!/usr/bin/env python3
"""
候補者情報デバッグスクリプト
Supabaseから候補者情報を取得して詳細に表示します
"""

import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv
from supabase import create_client, Client

# 親ディレクトリをパスに追加（ai_matching_systemからのインポート用）
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# 環境変数を読み込み（親ディレクトリの.envファイルから）
env_path = os.path.join(parent_dir, '.env')
print(f".envファイルパス: {env_path}")
print(f".envファイル存在: {os.path.exists(env_path)}")
load_dotenv(env_path)

class CandidateInfoDebugger:
    """候補者情報デバッグクラス"""
    
    def __init__(self):
        """初期化"""
        # Supabaseクライアントの初期化
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            print("エラー: SUPABASE_URLとSUPABASE_KEYの環境変数が必要です")
            print("環境変数を設定するか、.envファイルに追加してください")
            sys.exit(1)
        
        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            print("✓ Supabase接続成功")
        except Exception as e:
            print(f"✗ Supabase接続エラー: {e}")
            sys.exit(1)
    
    async def get_candidate_info_by_id(self, candidate_id):
        """IDで候補者情報を取得"""
        try:
            print(f"\n=== 候補者ID '{candidate_id}' の情報を取得中... ===")
            
            # candidatesテーブルから情報を取得
            response = self.supabase.table('candidates').select('*').eq('candidate_id', candidate_id).execute()
            
            if not response.data:
                print(f"✗ 候補者ID '{candidate_id}' の情報が見つかりません")
                return None
            
            candidate = response.data[0]
            return candidate
            
        except Exception as e:
            print(f"✗ 候補者情報取得エラー: {e}")
            return None
    
    async def get_candidate_info_from_resume(self, resume_file):
        """レジュメファイルから候補者情報を取得"""
        try:
            print(f"\n=== レジュメファイル '{resume_file}' から候補者情報を取得中... ===")
            
            # レジュメファイルを読み込む
            with open(resume_file, 'r', encoding='utf-8') as f:
                resume_text = f.read()
                print(f"  レジュメ読み込み完了: {len(resume_text)}文字")
            
            # レジュメから候補者IDを抽出
            candidate_id = None
            lines = resume_text.strip().split('\n')
            
            print("\n候補者ID抽出試行:")
            for i, line in enumerate(lines[:20]):  # 最初の20行をチェック
                print(f"  行 {i+1}: {line[:50]}{'...' if len(line) > 50 else ''}")
                if 'ID:' in line or 'candidate_id:' in line.lower() or 'candidate id:' in line.lower():
                    candidate_id = line.split(':', 1)[-1].strip()
                    print(f"  → 候補者ID検出: '{candidate_id}'")
                    break
            
            if not candidate_id:
                print("✗ レジュメから候補者IDを抽出できませんでした")
                return None
            
            # 抽出したIDで候補者情報を取得
            return await self.get_candidate_info_by_id(candidate_id)
            
        except Exception as e:
            print(f"✗ レジュメ処理エラー: {e}")
            return None
    
    def display_candidate_info(self, candidate):
        """候補者情報を表示"""
        if not candidate:
            return
        
        print("\n=== 候補者情報 ===")
        print(f"候補者ID: {candidate.get('candidate_id', 'N/A')}")
        
        # 基本情報
        print("\n【基本情報】")
        fields = [
            ('age', '年齢'),
            ('gender', '性別'),
            ('candidate_company', '現在の所属'),
            ('enrolled_company_count', '在籍企業数')
        ]
        
        for field, label in fields:
            value = candidate.get(field, 'N/A')
            print(f"{label}: {value}")
        
        # その他の利用可能なフィールド
        print("\n【その他の情報】")
        for key, value in candidate.items():
            if key not in ['candidate_id', 'age', 'gender', 'candidate_company', 'enrolled_company_count']:
                if value is not None:
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    print(f"{key}: {value}")
        
        # EvaluatorNodeで使用される形式
        print("\n【EvaluatorNodeで使用される形式】")
        info_parts = []
        if candidate.get('age'):
            info_parts.append(f"年齢: {candidate['age']}歳")
        if candidate.get('gender'):
            info_parts.append(f"性別: {candidate['gender']}")
        if candidate.get('candidate_company'):
            info_parts.append(f"現在の所属: {candidate['candidate_company']}")
        if candidate.get('enrolled_company_count'):
            info_parts.append(f"在籍企業数: {candidate['enrolled_company_count']}社")
        
        formatted_info = '\n'.join(info_parts) if info_parts else "年齢: 不明"
        print(formatted_info)
    
    async def list_recent_candidates(self, limit=5):
        """最近の候補者を一覧表示"""
        try:
            print(f"\n=== 最近の候補者一覧（最大{limit}件） ===")
            
            response = self.supabase.table('candidates').select('candidate_id,age,gender,candidate_company').order('created_at', desc=True).limit(limit).execute()
            
            if not response.data:
                print("候補者データが見つかりません")
                return
            
            print("\n【候補者一覧】")
            for i, candidate in enumerate(response.data, 1):
                print(f"{i}. ID: {candidate.get('candidate_id', 'N/A')}")
                print(f"   年齢: {candidate.get('age', 'N/A')}")
                print(f"   性別: {candidate.get('gender', 'N/A')}")
                print(f"   所属: {candidate.get('candidate_company', 'N/A')}")
                print()
            
        except Exception as e:
            print(f"✗ 候補者一覧取得エラー: {e}")
    
    async def check_database_connection(self):
        """データベース接続確認"""
        try:
            print("\n=== データベース接続確認 ===")
            
            # candidatesテーブルの存在確認
            response = self.supabase.table('candidates').select('count').limit(1).execute()
            print("✓ candidatesテーブルに接続できました")
            
            # テーブル構造の確認
            print("\n【テーブル構造】")
            # 実際のデータから構造を推測
            sample_response = self.supabase.table('candidates').select('*').limit(1).execute()
            if sample_response.data:
                sample = sample_response.data[0]
                for key in sample.keys():
                    print(f"- {key}: {type(sample[key]).__name__}")
            else:
                print("データがないためテーブル構造を確認できません")
            
            return True
            
        except Exception as e:
            print(f"✗ データベース接続エラー: {e}")
            return False
    
    async def test_evaluator_method(self, candidate_id=None, resume_file=None):
        """EvaluatorNodeの_get_candidate_infoメソッドをシミュレート"""
        from ai_matching.nodes.base import ResearchState
        
        print("\n=== EvaluatorNodeの_get_candidate_infoメソッドをシミュレート ===")
        
        # ResearchStateを作成
        state = ResearchState(
            resume="",
            job_memo="",
            job_description=None
        )
        
        # 候補者IDを設定
        if candidate_id:
            state.candidate_id = candidate_id
            print(f"候補者ID '{candidate_id}' を直接設定")
        elif resume_file:
            # レジュメファイルを読み込む
            with open(resume_file, 'r', encoding='utf-8') as f:
                resume_text = f.read()
            
            state.resume = resume_text
            print(f"レジュメファイル '{resume_file}' を読み込み（{len(resume_text)}文字）")
        else:
            print("候補者IDまたはレジュメファイルが必要です")
            return
        
        # _get_candidate_infoメソッドをシミュレート
        try:
            # 候補者IDの特定
            extracted_id = None
            
            # 1. state.candidate_idがある場合
            if hasattr(state, 'candidate_id') and state.candidate_id:
                extracted_id = state.candidate_id
                print(f"state.candidate_idから取得: '{extracted_id}'")
            
            # 2. レジュメから候補者IDを抽出
            elif state.resume:
                # レジュメの最初の行などからIDを探す
                lines = state.resume.strip().split('\n')
                for line in lines[:5]:  # 最初の5行をチェック
                    if 'ID:' in line or 'candidate_id:' in line.lower():
                        extracted_id = line.split(':')[-1].strip()
                        print(f"レジュメから抽出: '{extracted_id}'")
                        break
            
            if not extracted_id:
                print("✗ 候補者IDが見つかりません")
                return "年齢: 不明（候補者IDが見つかりません）"
            
            # Supabaseから候補者情報を取得
            response = self.supabase.table('candidates').select('age, gender, candidate_company, enrolled_company_count').eq('candidate_id', extracted_id).execute()
            
            if response.data and len(response.data) > 0:
                candidate = response.data[0]
                info_parts = []
                
                if candidate.get('age'):
                    info_parts.append(f"年齢: {candidate['age']}歳")
                if candidate.get('gender'):
                    info_parts.append(f"性別: {candidate['gender']}")
                if candidate.get('candidate_company'):
                    info_parts.append(f"現在の所属: {candidate['candidate_company']}")
                if candidate.get('enrolled_company_count'):
                    info_parts.append(f"在籍企業数: {candidate['enrolled_company_count']}社")
                
                result = '\n'.join(info_parts) if info_parts else "年齢: 不明"
                print(f"\n【取得結果】\n{result}")
                return result
            else:
                print("✗ 候補者データが見つかりません")
                return "年齢: 不明（データが見つかりません）"
                
        except Exception as e:
            print(f"✗ エラーが発生しました: {e}")
            return f"年齢: 不明（エラーが発生しました: {e}）"


async def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description='候補者情報デバッグツール')
    parser.add_argument('--id', help='候補者ID')
    parser.add_argument('--resume', help='レジュメファイルのパス')
    parser.add_argument('--list', action='store_true', help='最近の候補者を一覧表示')
    parser.add_argument('--check-db', action='store_true', help='データベース接続確認')
    parser.add_argument('--test-evaluator', action='store_true', help='EvaluatorNodeの_get_candidate_infoメソッドをテスト')
    
    args = parser.parse_args()
    
    debugger = CandidateInfoDebugger()
    
    # データベース接続確認
    if args.check_db:
        await debugger.check_database_connection()
    
    # 候補者一覧表示
    if args.list:
        await debugger.list_recent_candidates()
    
    # 候補者情報取得
    candidate = None
    if args.id:
        candidate = await debugger.get_candidate_info_by_id(args.id)
        debugger.display_candidate_info(candidate)
    elif args.resume:
        candidate = await debugger.get_candidate_info_from_resume(args.resume)
        debugger.display_candidate_info(candidate)
    
    # EvaluatorNodeのメソッドテスト
    if args.test_evaluator:
        await debugger.test_evaluator_method(args.id, args.resume)
    
    # 引数がない場合はヘルプを表示
    if not any([args.id, args.resume, args.list, args.check_db, args.test_evaluator]):
        parser.print_help()


if __name__ == "__main__":
    print("候補者情報デバッグツール")
    print("=" * 50)
    
    # 環境変数の確認
    print("\n環境変数:")
    print(f"SUPABASE_URL: {'設定済み' if os.getenv('SUPABASE_URL') else '未設定'}")
    print(f"SUPABASE_KEY: {'設定済み' if os.getenv('SUPABASE_KEY') else '未設定'}")
    
    asyncio.run(main())