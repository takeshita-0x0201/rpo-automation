"""
評価結果のパーサー
LLMの出力を構造化された評価結果に変換
"""

import re
from typing import Dict, List, Optional, Any
from ..nodes.base import EvaluationResult, ScoreDetail


class EvaluationParser:
    """評価結果をパースするユーティリティクラス"""
    
    @staticmethod
    def parse_score(text: str, section: Optional[str] = None, label: Optional[str] = None) -> Optional[int]:
        """テキストからスコアを抽出
        
        Args:
            text: パース対象のテキスト
            section: セクション名（オプション）
            label: ラベル名（オプション）
        
        Returns:
            抽出されたスコア、見つからない場合はNone
        """
        # セクションとラベルが指定されている場合
        if section and label:
            # まずセクションを探す
            section_pattern = rf'{section}[\s\S]*?(?=\n#|\Z)'
            section_match = re.search(section_pattern, text, re.IGNORECASE)
            if section_match:
                section_text = section_match.group(0)
                # セクション内でラベルを探す
                label_pattern = rf'{label}[：:]\s*\[?(\d+)\]?'
                label_match = re.search(label_pattern, section_text, re.IGNORECASE)
                if label_match:
                    return int(label_match.group(1))
        
        # 通常のパターンマッチング
        patterns = [
            r'適合度スコア[：:]\s*(\d+)',
            r'評価点[：:]\s*\[?(\d+)\]?',
            r'スコア[：:]\s*(\d+)',
            r'総合スコア[：:]\s*(\d+)',
            r'最終スコア[：:]\s*(\d+)',
            r'(\d+)点/100点',
            r'(\d+)/100'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                score = int(match.group(1))
                # 0-100の範囲に収める
                return max(0, min(100, score))
        
        # デフォルト値（引数なしの場合の後方互換性のため）
        if section is None and label is None:
            return 50
        
        return None
    
    @staticmethod
    def parse_confidence(text: str) -> str:
        """テキストから確信度を抽出"""
        text_lower = text.lower()
        
        # 確信度のパターン
        if any(word in text_lower for word in ['高い', 'high', '高']):
            return "高"
        elif any(word in text_lower for word in ['中程度', 'medium', '中']):
            return "中"
        elif any(word in text_lower for word in ['低い', 'low', '低']):
            return "低"
        
        # 確信度: の後を探す
        patterns = [
            r'確信度[：:]\s*([高中低])',
            r'confidence[：:]\s*([高中低])',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # デフォルト値
        return "中"
    
    @staticmethod
    def parse_list_items(text: str, section_name: str) -> List[str]:
        """特定セクションからリスト項目を抽出"""
        items = []
        
        # セクションを探す
        section_patterns = [
            rf'{section_name}[：:]\s*\n',
            rf'\*\*{section_name}\*\*[：:]\s*\n',
            rf'#{1,3}\s*{section_name}\s*\n',
            rf'【{section_name}】\s*\n'
        ]
        
        section_start = -1
        for pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                section_start = match.end()
                break
        
        if section_start == -1:
            return items
        
        # 次のセクションまでの内容を取得
        next_section_pattern = r'\n(?:#{1,3}|\*\*|【|主な|スコア|確信度|評価)'
        next_match = re.search(next_section_pattern, text[section_start:])
        
        if next_match:
            section_content = text[section_start:section_start + next_match.start()]
        else:
            section_content = text[section_start:]
        
        # リスト項目を抽出
        list_patterns = [
            r'^[-•*]\s*(.+)$',  # - や • や * で始まる行
            r'^\d+[.)]\s*(.+)$',  # 番号付きリスト
            r'^・\s*(.+)$'  # 日本語の中点
        ]
        
        for line in section_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            for pattern in list_patterns:
                match = re.match(pattern, line)
                if match:
                    items.append(match.group(1).strip())
                    break
            else:
                # リストマーカーがない場合でも、空行でない場合は追加
                if line and not any(keyword in line for keyword in ['：', ':', '評価', 'スコア']):
                    items.append(line)
        
        return items
    
    @staticmethod
    def parse_score_breakdown(text: str) -> Dict[str, ScoreDetail]:
        """スコアの詳細内訳をパース"""
        breakdown = {}
        
        # 各カテゴリのパターン
        categories = {
            "required_skills": ["必須要件", "必須スキル"],
            "practical_ability": ["実務遂行能力", "実務能力"],
            "preferred_skills": ["歓迎要件", "歓迎スキル"],
            "organizational_fit": ["組織適合性", "企業適合"],
            "outstanding_career": ["突出した経歴", "特筆事項"]
        }
        
        for key, patterns in categories.items():
            for pattern in patterns:
                # カテゴリセクションを探す
                section_pattern = rf'###?\s*{pattern}.*?(\d+)点満点.*?\n([\s\S]*?)(?=###?|$)'
                match = re.search(section_pattern, text)
                
                if match:
                    max_score = float(match.group(1))
                    section_content = match.group(2)
                    
                    # 実際のスコアを探す
                    score_match = re.search(r'小計[：:]\s*(\d+(?:\.\d+)?)', section_content)
                    actual_score = float(score_match.group(1)) if score_match else 0
                    
                    # 個別項目を抽出
                    items = []
                    item_pattern = r'^[-•]\s*(.+?)[：:]\s*(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)'
                    for line in section_content.split('\n'):
                        item_match = re.match(item_pattern, line.strip())
                        if item_match:
                            items.append({
                                "name": item_match.group(1),
                                "score": float(item_match.group(2)),
                                "max_score": float(item_match.group(3))
                            })
                    
                    breakdown[key] = ScoreDetail(
                        category=pattern,
                        max_score=max_score,
                        actual_score=actual_score,
                        items=items,
                        reasoning=section_content.strip()
                    )
                    break
        
        return breakdown
    
    @staticmethod
    def parse_evaluation(text: str) -> EvaluationResult:
        """LLMの出力を評価結果にパース"""
        print(f"  パース開始（応答文字数: {len(text)}）")
        
        # 基本情報のパース
        score = EvaluationParser.parse_score(text)
        confidence = EvaluationParser.parse_confidence(text)
        
        # リスト項目のパース
        strengths = EvaluationParser.parse_list_items(text, "主な強み")
        concerns = EvaluationParser.parse_list_items(text, "主な懸念点")
        interview_points = EvaluationParser.parse_list_items(text, "面接での確認事項")
        
        # サマリーの抽出
        summary = ""
        summary_patterns = [
            r'評価サマリー[：:]\s*\n([\s\S]+?)(?=\n\n|$)',
            r'総合評価[：:]\s*\n([\s\S]+?)(?=\n\n|$)',
            r'【評価サマリー】\s*\n([\s\S]+?)(?=\n\n|$)'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text)
            if match:
                summary = match.group(1).strip()
                break
        
        # スコア内訳のパース（存在する場合）
        score_breakdown = None
        if "スコア内訳" in text or "点満点" in text:
            try:
                score_breakdown = EvaluationParser.parse_score_breakdown(text)
            except Exception as e:
                print(f"    スコア内訳のパースに失敗: {e}")
        
        print(f"    パース結果: スコア={score}, 確信度={confidence}")
        print(f"    強み={len(strengths)}件, 懸念={len(concerns)}件")
        
        return EvaluationResult(
            score=score,
            confidence=confidence,
            strengths=strengths,
            concerns=concerns,
            summary=summary,
            interview_points=interview_points if interview_points else None,
            raw_response=text,
            score_breakdown=score_breakdown
        )
    
    @staticmethod
    def parse_skill_evaluation(text: str) -> Dict[str, Any]:
        """スキル評価の結果をパース"""
        result = {
            "required_skills": {},
            "preferred_skills": {},
            "match_rate": {"required": 0, "preferred": 0}
        }
        
        # 必須スキルの評価を抽出
        required_section = re.search(r'必須スキル評価[：:]([\s\S]+?)(?=歓迎スキル評価|マッチング率|$)', text)
        if required_section:
            for line in required_section.group(1).split('\n'):
                match = re.match(r'[-•]\s*(.+?)[：:]\s*(充足|不足)\s*[-–]\s*(.+)', line.strip())
                if match:
                    skill = match.group(1).strip()
                    status = match.group(2)
                    evidence = match.group(3).strip()
                    result["required_skills"][skill] = {
                        "fulfilled": status == "充足",
                        "evidence": evidence
                    }
        
        # 歓迎スキルの評価を抽出
        preferred_section = re.search(r'歓迎スキル評価[：:]([\s\S]+?)(?=マッチング率|$)', text)
        if preferred_section:
            for line in preferred_section.group(1).split('\n'):
                match = re.match(r'[-•]\s*(.+?)[：:]\s*(該当|非該当)\s*[-–]\s*(.+)', line.strip())
                if match:
                    skill = match.group(1).strip()
                    status = match.group(2)
                    evidence = match.group(3).strip()
                    result["preferred_skills"][skill] = {
                        "fulfilled": status == "該当",
                        "evidence": evidence
                    }
        
        # マッチング率を抽出
        match_rate = re.search(r'マッチング率[：:]\s*必須\[(\d+)\]%.*?歓迎\[(\d+)\]%', text)
        if match_rate:
            result["match_rate"]["required"] = int(match_rate.group(1))
            result["match_rate"]["preferred"] = int(match_rate.group(2))
        
        return result