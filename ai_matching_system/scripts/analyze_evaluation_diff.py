#!/usr/bin/env python3
"""
AI評価とクライアント評価の差分を分析するスクリプト
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
import argparse


def grade_to_score(grade):
    """評価グレードを数値に変換"""
    mapping = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
    return mapping.get(grade, 0)


def analyze_evaluation_differences(json_file):
    """評価の差分を分析"""
    # データを読み込み
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    evaluations = data['evaluations']
    
    # 分析結果を格納
    results = []
    
    for eval_data in evaluations:
        if eval_data.get('ai_evaluation') and eval_data.get('client_evaluation'):
            ai_grade = eval_data['ai_evaluation']['recommendation']
            client_grade = eval_data['client_evaluation']
            
            ai_score = grade_to_score(ai_grade)
            client_score = grade_to_score(client_grade)
            
            diff = ai_score - client_score
            
            results.append({
                'case_id': eval_data['case_id'],
                'management_number': eval_data.get('management_number', ''),
                'ai_grade': ai_grade,
                'client_grade': client_grade,
                'ai_score': ai_score,
                'client_score': client_score,
                'diff': diff,
                'diff_type': '過大評価' if diff > 0 else ('過小評価' if diff < 0 else '一致')
            })
    
    # DataFrameに変換
    df = pd.DataFrame(results)
    
    # 統計情報を計算
    stats = {
        'total_cases': len(df),
        'perfect_matches': len(df[df['diff'] == 0]),
        'overestimations': len(df[df['diff'] > 0]),
        'underestimations': len(df[df['diff'] < 0]),
        'mean_diff': df['diff'].mean(),
        'std_diff': df['diff'].std(),
        'max_overestimation': df['diff'].max(),
        'max_underestimation': df['diff'].min()
    }
    
    # 差分の分布
    diff_distribution = df['diff'].value_counts().sort_index().to_dict()
    
    # 評価タイプ別の詳細
    overestimated = df[df['diff'] > 0]
    underestimated = df[df['diff'] < 0]
    
    return df, stats, diff_distribution, overestimated, underestimated


def print_analysis_report(df, stats, diff_distribution, overestimated, underestimated):
    """分析レポートを出力"""
    print("\n" + "="*60)
    print("AI評価とクライアント評価の差分分析レポート")
    print("="*60)
    
    print(f"\n【全体統計】")
    print(f"総ケース数: {stats['total_cases']}")
    print(f"完全一致: {stats['perfect_matches']} ({stats['perfect_matches']/stats['total_cases']*100:.1f}%)")
    print(f"過大評価: {stats['overestimations']} ({stats['overestimations']/stats['total_cases']*100:.1f}%)")
    print(f"過小評価: {stats['underestimations']} ({stats['underestimations']/stats['total_cases']*100:.1f}%)")
    
    print(f"\n【差分の統計値】")
    print(f"平均差分: {stats['mean_diff']:.2f}")
    print(f"標準偏差: {stats['std_diff']:.2f}")
    print(f"最大過大評価: +{stats['max_overestimation']}")
    print(f"最大過小評価: {stats['max_underestimation']}")
    
    print(f"\n【差分の分布】")
    for diff, count in sorted(diff_distribution.items()):
        sign = '+' if diff > 0 else ''
        bar = '█' * count
        print(f"{sign}{diff}: {bar} ({count}件)")
    
    print(f"\n【AIの評価傾向】")
    if stats['mean_diff'] > 0.1:
        print(f"⚠️  AIは全体的に過大評価の傾向があります（平均 +{stats['mean_diff']:.2f}）")
    elif stats['mean_diff'] < -0.1:
        print(f"⚠️  AIは全体的に過小評価の傾向があります（平均 {stats['mean_diff']:.2f}）")
    else:
        print(f"✓ AIの評価は概ねバランスが取れています（平均差分 {stats['mean_diff']:.2f}）")
    
    # 過大評価の詳細
    if len(overestimated) > 0:
        print(f"\n【過大評価のケース】（AIが甘い評価）")
        for _, row in overestimated.head(5).iterrows():
            print(f"- {row['case_id']}: AI={row['ai_grade']}, Client={row['client_grade']} (差分: +{row['diff']})")
    
    # 過小評価の詳細
    if len(underestimated) > 0:
        print(f"\n【過小評価のケース】（AIが厳しい評価）")
        for _, row in underestimated.head(5).iterrows():
            print(f"- {row['case_id']}: AI={row['ai_grade']}, Client={row['client_grade']} (差分: {row['diff']})")
    
    # 推奨事項
    print(f"\n【推奨事項】")
    if abs(stats['mean_diff']) > 0.3:
        print("- 評価基準の大幅な調整が必要です")
        if stats['mean_diff'] > 0:
            print("- 必須要件の重要性を高める必要があります")
        else:
            print("- 歓迎要件やポテンシャルの評価を高める必要があります")
    elif stats['perfect_matches'] / stats['total_cases'] < 0.5:
        print("- 個別の評価基準の微調整を推奨します")
    else:
        print("- 現在の評価基準は概ね適切です")


def save_detailed_analysis(df, output_file):
    """詳細な分析結果をCSVで保存"""
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n詳細な分析結果を {output_file} に保存しました")


def main():
    parser = argparse.ArgumentParser(description='AI評価とクライアント評価の差分を分析')
    parser.add_argument('json_file', help='評価結果のJSONファイル')
    parser.add_argument('--output', help='詳細分析結果の出力先CSV', default='evaluation_diff_analysis.csv')
    args = parser.parse_args()
    
    if not Path(args.json_file).exists():
        print(f"エラー: ファイルが見つかりません - {args.json_file}")
        return
    
    # 分析実行
    df, stats, diff_distribution, overestimated, underestimated = analyze_evaluation_differences(args.json_file)
    
    # レポート出力
    print_analysis_report(df, stats, diff_distribution, overestimated, underestimated)
    
    # 詳細結果を保存
    save_detailed_analysis(df, args.output)


if __name__ == "__main__":
    main()