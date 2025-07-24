"""
レジュメ構造化パーサー
Gemini 2.0 Proを使用してレジュメを構造化データに変換
"""

import os
import json
import re
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import google.generativeai as genai


@dataclass
class CareerHistory:
    """職歴情報"""
    company: str
    role: str
    department: Optional[str]
    period: Dict[str, Optional[str]]  # {"start": "YYYY-MM", "end": "YYYY-MM" or None}
    responsibilities: List[str]
    achievements: List[str]
    used_skills: List[str]


@dataclass
class EducationHistory:
    """学歴情報"""
    school: str
    degree: Optional[str]
    major: Optional[str]
    period: Dict[str, Optional[str]]


@dataclass
class StructuredResume:
    """構造化されたレジュメデータ"""
    # 基本情報
    basic_info: Dict[str, Any]  # name, age, gender, contact, current_company
    
    # 原データ
    raw_data: Dict[str, Any]
    
    # マッチング用データ
    matching_data: Dict[str, Any]
    
    # メタデータ
    metadata: Dict[str, Any]


class ResumeParser:
    """レジュメ構造化パーサー"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("Gemini APIキーが設定されていません")
        
        genai.configure(api_key=api_key)
        # Gemini 2.5 Pro を使用
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        # Gemini 2.5 Pro: 5 RPM = 12秒間隔が必要
        # マッチング判断の処理時間（約5秒）を考慮して7秒の遅延
        self.rate_limit_delay = 7  # レート制限対策の遅延（秒）
        self.last_request_time = None  # 最後のリクエスト時刻を記録
    
    async def parse_resume(self, resume_text: str) -> StructuredResume:
        """レジュメを構造化データに変換"""
        
        print("[ResumeParser] レジュメの構造化を開始...")
        
        # レート制限チェック（5 RPM = 12秒間隔）
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            required_interval = 12  # 5 RPMの場合は12秒必要
            if elapsed < required_interval:
                wait_time = required_interval - elapsed
                print(f"[ResumeParser] レート制限対策として{wait_time:.1f}秒待機...")
                time.sleep(wait_time)
        
        # プロンプトを作成
        prompt = self._create_parsing_prompt(resume_text)
        
        try:
            # リクエスト時刻を記録
            self.last_request_time = time.time()
            
            # Gemini 2.5 Proで構造化
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # JSONを抽出
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if not json_match:
                raise ValueError("構造化データの抽出に失敗しました")
            
            json_text = json_match.group(1)
            structured_data = json.loads(json_text)
            
            # 次のマッチング判断のための遅延（処理時間を考慮）
            print(f"[ResumeParser] 次の処理のために{self.rate_limit_delay}秒待機...")
            time.sleep(self.rate_limit_delay)
            
            # ハイブリッド型データを構築
            return self._build_structured_resume(structured_data, resume_text)
            
        except Exception as e:
            print(f"[ResumeParser] エラー: {e}")
            # エラー時はデフォルト構造を返す
            return self._create_default_structure(resume_text)
    
    def _create_parsing_prompt(self, resume_text: str) -> str:
        """構造化用のプロンプトを作成"""
        return f"""あなたは採用のプロフェッショナルです。
以下のレジュメを詳細に分析し、構造化されたJSONデータとして出力してください。

# レジュメ
{resume_text}

# 抽出する情報
1. **基本情報**
   - 氏名（推測可能な場合）
   - 年齢（記載または推測）
   - 性別（記載がある場合）
   - 現在の所属企業
   - 連絡先（メール、電話）

2. **職歴** (すべての職歴を時系列で)
   - 会社名
   - 部署名
   - 役職/ポジション
   - 在籍期間（開始年月-終了年月）
   - 担当業務（箇条書き）
   - 実績・成果（数値があれば含める）
   - 使用したスキル・技術

3. **スキル**
   - 技術スキル（プログラミング言語、ツール等）
   - ビジネススキル（営業、マネジメント等）
   - 資格・認定
   - 言語スキル

4. **学歴**
   - 学校名
   - 学位・専攻
   - 卒業年月

5. **その他**
   - 志向性・希望
   - 特記事項

# 出力形式
以下のJSON形式で出力してください。情報が不明な場合はnullまたは空配列を使用。

```json
{{
  "basic_info": {{
    "name": "氏名（不明ならnull）",
    "age": 年齢（数値またはnull）,
    "gender": "性別（不明ならnull）",
    "current_company": "現在の所属企業",
    "contact": {{
      "email": "メールアドレス",
      "phone": "電話番号"
    }}
  }},
  "career_history": [
    {{
      "company": "会社名",
      "department": "部署名",
      "role": "役職",
      "period": {{
        "start": "YYYY-MM",
        "end": "YYYY-MM"（現在ならnull）
      }},
      "responsibilities": ["業務1", "業務2"],
      "achievements": ["実績1（数値含む）", "実績2"],
      "used_skills": ["スキル1", "スキル2"]
    }}
  ],
  "skills": {{
    "technical": ["技術スキル1", "技術スキル2"],
    "business": ["ビジネススキル1", "ビジネススキル2"],
    "certifications": ["資格1", "資格2"],
    "languages": ["言語1（レベル）", "言語2"]
  }},
  "education": [
    {{
      "school": "学校名",
      "degree": "学位",
      "major": "専攻",
      "period": {{
        "start": "YYYY-MM",
        "end": "YYYY-MM"
      }}
    }}
  ],
  "others": {{
    "preferences": "志向性・希望",
    "notes": "特記事項"
  }},
  "summary": {{
    "total_experience_years": 総経験年数,
    "job_change_count": 転職回数,
    "career_summary": "キャリアの要約（1-2文）"
  }}
}}
```

重要な注意点：
- 期間は必ず "YYYY-MM" 形式で記載
- 現在在籍中の場合、endはnull
- 数値実績は可能な限り具体的に抽出
- スキルは重複を避けて記載
- 推測が必要な場合は、合理的な推測を行う"""
    
    def _build_structured_resume(self, 
                               structured_data: Dict[str, Any],
                               original_text: str) -> StructuredResume:
        """ハイブリッド型の構造化レジュメを構築"""
        
        # マッチング用データを生成
        matching_data = self._create_matching_data(structured_data)
        
        # メタデータを生成
        metadata = {
            "parsed_at": datetime.now().isoformat(),
            "parser_version": "2.0",
            "model": "gemini-2.5-pro",
            "extraction_confidence": self._calculate_confidence(structured_data),
            "original_length": len(original_text)
        }
        
        return StructuredResume(
            basic_info=structured_data.get("basic_info", {}),
            raw_data=structured_data,
            matching_data=matching_data,
            metadata=metadata
        )
    
    def _create_matching_data(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """マッチング用に最適化されたデータを作成（採用要件の構造に対応）"""
        
        career_history = structured_data.get("career_history", [])
        skills = structured_data.get("skills", {})
        summary = structured_data.get("summary", {})
        
        # 採用要件のrequired_skills/preferred_skillsとマッチングしやすい形式
        all_skills = []
        
        # 技術スキル
        for skill in skills.get("technical", []):
            all_skills.append({
                "skill": skill,
                "type": "technical",
                "sources": self._find_skill_sources(skill, career_history)
            })
        
        # ビジネススキル
        for skill in skills.get("business", []):
            all_skills.append({
                "skill": skill,
                "type": "business",
                "sources": self._find_skill_sources(skill, career_history)
            })
        
        # 職歴から抽出したスキルも追加
        for job in career_history:
            for skill in job.get("used_skills", []):
                if not any(s["skill"] == skill for s in all_skills):
                    all_skills.append({
                        "skill": skill,
                        "type": "extracted",
                        "sources": [{"company": job["company"], "role": job["role"]}]
                    })
        
        # 経験年数の集計
        experience_summary = self._calculate_experience_summary(career_history)
        
        # 採用要件との高速マッチング用データ
        return {
            # スキルリスト（required_skills/preferred_skillsとの照合用）
            "all_skills": all_skills,
            "skills_flat": [s["skill"] for s in all_skills],  # 単純なリスト形式
            
            # 経験年数（experience_years_minとの照合用）
            "total_experience_years": summary.get("total_experience_years", 0),
            "experience_summary": experience_summary,
            
            # 職種・役職（positionとの照合用）
            "current_role": career_history[0]["role"] if career_history else None,
            "role_progression": [
                {
                    "role": job["role"],
                    "company": job["company"],
                    "period": job["period"]
                }
                for job in career_history
            ],
            
            # 業界経験
            "industry_experience": self._extract_industry_experience(career_history),
            
            # 実績（評価の参考用）
            "key_achievements": self._extract_key_achievements(career_history),
            
            # 現在の状況
            "current_employment": {
                "company": career_history[0]["company"] if career_history else None,
                "is_employed": career_history[0]["period"]["end"] is None if career_history else False
            }
        }
    
    def _find_skill_sources(self, skill: str, career_history: List[Dict]) -> List[Dict]:
        """スキルの習得元を特定"""
        sources = []
        
        for job in career_history:
            if skill in job.get("used_skills", []):
                sources.append({
                    "company": job["company"],
                    "role": job["role"],
                    "period": job["period"]
                })
        
        return sources
    
    def _calculate_experience_summary(self, career_history: List[Dict]) -> Dict[str, Any]:
        """経験年数のサマリーを計算"""
        if not career_history:
            return {"total_years": 0, "relevant_years": 0}
        
        # 最初の職歴から現在までの年数を計算
        first_job = career_history[-1]  # 最も古い職歴
        first_start = first_job["period"]["start"]
        
        if first_start:
            try:
                start_date = datetime.strptime(first_start, "%Y-%m")
                total_years = (datetime.now() - start_date).days / 365
            except:
                total_years = 0
        else:
            total_years = 0
        
        return {
            "total_years": round(total_years, 1),
            "company_count": len(set(job["company"] for job in career_history)),
            "role_count": len(set(job["role"] for job in career_history))
        }
    
    def _extract_key_achievements(self, career_history: List[Dict]) -> List[Dict]:
        """重要な実績を抽出"""
        achievements = []
        
        for job in career_history:
            for achievement in job.get("achievements", []):
                # 数値を含む実績を優先
                if any(char.isdigit() for char in achievement):
                    achievements.append({
                        "achievement": achievement,
                        "company": job["company"],
                        "role": job["role"]
                    })
        
        return achievements[:5]  # 上位5つ
    
    def _extract_industry_experience(self, career_history: List[Dict]) -> List[str]:
        """業界経験を抽出"""
        industries = set()
        
        industry_keywords = {
            "IT": ["システム", "ソフトウェア", "IT", "テクノロジー", "Web"],
            "製造": ["製造", "メーカー", "工場", "生産"],
            "金融": ["銀行", "証券", "保険", "金融", "ファイナンス"],
            "商社": ["商社", "商事", "トレーディング"],
            "小売": ["小売", "販売", "リテール", "ストア"],
            "サービス": ["サービス", "コンサルティング", "人材"]
        }
        
        for job in career_history:
            company = job["company"]
            for industry, keywords in industry_keywords.items():
                if any(keyword in company for keyword in keywords):
                    industries.add(industry)
        
        return list(industries)
    
    def _calculate_confidence(self, structured_data: Dict[str, Any]) -> float:
        """抽出の信頼度を計算"""
        score = 0.0
        total = 0
        
        # 基本情報の完全性
        basic_info = structured_data.get("basic_info", {})
        if basic_info.get("current_company"):
            score += 1
        total += 1
        
        # 職歴の詳細度
        career_history = structured_data.get("career_history", [])
        if career_history:
            score += 1
            # 期間が明確な職歴の割合
            valid_periods = sum(
                1 for job in career_history 
                if job.get("period", {}).get("start")
            )
            score += valid_periods / len(career_history)
            total += 2
        else:
            total += 2
        
        # スキル情報の充実度
        skills = structured_data.get("skills", {})
        if skills.get("technical") or skills.get("business"):
            score += 1
        total += 1
        
        return score / total if total > 0 else 0.5
    
    def _create_default_structure(self, resume_text: str) -> StructuredResume:
        """エラー時のデフォルト構造"""
        return StructuredResume(
            basic_info={},
            raw_data={"original_text": resume_text},
            matching_data={},
            metadata={
                "parsed_at": datetime.now().isoformat(),
                "parser_version": "2.0",
                "error": "構造化に失敗しました",
                "extraction_confidence": 0.0
            }
        )