"""
DeepResearch アルゴリズムを使用した採用マッチングシステム
評価→不足情報特定→検索のサイクルで候補者を評価
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import google.generativeai as genai
from dataclasses import dataclass, asdict
import time


@dataclass
class EvaluationResult:
    """評価結果のデータ構造"""
    score: int  # 0-100
    confidence: str  # 低/中/高
    strengths: List[str]
    concerns: List[str]
    summary: str


@dataclass
class InformationGap:
    """不足情報のデータ構造"""
    info_type: str
    query: str
    importance: str  # 高/中/低


@dataclass
class CycleResult:
    """各サイクルの結果"""
    cycle_number: int
    evaluation: EvaluationResult
    missing_info: List[InformationGap]
    search_results: Dict[str, Dict]


class DeepResearchMatcher:
    def __init__(self, gemini_api_key: str, max_cycles: int = 3):
        """
        初期化
        
        Args:
            gemini_api_key: Gemini API キー
            max_cycles: 最大サイクル数（デフォルト3）
        """
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.max_cycles = max_cycles
        
    def load_file(self, filepath: str) -> str:
        """ファイルからテキストを読み込む"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def match_candidate(
        self, 
        resume_file: str, 
        job_description_file: str, 
        job_memo_file: str
    ) -> Dict:
        """
        候補者マッチングを実行
        
        Args:
            resume_file: レジュメファイルのパス
            job_description_file: 求人票ファイルのパス
            job_memo_file: 求人メモファイルのパス
            
        Returns:
            最終評価結果
        """
        # ファイル読み込み
        print("=== ファイル読み込み ===")
        context = {
            'resume': self.load_file(resume_file),
            'job_description': self.load_file(job_description_file),
            'job_memo': self.load_file(job_memo_file),
            'additional_info': {}
        }
        print(f"レジュメ: {len(context['resume'])}文字")
        print(f"求人票: {len(context['job_description'])}文字")
        print(f"求人メモ: {len(context['job_memo'])}文字")
        
        evaluation_history = []
        
        # 評価サイクル実行
        for cycle in range(self.max_cycles):
            print(f"\n{'='*50}")
            print(f"=== サイクル {cycle + 1}/{self.max_cycles} ===")
            print('='*50)
            
            # 1. 評価
            print("\n[Step 1] 現在の情報で評価中...")
            evaluation = self._evaluate(context, evaluation_history)
            print(f"スコア: {evaluation.score}/100 (確信度: {evaluation.confidence})")
            print(f"サマリー: {evaluation.summary}")
            
            # 2. 不足情報の特定
            print("\n[Step 2] 不足情報を特定中...")
            missing_info = self._identify_gaps(evaluation, context)
            print(f"不足情報: {len(missing_info)}件")
            
            if not missing_info:
                print("✓ 十分な情報が揃いました")
                evaluation_history.append(
                    CycleResult(cycle + 1, evaluation, [], {})
                )
                break
            
            # 不足情報を表示
            for i, gap in enumerate(missing_info, 1):
                print(f"  {i}. {gap.info_type} (重要度: {gap.importance})")
            
            # 3. 検索（シミュレーション）
            print("\n[Step 3] 情報を検索中...")
            search_results = self._search_information(missing_info)
            context['additional_info'].update(search_results)
            
            # 履歴に追加
            evaluation_history.append(
                CycleResult(cycle + 1, evaluation, missing_info, search_results)
            )
            
            # API制限対策
            time.sleep(2)
        
        # 最終判定
        print(f"\n{'='*50}")
        print("=== 最終判定 ===")
        print('='*50)
        final_judgment = self._generate_final_judgment(evaluation_history, context)
        
        return {
            'final_judgment': final_judgment,
            'evaluation_history': [asdict(h) for h in evaluation_history],
            'total_cycles': len(evaluation_history)
        }
    
    def _evaluate(self, context: Dict, history: List[CycleResult]) -> EvaluationResult:
        """現在の情報で候補者を評価"""
        
        # 追加情報のフォーマット
        additional_info_text = ""
        if context['additional_info']:
            additional_info_text = "\n【追加収集情報】\n"
            for info_type, info in context['additional_info'].items():
                additional_info_text += f"\n■ {info_type}\n{info['summary']}\n"
        
        # 評価履歴のフォーマット
        history_text = ""
        if history:
            history_text = "\n【これまでの評価経緯】\n"
            for h in history:
                history_text += f"\nサイクル{h.cycle_number}: スコア{h.evaluation.score} (確信度:{h.evaluation.confidence})\n"
        
        prompt = f"""
以下の情報を基に候補者を評価してください。

【候補者レジュメ】
{context['resume']}

【求人票】
{context['job_description']}

【求人メモ】
{context['job_memo']}
{additional_info_text}
{history_text}

以下の形式で評価してください：
1. 適合度スコア: [0-100の整数]
2. 確信度: [低/中/高]
3. 主な強み: [箇条書きで3つまで]
4. 主な懸念点: [箇条書きで3つまで]
5. 評価サマリー: [1-2文で総合評価]

形式例：
適合度スコア: 75
確信度: 中
主な強み:
- 財務経験10年以上
- ERPシステム導入経験
- チームマネジメント経験
主な懸念点:
- クラウドシステム経験なし
- 英語力が不明
- グローバル経験が限定的
評価サマリー: 基本的な要件は満たしているが、クラウドシステムとグローバル経験の面で懸念がある。
"""
        
        response = self.model.generate_content(prompt)
        return self._parse_evaluation(response.text)
    
    def _identify_gaps(self, evaluation: EvaluationResult, context: Dict) -> List[InformationGap]:
        """評価の確信度を上げるために必要な情報を特定"""
        
        # すでに収集済みの情報
        collected_info = list(context['additional_info'].keys())
        
        prompt = f"""
現在の評価結果：
- 適合度スコア: {evaluation.score}
- 確信度: {evaluation.confidence}
- 懸念点: {', '.join(evaluation.concerns)}

すでに収集済みの情報：
{collected_info}

より確実な判断を行うために必要な追加情報を特定してください。
ただし、すでに収集済みの情報と重複しないようにしてください。

必要な情報を最大3つ、以下の形式でリストしてください：

情報1:
種類: [具体的に何を知りたいか]
検索クエリ: [Web検索用のクエリ]
重要度: [高/中/低]

情報2:
種類: [具体的に何を知りたいか]
検索クエリ: [Web検索用のクエリ]
重要度: [高/中/低]

確信度が「高」で、スコアが明確（80以上または40以下）の場合は、
「追加情報は不要です」と回答してください。
"""
        
        response = self.model.generate_content(prompt)
        return self._parse_gaps(response.text)
    
    def _search_information(self, missing_info: List[InformationGap]) -> Dict[str, Dict]:
        """不足情報をWeb検索で収集（シミュレーション）"""
        
        search_results = {}
        
        for info in missing_info[:2]:  # 最大2件まで
            # 実際の実装ではここでWeb検索APIを呼び出す
            # 今回はシミュレーション
            print(f"  検索中: {info.query}")
            
            # Geminiに検索結果のシミュレーションを生成してもらう
            prompt = f"""
以下の検索クエリに対する検索結果の要約をシミュレートしてください：

検索クエリ: {info.query}
情報の種類: {info.info_type}

採用評価に役立つ情報を含む、現実的な検索結果の要約を200文字程度で生成してください。
"""
            
            response = self.model.generate_content(prompt)
            
            search_results[info.info_type] = {
                'query': info.query,
                'summary': response.text.strip(),
                'sources': ['シミュレートされた検索結果']
            }
            
            time.sleep(1)  # API制限対策
        
        return search_results
    
    def _generate_final_judgment(self, history: List[CycleResult], context: Dict) -> Dict:
        """全サイクルの情報を統合して最終判定"""
        
        # 評価の推移をフォーマット
        evaluation_journey = ""
        for h in history:
            evaluation_journey += f"\nサイクル{h.cycle_number}:\n"
            evaluation_journey += f"  スコア: {h.evaluation.score} (確信度: {h.evaluation.confidence})\n"
            evaluation_journey += f"  強み: {', '.join(h.evaluation.strengths[:2])}\n"
            evaluation_journey += f"  懸念: {', '.join(h.evaluation.concerns[:2])}\n"
            if h.search_results:
                evaluation_journey += f"  追加情報: {len(h.search_results)}件収集\n"
        
        prompt = f"""
{len(history)}回の評価サイクルを経て、以下の情報が得られました：

【評価の推移】
{evaluation_journey}

【最終的な評価】
スコア: {history[-1].evaluation.score}
確信度: {history[-1].evaluation.confidence}

最終判定を以下の形式で行ってください：

推奨度: [A/B/C/D]
※A=強く推奨(80-100), B=推奨(60-79), C=要検討(40-59), D=推奨しない(0-39)

判定理由:
- 主な強み（3つ）
- 主な懸念点（2つ）
- 総合評価（2-3文）

面接での確認推奨事項:
- [具体的な確認事項を3つ]
"""
        
        response = self.model.generate_content(prompt)
        return self._parse_final_judgment(response.text)
    
    def _parse_evaluation(self, text: str) -> EvaluationResult:
        """評価結果のパース"""
        lines = text.strip().split('\n')
        
        score = 50  # デフォルト
        confidence = "中"
        strengths = []
        concerns = []
        summary = ""
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if '適合度スコア:' in line:
                try:
                    score = int(line.split(':')[1].strip())
                except:
                    score = 50
            elif '確信度:' in line:
                confidence = line.split(':')[1].strip()
            elif '主な強み:' in line:
                current_section = 'strengths'
            elif '主な懸念点:' in line:
                current_section = 'concerns'
            elif '評価サマリー:' in line:
                summary = line.split(':', 1)[1].strip()
                current_section = 'summary'
            elif line.startswith('- ') and current_section == 'strengths':
                strengths.append(line[2:])
            elif line.startswith('- ') and current_section == 'concerns':
                concerns.append(line[2:])
            elif current_section == 'summary' and line:
                summary += ' ' + line
        
        return EvaluationResult(score, confidence, strengths, concerns, summary)
    
    def _parse_gaps(self, text: str) -> List[InformationGap]:
        """不足情報のパース"""
        if '追加情報は不要' in text:
            return []
        
        gaps = []
        lines = text.strip().split('\n')
        
        current_info = {}
        for line in lines:
            line = line.strip()
            if line.startswith('情報'):
                if current_info and all(k in current_info for k in ['type', 'query', 'importance']):
                    gaps.append(InformationGap(
                        current_info['type'],
                        current_info['query'],
                        current_info['importance']
                    ))
                current_info = {}
            elif '種類:' in line:
                current_info['type'] = line.split(':', 1)[1].strip()
            elif '検索クエリ:' in line:
                current_info['query'] = line.split(':', 1)[1].strip()
            elif '重要度:' in line:
                current_info['importance'] = line.split(':', 1)[1].strip()
        
        # 最後の情報を追加
        if current_info and all(k in current_info for k in ['type', 'query', 'importance']):
            gaps.append(InformationGap(
                current_info['type'],
                current_info['query'],
                current_info['importance']
            ))
        
        return gaps
    
    def _parse_final_judgment(self, text: str) -> Dict:
        """最終判定のパース"""
        lines = text.strip().split('\n')
        
        result = {
            'recommendation': 'C',
            'strengths': [],
            'concerns': [],
            'overall_assessment': '',
            'interview_points': []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if '推奨度:' in line:
                grade = line.split(':')[1].strip()
                if grade in ['A', 'B', 'C', 'D']:
                    result['recommendation'] = grade
            elif '主な強み' in line:
                current_section = 'strengths'
            elif '主な懸念点' in line:
                current_section = 'concerns'
            elif '総合評価' in line:
                current_section = 'overall'
            elif '面接での確認推奨事項' in line or '面接' in line:
                current_section = 'interview'
            elif line.startswith('- '):
                content = line[2:].strip()
                if current_section == 'strengths':
                    result['strengths'].append(content)
                elif current_section == 'concerns':
                    result['concerns'].append(content)
                elif current_section == 'interview':
                    result['interview_points'].append(content)
            elif current_section == 'overall' and line:
                result['overall_assessment'] += line + ' '
        
        result['overall_assessment'] = result['overall_assessment'].strip()
        
        return result


def main():
    """メイン実行関数"""
    # 環境変数またはここで直接APIキーを設定
    api_key = os.getenv('GEMINI_API_KEY', 'your-api-key-here')
    
    # マッチャーインスタンス作成
    matcher = DeepResearchMatcher(api_key)
    
    # ファイルパスを指定
    resume_file = 'sample_data/resume.txt'
    job_desc_file = 'sample_data/job_description.txt'
    job_memo_file = 'sample_data/job_memo.txt'
    
    try:
        # マッチング実行
        result = matcher.match_candidate(resume_file, job_desc_file, job_memo_file)
        
        # 結果を表示
        print("\n" + "="*70)
        print("=== マッチング結果 ===")
        print("="*70)
        
        final = result['final_judgment']
        print(f"\n推奨度: {final['recommendation']}")
        print(f"\n強み:")
        for s in final['strengths']:
            print(f"  • {s}")
        print(f"\n懸念点:")
        for c in final['concerns']:
            print(f"  • {c}")
        print(f"\n総合評価:")
        print(f"  {final['overall_assessment']}")
        print(f"\n面接確認事項:")
        for p in final['interview_points']:
            print(f"  • {p}")
        
        # 詳細結果をJSONファイルに保存
        output_file = f"matching_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n詳細結果を保存しました: {output_file}")
        
    except FileNotFoundError as e:
        print(f"エラー: ファイルが見つかりません - {e}")
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    main()