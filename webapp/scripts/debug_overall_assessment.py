#!/usr/bin/env python3
"""
overall_assessment問題の調査スクリプト
データベースから評価結果を取得して分析する
"""
import os
import sys
import json
from datetime import datetime
from collections import Counter

# プロジェクトのルートディレクトリをPythonパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
webapp_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(webapp_dir)
sys.path.append(project_root)

from core.utils.supabase_client import get_supabase_client

def analyze_overall_assessments():
    """overall_assessmentの内容を分析"""
    supabase = get_supabase_client()
    
    # 最新の評価を取得
    response = supabase.table('ai_evaluations').select('*').order('evaluated_at', desc=True).limit(100).execute()
    evaluations = response.data or []
    
    print(f"分析対象: {len(evaluations)}件の評価\n")
    
    # overall_assessmentの内容を集計
    assessment_counter = Counter()
    empty_count = 0
    placeholder_count = 0
    actual_assessments = []
    
    for eval in evaluations:
        assessment = eval.get('overall_assessment', '')
        
        if not assessment:
            empty_count += 1
        elif assessment == '総合的な評価を実施中':
            placeholder_count += 1
        else:
            actual_assessments.append(assessment)
            # 最初の50文字で集計
            assessment_counter[assessment[:50] + '...'] += 1
    
    # 結果を表示
    print(f"=== overall_assessment分析結果 ===")
    print(f"空の値: {empty_count}件")
    print(f"プレースホルダー（総合的な評価を実施中）: {placeholder_count}件")
    print(f"実際の評価: {len(actual_assessments)}件")
    print()
    
    # 実際の評価内容のサンプルを表示
    if actual_assessments:
        print("=== 実際の評価内容サンプル（最新5件） ===")
        for i, assessment in enumerate(actual_assessments[:5], 1):
            print(f"\n{i}. {assessment}")
    
    # raw_responseを分析
    print("\n\n=== raw_response分析 ===")
    raw_response_analysis = analyze_raw_responses(evaluations[:10])  # 最新10件を詳細分析
    
    for i, analysis in enumerate(raw_response_analysis, 1):
        print(f"\n--- 評価 {i} ---")
        print(f"ID: {analysis['id']}")
        print(f"評価日時: {analysis['evaluated_at']}")
        print(f"overall_assessment: {analysis['overall_assessment'][:100]}..." if analysis['overall_assessment'] else "（空）")
        print(f"raw_responseのfinal_judgment:")
        if analysis['final_judgment']:
            for key, value in analysis['final_judgment'].items():
                if isinstance(value, list):
                    print(f"  {key}: {len(value)}項目")
                else:
                    print(f"  {key}: {str(value)[:100]}..." if value else f"  {key}: （空）")

def analyze_raw_responses(evaluations):
    """raw_responseの内容を分析"""
    analyses = []
    
    for eval in evaluations:
        analysis = {
            'id': eval['id'],
            'evaluated_at': eval['evaluated_at'],
            'overall_assessment': eval.get('overall_assessment', ''),
            'final_judgment': None
        }
        
        raw_response = eval.get('raw_response')
        if raw_response:
            try:
                response_data = json.loads(raw_response)
                final_judgment = response_data.get('final_judgment', {})
                analysis['final_judgment'] = final_judgment
            except json.JSONDecodeError:
                analysis['final_judgment'] = None
        
        analyses.append(analysis)
    
    return analyses

def check_parsing_logic():
    """パース処理をテスト"""
    print("\n\n=== パース処理のテスト ===")
    
    # テスト用のLLM応答例
    test_responses = [
        """推奨度: B

判定理由: Python/Django開発5年、AWS環境でのマイクロサービス構築経験3年、決済システム開発実績あり
チームリーダーとして5名規模の開発チームをマネジメント、アジャイル開発手法に精通

強み:
- 必要な技術スキルを全て保有
- チームマネジメント経験が豊富
- 決済システムの実装経験

懸念点:
- 金融業界での経験が不足
- 転職回数がやや多い（3年で3社）

総合評価: 技術力とリーダーシップは申し分なく、即戦力として期待できます。金融業界特有の規制やコンプライアンスについては入社後のキャッチアップが必要ですが、学習意欲が高いため問題ないと判断します。""",
        
        """推奨度: A

判定理由: フルスタックエンジニア10年、React/Node.js専門、B2C向けECサイト月間1000万PV達成
パフォーマンス改善により表示速度を70%向上、売上20%増に貢献

強み:
- フロントエンド・バックエンド両方に精通
- 大規模サービスの運用経験
- ビジネス成果への貢献実績

懸念点:
- マネジメント経験が少ない
- B2B領域の経験不足

総合評価：技術力は非常に高く、ビジネス視点も持ち合わせています。
マネジメント経験は不足していますが、技術リーダーとしての活躍が期待できます。
B2B領域については、技術力の高さから短期間での適応が可能と判断します。"""
    ]
    
    # パース処理を模擬
    for i, response in enumerate(test_responses, 1):
        print(f"\n--- テストケース {i} ---")
        judgment = parse_test_response(response)
        print(f"パース結果:")
        print(f"  recommendation: {judgment['recommendation']}")
        print(f"  overall_assessment: {judgment['overall_assessment'][:50]}..." if judgment['overall_assessment'] else "（空）")

def parse_test_response(text):
    """テスト用のパース処理（reporter.pyの_parse_final_judgmentを模擬）"""
    judgment = {
        'recommendation': 'C',
        'reason': '',
        'strengths': [],
        'concerns': [],
        'overall_assessment': ''
    }
    
    lines = text.strip().split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        # 推奨度
        if line.startswith('推奨度:') or '推奨度:' in line:
            parts = line.split(':', 1)
            if len(parts) > 1:
                rec = parts[1].strip()
                if 'A' in rec:
                    judgment['recommendation'] = 'A'
                elif 'B' in rec:
                    judgment['recommendation'] = 'B'
                elif 'C' in rec:
                    judgment['recommendation'] = 'C'
                elif 'D' in rec:
                    judgment['recommendation'] = 'D'
        
        # 総合評価
        elif ('総合評価' in line) and (':' in line or '：' in line):
            parts = line.split(':', 1) if ':' in line else line.split('：', 1)
            if len(parts) > 1:
                judgment['overall_assessment'] = parts[1].strip()
            current_section = 'overall'
        
        # 総合評価の続き
        elif current_section == 'overall' and line and not line.startswith('-'):
            judgment['overall_assessment'] += ' ' + line
    
    # デフォルト値
    if not judgment['overall_assessment']:
        judgment['overall_assessment'] = '総合的な評価を実施中'
    
    return judgment

if __name__ == '__main__':
    analyze_overall_assessments()
    check_parsing_logic()