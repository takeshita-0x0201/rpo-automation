"""
情報ギャップ分析ノード
"""

from typing import List, Dict
import google.generativeai as genai
import re
from datetime import datetime

from .base import BaseNode, ResearchState, InformationGap
from .score_based_strategy import ScoreBasedSearchStrategy
from ..utils.query_templates import QueryTemplates
from ..utils.contradiction_resolver import ContradictionResolver


class GapAnalyzerNode(BaseNode):
    """評価の不確実性から情報ギャップを特定するノード"""
    
    def __init__(self, api_key: str):
        super().__init__("GapAnalyzer")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.search_strategy = ScoreBasedSearchStrategy()
        self.contradiction_resolver = ContradictionResolver()
    
    async def process(self, state: ResearchState) -> ResearchState:
        """情報ギャップを分析"""
        self.state = "processing"
        
        # 現在の評価を確認
        if not state.current_evaluation:
            print("  警告: 評価結果がありません")
            state.information_gaps = []
            self.state = "completed"
            return state
        
        eval_result = state.current_evaluation
        print(f"  現在の評価を分析: スコア{eval_result.score}, 確信度{eval_result.confidence}")
        
        # スコアベースの戦略を取得
        strategy = self.search_strategy.get_strategy(eval_result.score, eval_result.confidence)
        print(f"  適用戦略: {strategy['name']} (検索必要性: {strategy['should_search']})")
        
        # 既に収集した情報
        collected_info = list(state.search_results.keys())
        if collected_info:
            print(f"  既存の収集情報: {len(collected_info)}件")
        
        # 環境適応性チェックのための情報を抽出
        company_size_checked = any(key in collected_info for key in ["企業規模比較", "環境適応性ギャップ"])
        
        # 最適化されたプロンプト
        prompt = f"""中途採用ギャップ分析の専門家として、理想の候補者（求人要件）と実際の候補者のレジュメから読み取れない「見えないギャップ」を特定し、評価の確信度を高めるための追加情報を提案します。

# 現在の評価状況
- スコア: {eval_result.score}/100
- 確信度: {eval_result.confidence}
- 強み: {', '.join(eval_result.strengths[:2])}
- 懸念: {', '.join(eval_result.concerns[:2])}
- 収集済み情報: {', '.join(collected_info) if collected_info else 'なし'}

# 候補者レジュメ（要約）
{state.resume[:500]}...

# 求人要件
{state.job_description[:300]}...
{state.job_memo[:200]}...

# 分析終了条件（厳格化した評価基準に対応）
- 確信度「高」かつスコア85以上 → 追加情報不要
- スコア95以上 → 追加情報不要（十分高評価）
- スコア20以下かつ確信度「高」→ 追加情報不要（明らかに不適合）
- それ以外は情報収集を継続

※重要：
- スコアが45-80の範囲では、確信度に関わらず少なくとも1つの情報ギャップを特定すること
- 特に環境適応性（企業規模・文化）の確認は、スコア80未満では必須
- 「追加情報不要」の判断は慎重に行い、上記の終了条件を厳密に適用すること

# ギャップ分析の4つの観点
1. 環境適応性ギャップ: 組織規模・文化・働き方の違いによる適応リスク
2. 実務遂行能力ギャップ: 必須スキルの実践的な深さと応用範囲
3. 役割期待値ギャップ: 現職と求人職の責任範囲・権限レベルの差異
4. 市場競争力ギャップ: 候補者の相対的な市場価値と採用可能性

# 必要な追加情報（最大3つ、優先度順）
{"※重要: 環境適応性（企業規模・文化）の確認が未実施の場合、必ず最初に含めること" if not company_size_checked else ""}

※スコアが45-80の範囲の場合：
- 最低1つ、できれば2-3つの情報ギャップを特定してください
- 単に「追加情報不要」とせず、採用判断の確信度を高めるための具体的な情報を提案してください

情報1:
種類: [環境適応性ギャップ/実務遂行能力ギャップ/役割期待値ギャップ/市場競争力ギャップ]
説明: [レジュメから読み取れない具体的な情報ギャップ]
検索クエリ: [具体的な企業名・数値・年号を含む実行可能なクエリ]
重要度: [高/中/低]
理由: [この情報が採用判断にどう影響するか]

# 検索クエリの具体例
環境適応性: "[候補者企業] 従業員数 売上規模 組織文化 働き方"
実務遂行能力: "[必須スキル] [候補者企業] 活用事例 プロジェクト規模"
役割期待値: "[現職役職] から [求人役職] 転職 成功要因 課題"
市場競争力: "[職種] [経験年数] 市場価値 年収相場 [地域] 2024"

# 重要な注意点
- 懸念点で不明と判断された点に関しては調査対象とする
- レジュメに明記されていない「実態」を探る
- 求人の必須要件に関連するギャップを優先
- 具体的で検索可能なクエリを生成
- 個人情報や推測に基づくクエリは避ける"""
        
        print(f"  LLMに情報ギャップ分析を依頼中...")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        # 現在のスコアを一時的に保存（デフォルトギャップ生成用）
        self._current_eval_score = eval_result.score
        
        gaps = self._parse_gaps(response.text)
        print(f"  情報ギャップ分析完了: {len(gaps)}件の不足情報を特定")
        
        # 既存の検索結果に矛盾がある場合は検出
        if state.search_results:
            print(f"  矛盾検出を開始...")
            contradictions = self.contradiction_resolver.detect_contradictions(
                resume_data={'text': state.resume},
                search_results=state.search_results,
                evaluation_text=eval_result.raw_response if eval_result.raw_response else ""
            )
            if contradictions:
                print(f"  {len(contradictions)}件の矛盾を検出")
                # 矛盾解決を優先的な情報ギャップとして追加
                for contradiction in contradictions[:1]:  # 最も重要な矛盾1つを追加
                    gaps.insert(0, InformationGap(
                        info_type="矛盾解決ギャップ",
                        description=f"{contradiction.topic}に関する矛盾情報の確認",
                        search_query=f"{contradiction.topic} 正確な情報 最新 確認",
                        importance="高",
                        rationale=f"{contradiction.source1['name']}と{contradiction.source2['name']}で情報が矛盾しているため確認が必要"
                    ))
        
        # 状態を更新
        state.information_gaps = gaps
        
        # 継続判定（厳格化した基準に対応）
        should_stop = False
        stop_reason = ""
        
        # スコアベースの判定を先に行う
        if 45 <= eval_result.score <= 80:
            # 中間スコアの場合は必ず情報収集を試みる
            if not gaps:
                # ギャップが見つからない場合でも1回は検索を強制
                if state.current_cycle == 0:
                    should_stop = False
                    stop_reason = "中間スコアのため初回検索を実行"
                else:
                    should_stop = True
                    stop_reason = "追加情報なし（検索済み）"
            else:
                should_stop = False
                stop_reason = "情報ギャップ発見、検索継続"
        elif eval_result.score >= 95:
            should_stop = True
            stop_reason = "スコアが95以上（十分高評価）"
        elif eval_result.score <= 20 and eval_result.confidence == "高":
            should_stop = True
            stop_reason = "スコアが20以下かつ確信度高（明らかに不適合）"
        elif eval_result.confidence == "高" and eval_result.score >= 85:
            should_stop = True
            stop_reason = "確信度高かつスコア85以上"
        elif not gaps:
            should_stop = True
            stop_reason = "追加情報不要"
        
        if should_stop:
            state.should_continue = False
            print(f"  継続判定: 終了（理由: {stop_reason}）")
        else:
            print(f"  継続判定: 続行（追加情報収集が必要）")
        
        self.state = "completed"
        return state
    
    def _parse_gaps(self, text: str) -> List[InformationGap]:
        """LLMの出力を情報ギャップにパース"""
        gaps = []
        
        if "追加情報不要" in text:
            # スコアが中間範囲の場合はデフォルトギャップを生成
            if hasattr(self, '_current_eval_score') and 45 <= self._current_eval_score <= 80:
                print("  中間スコアのためデフォルトギャップを生成")
                return self._generate_default_gaps()
            return gaps
        
        # 情報ブロックを分割
        blocks = text.strip().split('\n\n')
        
        current_gap = {}
        for line in text.strip().split('\n'):
            line = line.strip()
            
            if line.startswith("情報") and ":" in line:
                # 新しい情報ブロック開始
                if current_gap and all(k in current_gap for k in ['type', 'description', 'query', 'importance', 'rationale']):
                    gaps.append(InformationGap(
                        info_type=current_gap['type'],
                        description=current_gap['description'],
                        search_query=current_gap['query'],
                        importance=current_gap['importance'],
                        rationale=current_gap['rationale']
                    ))
                current_gap = {}
            elif line.startswith("種類:"):
                current_gap['type'] = line.split(':', 1)[1].strip()
            elif line.startswith("説明:"):
                current_gap['description'] = line.split(':', 1)[1].strip()
            elif line.startswith("検索クエリ:"):
                raw_query = line.split(':', 1)[1].strip()
                # テンプレートを使用してクエリを改善
                current_gap['query'] = self._enhance_query(raw_query, current_gap)
            elif line.startswith("重要度:"):
                imp = line.split(':', 1)[1].strip()
                if imp in ["高", "中", "低"]:
                    current_gap['importance'] = imp
            elif line.startswith("理由:"):
                current_gap['rationale'] = line.split(':', 1)[1].strip()
        
        # 最後のギャップを追加
        if current_gap and all(k in current_gap for k in ['type', 'description', 'query', 'importance', 'rationale']):
            gaps.append(InformationGap(
                info_type=current_gap['type'],
                description=current_gap['description'],
                search_query=current_gap['query'],
                importance=current_gap['importance'],
                rationale=current_gap['rationale']
            ))
        
        # 最大3つに制限
        return gaps[:3]
    
    def _generate_default_gaps(self) -> List[InformationGap]:
        """中間スコアの場合のデフォルトギャップを生成"""
        # コンテキストから企業名やスキルを抽出
        context = self._extract_context_from_state()
        
        default_gaps = []
        
        # 環境適応性ギャップ
        if context.get("company_name"):
            query = QueryTemplates.generate_company_query(
                context["company_name"], "企業文化", datetime.now().year
            )
        else:
            query = "企業規模 従業員数 組織文化 働き方 比較"
            
        default_gaps.append(InformationGap(
            info_type="環境適応性ギャップ",
            description="候補者の現在の企業と求人企業の規模・文化の違いによる適応リスク",
            search_query=query,
            importance="高",
            rationale="組織規模や文化の違いは採用後の定着率に大きく影響するため"
        ))
        
        # 実務遂行能力ギャップ
        if context.get("key_skill"):
            query = QueryTemplates.generate_skill_query(
                context["key_skill"], context.get("industry", "")
            )
        else:
            query = "実務経験 プロジェクト規模 技術スタック 活用事例"
            
        default_gaps.append(InformationGap(
            info_type="実務遂行能力ギャップ",
            description="必須スキルの実践的な深さと実際のプロジェクト規模での適用経験",
            search_query=query,
            importance="高",
            rationale="レジュメに記載されたスキルの実践的な深さを確認するため"
        ))
        
        return default_gaps[:2]  # 最大2つのデフォルトギャップ
    
    def _enhance_query(self, raw_query: str, gap_context: Dict) -> str:
        """生のクエリをテンプレートを使用して改善"""
        # 企業名を抽出
        company_match = re.search(r'(株式会社[\w]+|[\w]+株式会社)', raw_query)
        if company_match and gap_context.get('type') == '環境適応性ギャップ':
            return QueryTemplates.generate_company_query(
                company_match.group(1), "企業文化"
            )
        
        # スキル名を抽出
        skill_keywords = ["Python", "Java", "JavaScript", "営業", "マネジメント", "マーケティング"]
        for skill in skill_keywords:
            if skill in raw_query and gap_context.get('type') == '実務遂行能力ギャップ':
                return QueryTemplates.generate_skill_query(skill)
        
        # デフォルトは元のクエリに年号を追加
        if str(datetime.now().year) not in raw_query:
            raw_query += f" {datetime.now().year}"
            
        return raw_query
    
    def _extract_context_from_state(self) -> Dict:
        """現在の状態からコンテキスト情報を抽出"""
        context = {}
        
        # stateから企業名、スキル、業界などを抽出するロジック
        # これは実際のstateの内容に基づいて実装する必要がある
        
        return context