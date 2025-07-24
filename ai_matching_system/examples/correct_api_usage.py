#!/usr/bin/env python3
"""
AI Matching System の正しい使用例
"""

from ai_matching.nodes.orchestrator import SeparatedDeepResearchMatcher
import json

def main():
    # 1. データベースから取得したデータの例
    # job_requirementsテーブルから
    requirement = {
        'title': 'シニアバックエンドエンジニア',
        'job_description': '''【募集背景】
当社は急成長中のFinTechスタートアップです。事業拡大に伴い、
決済システムの開発をリードしていただけるシニアエンジニアを募集しています。

【職務内容】
- 大規模決済システムのアーキテクチャ設計と実装
- マイクロサービスの開発・運用
- チームメンバーの技術指導とコードレビュー
- パフォーマンスチューニングとセキュリティ強化

【必須要件】
- Python開発経験5年以上
- AWSでのシステム構築経験3年以上
- マイクロサービスアーキテクチャの設計・実装経験
- チームリード経験2年以上

【歓迎要件】
- 決済システムの開発経験
- Go言語の実務経験
- セキュリティに関する深い知識
''',  # 実際は4,000文字以上
        'memo': '技術力重視。スタートアップマインドを持った方を求めています。',
        'structured_data': {
            'position': 'シニアバックエンドエンジニア',
            'employment_type': '正社員',
            'work_location': '東京都渋谷区',
            'salary_min': 8000000,
            'salary_max': 12000000,
            'required_skills': [
                'Python開発経験5年以上',
                'AWSでのシステム構築経験3年以上',
                'マイクロサービスアーキテクチャの設計・実装経験',
                'チームリード経験2年以上'
            ],
            'preferred_skills': [
                '決済システムの開発経験',
                'Go言語の実務経験',
                'セキュリティに関する深い知識'
            ],
            'experience_years_min': 5
        }
    }
    
    # candidatesテーブルから
    candidate = {
        'id': 'cand_123456',
        'age': 32,
        'gender': '男性',
        'current_company': '株式会社テクノロジー',
        'enrolled_company_count': 3,
        'resume': '''# 山田太郎
        
## 職歴
### 株式会社テクノロジー（2019年4月〜現在）
- シニアソフトウェアエンジニア
- Pythonを使用したマイクロサービスの開発（5年）
- AWS環境でのシステム構築と運用（4年）
- 5名のチームのテックリード（2年）

## スキル
- Python, Go, JavaScript
- AWS (EC2, RDS, Lambda, ECS)
- Docker, Kubernetes
- マイクロサービスアーキテクチャ
'''
    }
    
    # 2. デバッグ: データを確認
    print("=== データ確認 ===")
    print(f"job_description length: {len(requirement['job_description'])} 文字")
    print(f"job_description preview: {requirement['job_description'][:100]}...")
    print(f"structured_data keys: {list(requirement['structured_data'].keys())}")
    print(f"candidate info: age={candidate['age']}, company={candidate['current_company']}")
    print()
    
    # 3. AI Matching Systemの初期化
    matcher = SeparatedDeepResearchMatcher(
        gemini_api_key="your-gemini-api-key",
        tavily_api_key="your-tavily-api-key",  # オプション
        pinecone_api_key="your-pinecone-api-key"  # オプション
    )
    
    # 4. 正しい呼び出し方法
    result = matcher.match_candidate_direct(
        # レジュメ
        resume_text=candidate['resume'],
        
        # 求人情報（全文を渡す）
        job_description_text=requirement['job_description'],  # ⚠️ titleではない！
        
        # 求人メモ
        job_memo_text=requirement['memo'],
        
        # 候補者基本情報
        candidate_id=candidate['id'],
        candidate_age=candidate['age'],
        candidate_gender=candidate['gender'],
        candidate_company=candidate['current_company'],
        enrolled_company_count=candidate['enrolled_company_count'],
        
        # 構造化データ
        structured_job_data=requirement['structured_data'],
        
        # その他
        max_cycles=3
    )
    
    # 5. 結果の確認
    print("\n=== マッチング結果 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()