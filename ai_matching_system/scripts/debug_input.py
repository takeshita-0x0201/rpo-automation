#!/usr/bin/env python3
"""
入力データのデバッグスクリプト
実際に渡されているデータのサイズと内容を確認
"""

import asyncio
import os
from pathlib import Path
import sys
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from ai_matching.nodes.orchestrator import DeepResearchOrchestrator


async def debug_input_data():
    """入力データをデバッグ"""
    
    # 環境変数を読み込み
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    
    # APIキーの確認
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY not found")
        return
    
    # サンプルデータを読み込み
    sample_dir = project_root / "sample_data"
    
    # ファイルの内容を確認
    print("=== ファイルの内容確認 ===")
    
    resume_path = sample_dir / "resume.txt"
    job_desc_path = sample_dir / "job_description.txt"
    job_memo_path = sample_dir / "job_memo.txt"
    
    with open(resume_path, "r", encoding="utf-8") as f:
        resume = f.read()
        print(f"resume.txt: {len(resume)}文字 ({resume_path.stat().st_size}バイト)")
        print(f"  最初の100文字: {resume[:100]}...")
    
    with open(job_desc_path, "r", encoding="utf-8") as f:
        job_description = f.read()
        print(f"\njob_description.txt: {len(job_description)}文字 ({job_desc_path.stat().st_size}バイト)")
        print(f"  最初の100文字: {job_description[:100]}...")
    
    with open(job_memo_path, "r", encoding="utf-8") as f:
        job_memo = f.read()
        print(f"\njob_memo.txt: {len(job_memo)}文字 ({job_memo_path.stat().st_size}バイト)")
        print(f"  最初の100文字: {job_memo[:100]}...")
    
    # 短いテストデータで実行してみる
    print("\n=== 短いテストデータで実行 ===")
    
    # これが表示されている文字数に近い
    short_job_desc = "Treasury Specialist/ 財務スペシャリスト"  # 約38文字
    short_job_memo = "メルカリグループのTreasuryチームで財務スペシャリストを募集。資金管理、出納業務、業法対応などを担当。"  # 約144文字
    
    print(f"短い求人情報: {len(short_job_desc)}文字")
    print(f"短い求人メモ: {len(short_job_memo)}文字")
    
    # オーケストレーターを初期化
    orchestrator = DeepResearchOrchestrator(
        gemini_api_key=gemini_api_key,
        tavily_api_key=os.getenv("TAVILY_API_KEY")
    )
    
    # 短いデータで実行
    print("\n=== orchestrator.run()を実行（短いデータ） ===")
    try:
        result = await orchestrator.run(
            resume=resume[:500],  # レジュメは一部だけ
            job_description=short_job_desc,
            job_memo=short_job_memo,
            max_cycles=1,
            # 候補者情報を提供
            candidate_age=35,
            candidate_gender="M",
            candidate_company="テスト会社",
            enrolled_company_count=3
        )
        print("実行完了")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 正しいデータで実行
    print("\n\n=== orchestrator.run()を実行（正しいデータ） ===")
    try:
        result = await orchestrator.run(
            resume=resume,
            job_description=job_description,  # 完全なファイル内容
            job_memo=job_memo,  # 完全なファイル内容
            max_cycles=1,
            # 候補者情報を提供
            candidate_age=35,
            candidate_gender="M",
            candidate_company="テスト会社",
            enrolled_company_count=3
        )
        print("実行完了")
    except Exception as e:
        print(f"エラー: {e}")


if __name__ == "__main__":
    asyncio.run(debug_input_data())