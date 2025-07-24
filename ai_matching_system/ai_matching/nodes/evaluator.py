"""
候補者評価ノード
"""

import os
from typing import Dict, List, Optional
import google.generativeai as genai
from supabase import create_client, Client
from dotenv import load_dotenv

from .base import BaseNode, ResearchState, EvaluationResult, ScoreDetail
from ..utils.semantic_guards import SemanticGuards


class EvaluatorNode(BaseNode):
    """候補者を評価するノード"""
    
    def __init__(self, api_key: str, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        super().__init__("Evaluator")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Supabaseクライアントの初期化
        self.supabase_client = None
        
        # dotenvから環境変数を読み込む（親ディレクトリの.envも探す）
        from dotenv import load_dotenv
        from pathlib import Path
        
        # 現在のディレクトリから上位に遡って.envを探す
        current_path = Path(__file__).resolve()
        for parent in [current_path.parent, current_path.parent.parent, current_path.parent.parent.parent, current_path.parent.parent.parent.parent]:
            env_path = parent / '.env'
            if env_path.exists():
                print(f"[EvaluatorNode初期化] .envファイルを発見: {env_path}")
                load_dotenv(env_path)
                break
        else:
            # 見つからない場合はデフォルトの動作
            load_dotenv()
        
        # デバッグ: 環境変数の状態を確認
        env_url = os.getenv("SUPABASE_URL")
        env_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        print(f"[EvaluatorNode初期化] SUPABASE_URL from env: {env_url is not None}")
        print(f"[EvaluatorNode初期化] SUPABASE_KEY/ANON_KEY from env: {env_key is not None}")
        
        if supabase_url and supabase_key:
            print(f"[EvaluatorNode初期化] 引数から Supabase設定を使用")
            self.supabase_client = create_client(supabase_url, supabase_key)
        elif env_url and env_key:
            print(f"[EvaluatorNode初期化] 環境変数から Supabase設定を使用")
            self.supabase_client = create_client(env_url, env_key)
        else:
            print(f"[EvaluatorNode初期化] Supabase設定が見つかりません")
    
    async def process(self, state: ResearchState) -> ResearchState:
        """候補者を現在の情報で評価"""
        self.state = "processing"
        
        print(f"  候補者評価を開始（サイクル{state.current_cycle}）")
        
        # 追加情報のフォーマット
        additional_info = self._format_additional_info(state.search_results)
        if additional_info:
            print(f"  追加情報を含めて評価: {len(state.search_results)}件の検索結果")
        
        # 評価履歴のフォーマット
        history_text = self._format_history(state.evaluation_history)
        if state.evaluation_history:
            print(f"  過去の評価履歴を考慮: {len(state.evaluation_history)}サイクル分")
        
        # RAG洞察のフォーマット
        rag_insights_text = self._format_rag_insights(state)
        if hasattr(state, 'rag_insights') and state.rag_insights:
            print(f"  類似ケースの洞察を活用")
        
        # 候補者情報を取得
        candidate_info = await self._get_candidate_info(state)
        
        # セマンティックガードによる事前チェック
        guard_insights = self._apply_semantic_guards(state)
        
        # 構造化データの存在チェック
        has_structured_job_data = hasattr(state, 'structured_job_data') and state.structured_job_data
        structured_job_data_text = self._format_structured_job_data(state) if has_structured_job_data else ''
        
        has_structured_resume_data = hasattr(state, 'structured_resume_data') and state.structured_resume_data
        structured_resume_data_text = self._format_structured_resume_data(state) if has_structured_resume_data else ''
        
        # 最適化されたプロンプト
        prompt = f"""あなたは経験豊富な採用コンサルタントです。
クライアント企業の採用成功のため、候補者を適切に評価してください。

# 重要な評価ルール
1. **構造化データを最優先で使用**
   - 求人の構造化データ（必須スキル、歓迎スキル、給与レンジ等）がある場合は、それを基準に評価
   - 構造化データで判断できる項目は、求人票の自由記述（job_description）より優先
2. **求人票の自由記述は補助的に使用**
   - 構造化データに含まれない要件の確認
   - 構造化データの解釈が必要な場合の補足情報
   - 企業文化や詳細な業務内容の理解

# 入力データ
## 候補者レジュメ（原文）
{state.resume}

## 候補者情報
{candidate_info}

{structured_resume_data_text}

{structured_job_data_text}

## 求人票（自由記述）
※構造化データで判断できない項目の参照用
{state.job_description}

## 追加情報
{state.job_memo}

{additional_info}
{history_text}
{rag_insights_text}
{guard_insights}

# 【最重要】必須要件と歓迎要件の区別
## 必須要件（required_skills / 必須経験）
- 候補者が持っていなければならない要件
- 不足している場合は懸念点として記載する
- 評価の45%を占める

## 歓迎要件（preferred_skills / 歓迎経験 / 業界経験）
- あればプラスになる要件
- 不足していても懸念点には記載しない
- 評価の15%を占める（純粋な加点要素）
- 特定業界の経験は多くの場合歓迎要件

【重要】「飲食、物流、小売業界の経験」「新規顧客獲得経験」などが歓迎要件の場合、
それらがなくても絶対に懸念点として記載しない

# 評価方針（改善版 - セマンティック理解重視）
1. 必須要件は業務本質を理解した上で評価する
   - 直接的な記載がなくても、実質的に同等の経験があれば認める
   - 例：「法人営業」の記載がなくても、B2B取引の実績があれば営業経験として評価
2. 類似経験・関連スキルを適切に評価する
   - 同一業界内での隣接領域：高い評価（80-90%）
   - 異業界でも本質的に同じスキル：中程度の評価（60-80%）
   - 間接的に関連する経験：限定的に評価（40-60%）
3. レジュメから読み取れる能力・実績を総合的に判断
   - 明示的な記載を重視しつつ、文脈から合理的に推測できる内容も考慮
   - ただし、根拠のない楽観的な推測は避ける
4. 歓迎要件の充足は明確な加点要素として評価する
5. 求人メモから読み取れる「本当に求める人材像」を重視する
6. 経験の時期による評価調整（緩和）
   - 直近3年以内：100%
   - 3-5年前：80%（20%減点）
   - 5-10年前：60%（40%減点）
   - 10年以上前：40%（60%減点）
7. キャリアチェンジは文脈に応じて評価
   - 関連性のある転職：ペナルティなし
   - スキル転用可能な異動：限定的な減点（10-20%）
8. 業務内容は総合的に判断
   - 具体的な記載があれば高評価
   - 概要のみでも業界標準的な業務なら中程度の評価

# 評価基準と配点（目安）
## 必須要件（45%）
- **構造化データの必須スキル（required_skills）を最優先で評価**
- 構造化データがない場合のみ、求人票の「求める経験・スキル」「必須」項目を使用
- 直接的な経験が明確に確認できる場合：満点
- 類似経験での代替（以下の場合のみ認める）：最大50%の得点
  * 同一業界内での隣接領域の経験
  * 使用技術・ツールが70%以上一致
  * 業務プロセスが実質的に同等
- 経験が不明確・推測が必要な場合：最大30%の得点
- 完全に欠如している場合：該当項目は0点

### 必須要件不足のペナルティ（追加減点）
- 必須要件を1つでも完全に欠如：総合スコアから-15点
- 必須要件の50%以上が不明確/欠如：総合スコアから-25点
- 中核的な必須要件（役職・資格等）の欠如：総合スコアから-30点

### 重要：経験の時期による調整（緩和）
- 直近3年以内の経験：満点（100%）
- 3-5年前の経験：20%減点（80%）
- 5-10年前の経験：40%減点（60%）
- 10年以上前の経験：60%減点（40%）
- 関連性のあるキャリアチェンジ：減点なし
- スキル転用可能な異動：10-20%減点
- 業務内容の記載が概要レベル：10%減点（業界標準的な業務の場合）

## 実務遂行能力（25%）
- 業務を遂行できる実質的な能力
- 過去の実績・成果から判断
- 具体的な数値や成果があれば加点

## 歓迎要件（15%）【純粋な加点要素】
- **構造化データの歓迎スキル（preferred_skills）を最優先で評価**
- 構造化データがない場合のみ、求人票の「歓迎する経験・スキル」「尚可」項目を使用
- 1つ充足ごとに加点（最大15%）
- 特に重要な歓迎要件は2倍の加点
- 必須要件を補強する歓迎要件は追加加点
- ※歓迎要件を満たしていなくても減点はしない
- ※歓迎要件の不足は懸念点に含めない

## 組織適合性（10%）
- 過去の所属企業と求人企業の類似性（業界、規模、文化）
- 実際の転職実績（成功した環境変化の経験）
- 企業規模適応性（規模差による減点：2段階差で-5点、3段階以上で-10点）
- ※注意：ポテンシャルや適応可能性ではなく、過去の実績から判断

## 突出した経歴・実績（5%）
- 必須要件の不足を補う「尖った経歴」（ボーナス要素）
- 求人に関連する分野での業界注目度（関連分野の有名企業での実績）
- 求人に活かせる希少経験（関連事業の立ち上げ、類似領域でのターンアラウンド等）
- 求人に貢献できるユニークな経歴（求人に活かせる異業種経験等）
- 求人領域での圧倒的成果（関連分野での売上○億円達成、ユーザー○万人獲得等）
- ※重要：求人との関連性がない経歴は評価しない。求人に活かせる希少な経歴のみ加点

# スコアリング指針（厳格基準）
- 85-100点: 必須要件を100%充足＋歓迎要件3個以上＋直近3年の実績
- 70-84点: 必須要件を90%以上充足＋歓迎要件1個以上
- 60-69点: 必須要件を70%以上充足、または突出した経歴で補完
- 40-59点: 必須要件の充足が70%未満
- 0-39点: 必須要件の半数以上が未充足

※重要：必須要件が不明確・推測が必要な場合は、そのことを理由に10-20点減点

※重要：突出した経歴（5%）は本当に希少な場合のみ加点。通常は必須要件と実務能力で評価

# バランスの取れた評価実施ルール
1. 評価の基本姿勢：
   - レジュメの記載内容を基本としつつ、文脈から合理的に読み取れる内容も考慮
   - 業務の本質的な類似性を理解し、適切に評価
   - 根拠のない楽観的な推測は避けるが、論理的な推論は許容

2. セマンティック理解の適用：
   - 用語の違いではなく、業務内容の本質で判断
   - 営業経験の判断例：
     * 「法人営業」≈「B2B営業」≈「企業向け営業」≈「アカウント営業」
     * 「担当案件」「主担当」「クライアント対応」＋ 売上/契約の文脈 = 営業要素あり
     * 「新規開拓」「既存顧客フォロー」「提案」「受注」= 営業活動
   - 財務・経理の関連性：
     * 「経理」経験は「財務」要件の一部として評価可能
     * 「管理会計」「予算管理」は経営企画要素として評価
   - マネジメント経験の判断：
     * 「プロジェクト管理」「チームリード」「統括」= マネジメント要素
     * 「作業者の進捗管理」「レクチャー」「フォロー」= 実質的なマネジメント

3. 評価の透明性：
   - 必須要件との合致度を明確に示す
   - 類似経験で評価した場合はその旨を明記
   - 減点理由は具体的に説明

# 出力フォーマット
適合度スコア: [0-100の整数]
確信度: [低/中/高]

## スコア内訳
### 必須要件（45点満点）
- [構造化データの各必須スキル項目]: [点数]/[配点] - [根拠となるレジュメの記載]
- ※構造化データがない場合は求人票から抽出した必須要件を記載
- 小計: [実際の点数]/45点

### 実務遂行能力（25点満点）
- [評価項目]: [点数]/[配点] - [根拠となる実績・経験]
- 小計: [実際の点数]/25点

### 歓迎要件（15点満点）
- [構造化データの各歓迎スキル項目]: [点数]/[配点] - [該当する経験]
- ※構造化データがない場合は求人票から抽出した歓迎要件を記載
- 小計: [実際の点数]/15点

### 組織適合性（10点満点）
- 企業規模適応: [点数]/5点 - [過去の所属企業と求人企業の比較]
- 文化適合: [点数]/5点 - [根拠]
- 小計: [実際の点数]/10点

### 突出した経歴（5点満点）
- [特筆すべき実績]: [点数]/5点
- 小計: [実際の点数]/5点

主な強み:
- [必須要件との合致点を優先的に記載]
- [歓迎要件の充足があれば「○○の歓迎要件も満たしている」と明記]
- [突出した経歴・実績があれば強調（「○○での実績は業界でも稀少」等）]
- [「会ってみたい」と思わせる要素を明記]

主な懸念点:
【超重要】以下のルールを厳守すること：
1. 必須要件（required_skills/必須経験）の不足のみを記載
2. 歓迎要件（preferred_skills/歓迎経験）の不足は絶対に記載しない
3. 「業界知識不足」は、それが必須要件である場合のみ記載

記載フォーマット：
- [必須要件の不足のみを記載（「○○の必須要件を満たしていない」と明確に）]
- [必須要件不足による具体的な業務遂行上のリスク]

【絶対に記載してはいけない例】
× 飲食、物流、小売業界への営業経験がない（これが歓迎要件の場合）
× 新規顧客獲得の経験が不明（これが歓迎要件の場合）
× 特定業界の知識がない（これが歓迎要件の場合）

【記載すべき例】
○ 5年以上の法人営業経験（必須要件）を満たしていない
○ マネジメント経験（必須要件）が確認できない

評価サマリー:
[以下を含む総合評価]
- 構造化データに基づく評価結果
  * 必須スキル（required_skills）の充足度: ○個中○個充足
  * 歓迎スキル（preferred_skills）の充足度: ○個中○個充足
  * 経験年数要件（experience_years_min）の充足状況
- 構造化データで判断できなかった項目（求人票から補足的に評価）
- 【重要】必須要件不足の場合、その業務遂行上の具体的影響
- 経験の直近性（直近の経験か、過去の経験かを明記）
- 突出した経歴（ある場合は「○○の実績は採用市場でも希少」等と明記）
- 企業規模適応性（経歴企業と求人企業の規模差があれば明記）
- 企業が本質的に求める人材像との適合性（過去実績ベース）
- この候補者の実績・経験に基づく価値
- 総合的な推薦判断（必須要件不足がある場合は、その重大性を明記）

# 評価の注意点
- **構造化データ（required_skills、preferred_skills）を最優先で使用**
- 構造化データで判断できない項目のみ、求人票（job_description）を参照
- 必須要件と歓迎要件を明確に区別
- 必須要件の不足は致命的な問題として扱う
- 必須要件を1つでも満たさない場合、その影響を懸念点で詳細に説明
- 歓迎要件は純粋な加点要素として評価（満たしていなくても懸念点には含めない）
- 歓迎要件の不足を理由に候補者を否定的に評価しない
- レジュメに記載された事実・経歴のみで判断（ポテンシャルや可能性は評価しない）
- 「面接でカバー可能」「今後の成長に期待」等の楽観的評価は一切含めない
- 最終的に「現時点の経歴でクライアントがこの候補者と面談すべきか」で判断
- 必須要件不足の候補者は原則として推薦しない姿勢で評価

# 懸念点記載のルール
- 懸念点には必須要件の不足のみを記載する
- 歓迎要件が満たされていないことは懸念点として扱わない
- 「○○の歓迎要件はないが...」のような記載は避ける
- 歓迎要件は「あれば嬉しい」レベルであることを理解する"""
        
        print(f"  LLMにプロンプト送信中... (文字数: {len(prompt)})")
        response = self.model.generate_content(prompt)
        print(f"  LLMから応答受信")
        
        # デバッグモードの場合、生の応答を表示
        if os.getenv('DEBUG_MODE'):
            print(f"  LLM応答（最初の500文字）:")
            print(f"    {response.text[:500]}")
            print("    ...")
        
        evaluation = self._parse_evaluation(response.text)
        print(f"  評価結果パース完了")
        
        # 状態を更新
        state.current_evaluation = evaluation
        self.state = "completed"
        
        return state
    
    def _format_rag_insights(self, state) -> str:
        """RAG洞察をフォーマット"""
        if not hasattr(state, 'rag_insights') or not state.rag_insights:
            return ""
        
        insights = state.rag_insights
        text = "\n### 類似ケースからの洞察"
        
        # クライアント評価傾向
        if insights.get('client_tendency'):
            tendency = insights['client_tendency']
            text += f"\n- 類似ケースでの最頻出評価: {tendency['most_common_evaluation']} ({tendency['percentage']:.1f}%)"
        
        # リスク要因
        if insights.get('risk_factors'):
            text += "\n- 注意すべきリスク要因:"
            for risk in insights['risk_factors'][:2]:  # 上位2件
                text += f"\n  * {risk['pattern']}: {risk['reason']}"
        
        # 成功パターン
        if insights.get('success_patterns'):
            text += "\n- 成功パターン:"
            for pattern in insights['success_patterns'][:1]:  # 上位1件
                text += f"\n  * {pattern['evaluation']}: {pattern['key_factor']}"
        
        return text
    
    def _format_additional_info(self, search_results: Dict) -> str:
        """検索結果をフォーマット"""
        if not search_results:
            return ""
        
        text = "\n### Web検索による追加情報"
        
        # 企業規模比較を優先的に表示
        if "企業規模比較" in search_results:
            result = search_results["企業規模比較"]
            text += f"\n\n**企業規模比較（重要）**"
            text += f"\n{result.summary}"
            text += f"\n※規模差が大きい場合は適応リスクとして評価に反映すること"
            if result.sources:
                text += f"\n情報源: {', '.join(result.sources[:2])}"
        
        # その他の検索結果
        for key, result in search_results.items():
            if key != "企業規模比較":
                text += f"\n\n**{key}**"
                text += f"\n{result.summary}"
                if result.sources:
                    text += f"\n情報源: {', '.join(result.sources[:2])}"
        
        return text
    
    def _format_history(self, history: List) -> str:
        """評価履歴をフォーマット"""
        if not history:
            return ""
        
        text = "\n### 過去の評価推移"
        for cycle in history:
            text += f"\n\n**サイクル{cycle.cycle_number}**"
            text += f"\n- スコア: {cycle.evaluation.score}点（確信度: {cycle.evaluation.confidence}）"
            text += f"\n- 主な懸念: {cycle.evaluation.concerns[0] if cycle.evaluation.concerns else 'なし'}"
            if len(cycle.search_results) > 0:
                text += f"\n- 収集情報: {len(cycle.search_results)}件"
        
        return text
    
    def _parse_evaluation(self, text: str) -> EvaluationResult:
        """LLMの出力を評価結果にパース"""
        print(f"  パース開始（応答文字数: {len(text)}）")
        
        # デフォルト値
        score = 50
        confidence = "低"
        strengths = []
        concerns = []
        interview_points = []
        summary = ""
        
        # 各セクションを探す
        lines = text.strip().split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # スコアを探す（複数のパターンに対応）
            if "適合度スコア" in line and ":" in line:
                try:
                    # 数値部分を抽出
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                        print(f"    スコア検出: {score}")
                except Exception as e:
                    print(f"    スコアパースエラー: {e}")
            
            # 確信度を探す
            elif "確信度" in line and ":" in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    conf_text = parts[1].strip()
                    if "低" in conf_text:
                        confidence = "低"
                    elif "中" in conf_text:
                        confidence = "中"
                    elif "高" in conf_text:
                        confidence = "高"
                    print(f"    確信度検出: {confidence}")
            
            # セクションの開始を検出
            elif "強み" in line and (":" in line or "：" in line):
                current_section = "strengths"
            elif "懸念" in line and (":" in line or "：" in line):
                current_section = "concerns"
            elif ("評価サマリー" in line or "サマリー" in line) and (":" in line or "：" in line):
                parts = line.split(':', 1) if ':' in line else line.split('：', 1)
                if len(parts) > 1:
                    summary = parts[1].strip()
                current_section = "summary"
            
            # 箇条書き項目を収集
            elif current_section and (line.startswith("- ") or line.startswith("・ ") or line.startswith("* ")):
                item = line[2:].strip()
                if current_section == "strengths" and len(strengths) < 3:
                    strengths.append(item)
                elif current_section == "concerns" and len(concerns) < 3:
                    concerns.append(item)
            
            # サマリーの続きを収集
            elif current_section == "summary" and line and not line.startswith('-'):
                summary += ' ' + line
        
        # 情報が取得できなかった場合の処理
        if not strengths:
            print("    警告: 強みが検出できませんでした")
            strengths = ["候補者の具体的な強みを評価中"]
        if not concerns:
            print("    警告: 懸念点が検出できませんでした")
            concerns = ["特筆すべき懸念点なし"]
        if not summary:
            print("    警告: サマリーが検出できませんでした")
            # 全テキストから「評価サマリー」を探す別の方法
            for i, line in enumerate(lines):
                if "評価サマリー" in line:
                    # 次の行から内容を取得
                    if i + 1 < len(lines):
                        summary = lines[i + 1].strip()
                        # 空行まで続きを取得
                        for j in range(i + 2, len(lines)):
                            if lines[j].strip() and not lines[j].startswith('-'):
                                summary += ' ' + lines[j].strip()
                            else:
                                break
                    break
            
            if not summary:
                summary = "総合的な評価を実施中"
        
        print(f"    パース結果: スコア={score}, 確信度={confidence}, 強み={len(strengths)}件, 懸念={len(concerns)}件")
        
        return EvaluationResult(
            score=score,
            confidence=confidence,
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            raw_response=text
        )
    
    async def _get_candidate_info(self, state: ResearchState) -> str:
        """候補者基本情報を取得（stateから直接取得）"""
        print("    [候補者情報取得] 開始")
        
        # stateから直接候補者情報を取得
        info_parts = []
        
        if hasattr(state, 'candidate_age') and state.candidate_age is not None:
            info_parts.append(f"年齢: {state.candidate_age}歳")
            print(f"    [候補者情報取得] 年齢: {state.candidate_age}歳")
        
        if hasattr(state, 'candidate_gender') and state.candidate_gender:
            info_parts.append(f"性別: {state.candidate_gender}")
            print(f"    [候補者情報取得] 性別: {state.candidate_gender}")
        
        if hasattr(state, 'candidate_company') and state.candidate_company:
            info_parts.append(f"現在の所属: {state.candidate_company}")
            print(f"    [候補者情報取得] 現在の所属: {state.candidate_company}")
        
        if hasattr(state, 'enrolled_company_count') and state.enrolled_company_count is not None:
            info_parts.append(f"在籍企業数: {state.enrolled_company_count}社")
            print(f"    [候補者情報取得] 在籍企業数: {state.enrolled_company_count}社")
        
        if info_parts:
            return '\n'.join(info_parts)
        else:
            print("    [候補者情報取得] 候補者基本情報が提供されていません")
            return "年齢: 不明（候補者情報が提供されていません）"
    
    def _format_structured_resume_data(self, state: ResearchState) -> str:
        """構造化されたレジュメデータをフォーマット"""
        if not hasattr(state, 'structured_resume_data') or not state.structured_resume_data:
            return ""
        
        data = state.structured_resume_data
        formatted_parts = []
        
        formatted_parts.append("## 候補者詳細データ（構造化データ）【高精度抽出済み】")
        
        # 基本情報
        basic_info = data.get('basic_info', {})
        if basic_info:
            formatted_parts.append("\n### 基本情報")
            if basic_info.get('name'):
                formatted_parts.append(f"氏名: {basic_info['name']}")
            if basic_info.get('age'):
                formatted_parts.append(f"年齢: {basic_info['age']}歳")
            if basic_info.get('current_company'):
                formatted_parts.append(f"現職: {basic_info['current_company']}")
        
        # マッチング用データ
        matching_data = data.get('matching_data', {})
        if matching_data:
            formatted_parts.append("\n### 経験サマリー")
            formatted_parts.append(f"総経験年数: {matching_data.get('total_experience_years', 0)}年")
            if matching_data.get('current_role'):
                formatted_parts.append(f"現在の役職: {matching_data['current_role']}")
            
            # 抽出されたスキル
            if matching_data.get('skills_flat'):
                formatted_parts.append("\n### 保有スキル（構造化抽出）")
                for i, skill in enumerate(matching_data['skills_flat'][:20], 1):
                    formatted_parts.append(f"{i}. {skill}")
                if len(matching_data['skills_flat']) > 20:
                    formatted_parts.append(f"... 他{len(matching_data['skills_flat']) - 20}件")
            
            # 主要な実績
            if matching_data.get('key_achievements'):
                formatted_parts.append("\n### 主要実績（数値含む）")
                for i, achievement in enumerate(matching_data['key_achievements'][:5], 1):
                    formatted_parts.append(f"{i}. {achievement['achievement']} ({achievement['company']})")
        
        # 職歴詳細
        raw_data = data.get('raw_data', {})
        career_history = raw_data.get('career_history', [])
        if career_history:
            formatted_parts.append("\n### 職歴詳細（時系列）")
            for job in career_history[:3]:  # 直近3社まで
                period = f"{job.get('period', {}).get('start', '不明')} - {job.get('period', {}).get('end', '現在')}"
                formatted_parts.append(f"\n**{period}: {job.get('company', '不明')} - {job.get('role', '不明')}**")
                if job.get('responsibilities'):
                    formatted_parts.append("担当業務:")
                    for resp in job['responsibilities'][:3]:
                        formatted_parts.append(f"- {resp}")
                if job.get('achievements'):
                    formatted_parts.append("実績:")
                    for ach in job['achievements'][:2]:
                        formatted_parts.append(f"- {ach}")
        
        return '\n'.join(formatted_parts) if formatted_parts else ""
    
    def _format_structured_job_data(self, state: ResearchState) -> str:
        """構造化された求人データをフォーマット"""
        if not hasattr(state, 'structured_job_data') or not state.structured_job_data:
            return ""
        
        data = state.structured_job_data
        formatted_parts = []
        
        formatted_parts.append("## 求人詳細データ（構造化データ）【優先的に使用】")
        
        # 基本情報
        if data.get('position'):
            formatted_parts.append(f"職種: {data['position']}")
        if data.get('employment_type'):
            formatted_parts.append(f"雇用形態: {data['employment_type']}")
        if data.get('work_location'):
            formatted_parts.append(f"勤務地: {data['work_location']}")
        
        # 給与情報
        if data.get('salary_min') or data.get('salary_max'):
            salary_min = data.get('salary_min', '未設定')
            salary_max = data.get('salary_max', '未設定')
            formatted_parts.append(f"給与レンジ: {salary_min:,}円 〜 {salary_max:,}円" if isinstance(salary_min, (int, float)) else f"給与レンジ: {salary_min} 〜 {salary_max}")
        
        # 必須スキル
        if data.get('required_skills'):
            formatted_parts.append("\n### 必須スキル・経験【最重要：これを基準に評価】")
            for i, skill in enumerate(data['required_skills'], 1):
                formatted_parts.append(f"{i}. {skill}")
        
        # 歓迎スキル
        if data.get('preferred_skills'):
            formatted_parts.append("\n### 歓迎スキル・経験【加点要素：これを基準に加点評価】")
            for i, skill in enumerate(data['preferred_skills'], 1):
                formatted_parts.append(f"{i}. {skill}")
        
        # 最小経験年数
        if data.get('experience_years_min'):
            formatted_parts.append(f"\n最小経験年数: {data['experience_years_min']}年以上")
        
        return '\n'.join(formatted_parts) if formatted_parts else ""
    
    def _apply_semantic_guards(self, state: ResearchState) -> str:
        """セマンティックガードレールを適用して洞察を生成"""
        insights = []
        
        # 営業経験の検出
        if hasattr(state, 'job_description') and '営業' in state.job_description:
            has_sales, confidence, evidence = SemanticGuards.detect_sales_experience(state.resume)
            
            if evidence:
                insights.append("\n### セマンティック分析による営業経験の検出")
                insights.append(f"営業経験の可能性: {'高' if confidence > 0.7 else '中' if confidence > 0.4 else '低'} (確信度: {confidence:.1%})")
                insights.append("検出された要素:")
                for e in evidence[:3]:  # 最大3つまで
                    insights.append(f"- {e}")
                
                if has_sales and confidence < 0.7:
                    insights.append("※ 間接的な指標から営業要素を検出。詳細な評価が必要")
        
        # 職種マッチングの評価（必要に応じて）
        # ここに追加の分析を実装可能
        
        return '\n'.join(insights) if insights else ""