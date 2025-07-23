#!/usr/bin/env python3
"""
evaluation_results.jsonにレジュメテキストと求人情報テキストを追加するスクリプト
"""

import json
import csv
import os
import argparse
from pathlib import Path


def load_csv_resumes(csv_path):
    """CSVファイルからレジュメテキストを読み込む"""
    resumes = {}
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            management_number = row.get('management_number', '')
            resume_text = row.get('resumeText', '')
            if management_number and resume_text:
                resumes[management_number] = resume_text
    return resumes


def load_text_file(file_path):
    """テキストファイルの内容を読み込む"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def enrich_json_with_text(json_path, csv_path, output_path=None):
    """JSONファイルにレジュメテキストと求人情報を追加"""
    
    # JSONファイルを読み込む
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # CSVからレジュメテキストを読み込む
    print(f"CSVファイルからレジュメテキストを読み込み中: {csv_path}")
    resumes = load_csv_resumes(csv_path)
    print(f"  {len(resumes)}件のレジュメを読み込みました")
    
    # 求人票と求人メモのテキストを読み込む
    job_desc_path = data.get('job_description_path', '')
    job_memo_path = data.get('job_memo_path', '')
    
    print(f"求人票を読み込み中: {job_desc_path}")
    job_description_text = load_text_file(job_desc_path)
    print(f"  文字数: {len(job_description_text)}")
    
    print(f"求人メモを読み込み中: {job_memo_path}")
    job_memo_text = load_text_file(job_memo_path)
    print(f"  文字数: {len(job_memo_text)}")
    
    # データを更新
    data['job_description'] = job_description_text
    data['job_memo'] = job_memo_text
    
    # 各評価にレジュメテキストを追加
    updated_count = 0
    for evaluation in data.get('evaluations', []):
        management_number = evaluation.get('management_number', '')
        if management_number in resumes:
            evaluation['resume_text'] = resumes[management_number]
            updated_count += 1
        else:
            print(f"  警告: {management_number}のレジュメテキストが見つかりません")
    
    print(f"\n{updated_count}件の評価にレジュメテキストを追加しました")
    
    # 出力ファイルパスを決定
    if output_path is None:
        output_path = json_path.replace('.json', '_with_text.json')
    
    # 更新されたデータを保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n更新されたデータを保存しました: {output_path}")
    
    # 統計情報を表示
    print("\n=== 統計情報 ===")
    print(f"総評価数: {len(data.get('evaluations', []))}")
    print(f"レジュメテキスト追加: {updated_count}")
    print(f"求人票文字数: {len(job_description_text)}")
    print(f"求人メモ文字数: {len(job_memo_text)}")
    
    # サンプル表示
    if data.get('evaluations'):
        sample = data['evaluations'][0]
        if 'resume_text' in sample:
            print(f"\nサンプル（最初の評価）:")
            print(f"  管理番号: {sample.get('management_number', '')}")
            print(f"  レジュメ文字数: {len(sample['resume_text'])}")
            print(f"  レジュメ冒頭: {sample['resume_text'][:100]}...")


def main():
    parser = argparse.ArgumentParser(description='JSONファイルにレジュメテキストを追加')
    parser.add_argument('json_file', help='evaluation_results.jsonファイル')
    parser.add_argument('csv_file', help='レジュメデータを含むCSVファイル')
    parser.add_argument('--output', help='出力ファイル名（省略時は_with_text.jsonを付加）')
    args = parser.parse_args()
    
    # ファイルの存在確認
    if not os.path.exists(args.json_file):
        print(f"エラー: JSONファイルが見つかりません - {args.json_file}")
        return
    
    if not os.path.exists(args.csv_file):
        print(f"エラー: CSVファイルが見つかりません - {args.csv_file}")
        return
    
    # エンリッチメント実行
    enrich_json_with_text(args.json_file, args.csv_file, args.output)


if __name__ == "__main__":
    main()