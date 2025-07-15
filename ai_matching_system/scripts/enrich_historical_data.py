#!/usr/bin/env python3
"""
CSVデータからレジュメを読み込み、AI評価を実行するスクリプト
"""

import os
import sys
import json
import csv
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
import argparse

# プロジェクトのルートパスを追加
sys.path.append(str(Path(__file__).parent.parent))

from ai_matching.nodes import SeparatedDeepResearchMatcher


class HistoricalDataEnricher:
    """CSVデータを元にAI評価を実行"""
    
    def __init__(self, gemini_api_key: str, tavily_api_key: str = None):
        self.matcher = SeparatedDeepResearchMatcher(
            gemini_api_key=gemini_api_key,
            tavily_api_key=tavily_api_key
        )
        self.results = []
        self.job_info = {}  # 求人情報を保持
        
    def set_job_info(self, position: str, job_description_path: str, job_memo_path: str):
        """求人情報を設定"""
        self.job_info['position'] = position
        
        # 求人票を読み込み
        with open(job_description_path, 'r', encoding='utf-8') as f:
            self.job_info['job_description'] = f.read()
            
        # 求人メモを読み込み
        with open(job_memo_path, 'r', encoding='utf-8') as f:
            self.job_info['job_memo'] = f.read()
            
        print(f"求人情報を設定しました:")
        print(f"  ポジション: {position}")
        print(f"  求人票: {job_description_path}")
        print(f"  求人メモ: {job_memo_path}")
        
    def evaluate_resume(self, resume_data: dict) -> dict:
        """レジュメを評価"""
        try:
            case_id = resume_data.get('id', 'unknown')
            print(f"\n評価中: Case {case_id}")
            
            # レジュメテキストを取得
            resume_text = resume_data.get('resumeText', '')
            if not resume_text:
                raise ValueError(f"レジュメテキストが空です: Case {case_id}")
            
            # テキストを一時ファイルに保存
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_resume:
                tmp_resume.write(resume_text)
                tmp_resume_path = tmp_resume.name
                
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_job_desc:
                tmp_job_desc.write(self.job_info['job_description'])
                tmp_job_desc_path = tmp_job_desc.name
                
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp_job_memo:
                tmp_job_memo.write(self.job_info['job_memo'])
                tmp_job_memo_path = tmp_job_memo.name
            
            try:
                # AI評価を実行（ファイルパスを使用）
                ai_result = self.matcher.match_candidate(
                    resume_file=tmp_resume_path,
                    job_description_file=tmp_job_desc_path,
                    job_memo_file=tmp_job_memo_path,
                    max_cycles=2  # 既存データ処理は軽めに
                )
            finally:
                # 一時ファイルを削除
                for tmp_file in [tmp_resume_path, tmp_job_desc_path, tmp_job_memo_path]:
                    if os.path.exists(tmp_file):
                        os.unlink(tmp_file)
            
            # 結果を整理
            evaluation_result = {
                "case_id": case_id,
                "position": self.job_info['position'],
                "ai_evaluation": {
                    "recommendation": ai_result['final_judgment']['recommendation'],
                    "score": ai_result['final_score'],
                    "confidence": ai_result['final_confidence'],
                    "reasoning": ai_result['final_judgment']['reason'],
                    "strengths": ai_result['final_judgment']['strengths'],
                    "concerns": ai_result['final_judgment']['concerns'],
                    "overall_assessment": ai_result['final_judgment']['overall_assessment'],
                    "evaluated_at": datetime.now().isoformat()
                }
            }
            
            # 管理番号がある場合は追加
            if 'management_number' in resume_data and resume_data['management_number']:
                evaluation_result['management_number'] = resume_data['management_number']
            
            # クライアント評価がある場合は比較
            if 'client_evaluation' in resume_data and resume_data['client_evaluation']:
                evaluation_result['client_evaluation'] = resume_data['client_evaluation']
                evaluation_result['comparison'] = {
                    "match": resume_data['client_evaluation'] == ai_result['final_judgment']['recommendation'],
                    "client": resume_data['client_evaluation'],
                    "ai": ai_result['final_judgment']['recommendation']
                }
                
                # クライアントコメントがある場合は追加
                if 'client_comment' in resume_data and resume_data['client_comment']:
                    evaluation_result['client_comment'] = resume_data['client_comment']
                
                print(f"  クライアント評価: {resume_data['client_evaluation']}")
                print(f"  AI評価: {ai_result['final_judgment']['recommendation']} (スコア: {ai_result['final_score']})")
                print(f"  一致: {'○' if evaluation_result['comparison']['match'] else '×'}")
            else:
                print(f"  AI評価: {ai_result['final_judgment']['recommendation']} (スコア: {ai_result['final_score']})")
            
            return evaluation_result
            
        except Exception as e:
            print(f"  エラー: {e}")
            import traceback
            traceback.print_exc()
            return {
                "case_id": case_id,
                "position": self.job_info.get('position', ''),
                "ai_evaluation": None,
                "error": str(e)
            }
    
    def evaluate_multiple_resumes(self, resume_list: list, batch_size: int = 5):
        """複数のレジュメを評価"""
        total = len(resume_list)
        print(f"\n=== AI評価開始 ===")
        print(f"総レジュメ数: {total}")
        print(f"バッチサイズ: {batch_size}")
        
        for i in range(0, total, batch_size):
            batch = resume_list[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            print(f"\n--- バッチ {batch_num}/{(total + batch_size - 1) // batch_size} ---")
            
            # バッチ処理（同期的に実行）
            batch_results = []
            for resume_data in batch:
                result = self.evaluate_resume(resume_data)
                batch_results.append(result)
            self.results.extend(batch_results)
            
            # 進捗表示
            processed = min(i + batch_size, total)
            print(f"\n進捗: {processed}/{total} ({processed * 100 // total}%)")
            
            # API制限対策で少し待機
            if processed < total:
                import time
                time.sleep(1)
        
        return self.results
    
    def generate_analysis_report(self):
        """分析レポートを生成"""
        if not self.results:
            return None
            
        valid_results = [r for r in self.results if r.get('ai_evaluation')]
        
        report = {
            "summary": {
                "total_cases": len(self.results),
                "successfully_evaluated": len(valid_results),
                "failed": len(self.results) - len(valid_results)
            },
            "match_analysis": {
                "total_matches": sum(1 for r in valid_results if r['comparison']['match']),
                "match_rate": sum(1 for r in valid_results if r['comparison']['match']) / len(valid_results) if valid_results else 0
            },
            "recommendation_distribution": {},
            "position_analysis": {},
            "mismatch_patterns": []
        }
        
        # 推奨度の分布
        for grade in ['A', 'B', 'C', 'D']:
            ai_count = sum(1 for r in valid_results if r['ai_evaluation']['recommendation'] == grade)
            # client_evaluationは文字列として保存されている場合とオブジェクトの場合がある
            client_count = sum(1 for r in valid_results if 
                             (isinstance(r.get('client_evaluation'), str) and r['client_evaluation'] == grade) or
                             (isinstance(r.get('client_evaluation'), dict) and r['client_evaluation'].get('recommendation') == grade))
            report["recommendation_distribution"][grade] = {
                "ai": ai_count,
                "client": client_count
            }
        
        # ポジション別の分析
        positions = {}
        for r in valid_results:
            pos = r.get('position', 'Unknown')
            if pos not in positions:
                positions[pos] = {"total": 0, "matches": 0}
            positions[pos]["total"] += 1
            if r['comparison']['match']:
                positions[pos]["matches"] += 1
        
        for pos, data in positions.items():
            report["position_analysis"][pos] = {
                "total": data["total"],
                "match_rate": data["matches"] / data["total"] if data["total"] > 0 else 0
            }
        
        # ミスマッチパターンの抽出
        mismatches = [r for r in valid_results if r.get('comparison', {}).get('match') == False]
        for r in mismatches[:10]:  # 上位10件
            client_rec = r.get('client_evaluation', '')
            if isinstance(client_rec, dict):
                client_rec = client_rec.get('recommendation', '')
            
            report["mismatch_patterns"].append({
                "position": r.get('position', 'Unknown'),
                "client": client_rec,
                "ai": r['ai_evaluation']['recommendation'],
                "ai_reasoning": r['ai_evaluation']['reasoning']
            })
        
        return report


def save_results_to_csv(results: list, output_path: str):
    """評価結果をCSV形式で保存"""
    with open(output_path, 'w', encoding='utf-8', newline='') as csvfile:
        fieldnames = ['id', 'management_number', 'ai_evaluation', 'reasoning', 'client_evaluation', 'client_comment', 'match']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            row = {
                'id': result.get('case_id', ''),
                'management_number': result.get('management_number', ''),
                'ai_evaluation': '',
                'reasoning': '',
                'client_evaluation': result.get('client_evaluation', ''),
                'client_comment': result.get('client_comment', ''),
                'match': ''
            }
            
            # AI評価結果がある場合
            if result.get('ai_evaluation'):
                row['ai_evaluation'] = result['ai_evaluation'].get('recommendation', '')
                row['reasoning'] = result['ai_evaluation'].get('reasoning', '')
            elif result.get('error'):
                row['ai_evaluation'] = 'ERROR'
                row['reasoning'] = result.get('error', '')
            
            # 一致判定
            if result.get('comparison'):
                row['match'] = '○' if result['comparison']['match'] else '×'
            
            writer.writerow(row)


def load_resume_data_from_csv(csv_path: str) -> list:
    """CSVファイルからレジュメデータを読み込む"""
    resume_list = []
    
    with open(csv_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # 必須フィールド
            if 'id' not in row or 'resumeText' not in row:
                print(f"警告: 必須フィールドが不足しています - {row}")
                continue
                
            resume_data = {
                "id": row['id'],
                "resumeText": row['resumeText'],
            }
            
            # オプションフィールド
            if 'management_number' in row and row['management_number']:
                resume_data['management_number'] = row['management_number']
                
            if 'client_evaluation' in row and row['client_evaluation']:
                resume_data['client_evaluation'] = row['client_evaluation']
                
            if 'client_comment' in row and row['client_comment']:
                resume_data['client_comment'] = row['client_comment']
            
            resume_list.append(resume_data)
    
    print(f"CSVから{len(resume_list)}件のレジュメデータを読み込みました")
    return resume_list


def main():
    # コマンドライン引数の処理
    parser = argparse.ArgumentParser(description='CSVデータからレジュメを評価')
    parser.add_argument('csv_file', help='レジュメ情報を含むCSVファイル')
    parser.add_argument('position', help='ポジション名')
    parser.add_argument('job_description', help='求人票ファイルパス')
    parser.add_argument('job_memo', help='求人メモファイルパス')
    parser.add_argument('--limit', type=int, help='処理するレジュメ数の上限')
    parser.add_argument('--batch-size', type=int, default=5, help='バッチサイズ')
    parser.add_argument('--output', default='evaluation_results.json', help='出力ファイル名')
    parser.add_argument('--dry-run', action='store_true', help='実行せずに対象を表示')
    args = parser.parse_args()
    
    # APIキーの確認
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        print("エラー: GEMINI_API_KEY環境変数が設定されていません")
        return
    
    tavily_api_key = os.getenv('TAVILY_API_KEY')
    
    # ファイルの存在確認
    if not os.path.exists(args.csv_file):
        print(f"エラー: CSVファイルが見つかりません - {args.csv_file}")
        return
    if not os.path.exists(args.job_description):
        print(f"エラー: 求人票ファイルが見つかりません - {args.job_description}")
        return
    if not os.path.exists(args.job_memo):
        print(f"エラー: 求人メモファイルが見つかりません - {args.job_memo}")
        return
    
    # エンリッチャーの初期化
    enricher = HistoricalDataEnricher(gemini_api_key, tavily_api_key)
    
    # 求人情報の設定
    enricher.set_job_info(args.position, args.job_description, args.job_memo)
    
    # CSVからレジュメデータを読み込み
    resume_list = load_resume_data_from_csv(args.csv_file)
    
    # 制限がある場合
    if args.limit:
        resume_list = resume_list[:args.limit]
    
    # ドライラン
    if args.dry_run:
        print(f"\n=== ドライラン ===")
        print(f"処理対象: {len(resume_list)}件のレジュメ")
        for i, resume in enumerate(resume_list[:5]):
            resume_preview = resume.get('resumeText', '')[:50] + '...' if len(resume.get('resumeText', '')) > 50 else resume.get('resumeText', '')
            print(f"{i+1}. ID: {resume.get('id', 'unknown')} - {resume_preview}")
        if len(resume_list) > 5:
            print(f"... 他 {len(resume_list) - 5}件")
        return
    
    # 評価実行
    results = enricher.evaluate_multiple_resumes(resume_list, batch_size=args.batch_size)
    
    # 結果の保存
    output_data = {
        "evaluated_at": datetime.now().isoformat(),
        "position": args.position,
        "job_description_path": args.job_description,
        "job_memo_path": args.job_memo,
        "total_resumes": len(results),
        "evaluations": results
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n評価結果を {args.output} に保存しました")
    
    # CSV出力（レポート生成前に実行）
    csv_file = args.output.replace('.json', '_results.csv')
    save_results_to_csv(results, csv_file)
    print(f"\n評価結果CSVを {csv_file} に保存しました")
    
    # 分析レポートの生成
    try:
        report = enricher.generate_analysis_report()
        if report:
            print("\n=== 分析レポート ===")
            print(f"総レジュメ数: {report['summary']['total_cases']}")
            print(f"成功: {report['summary']['successfully_evaluated']}")
            
            if report['match_analysis']['match_rate'] > 0:
                print(f"一致率: {report['match_analysis']['match_rate']:.1%}")
                
                print("\n推奨度分布:")
                for grade in ['A', 'B', 'C', 'D']:
                    ai = report['recommendation_distribution'][grade]['ai']
                    client = report['recommendation_distribution'][grade]['client']
                    print(f"  {grade}: AI={ai}, クライアント={client}")
            
            # レポートも保存
            report_file = args.output.replace('.json', '_report.json')
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\nレポートを {report_file} に保存しました")
    except Exception as e:
        print(f"\nレポート生成中にエラーが発生しました: {e}")
        print("ただし、評価結果とCSVは正常に保存されています。")


if __name__ == "__main__":
    main()