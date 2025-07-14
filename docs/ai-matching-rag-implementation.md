# RAGとAIエージェントによる採用マッチングシステム実装ガイド

## 概要

本ドキュメントは、RPO自動化システムにおけるAIマッチング機能の実装設計を記載しています。過去の採用評価データを活用したRAG（Retrieval-Augmented Generation）システムと、DeepResearchアプローチによる段階的評価を組み合わせた、高精度な候補者マッチングシステムの構築方法を説明します。

## システムアーキテクチャ

### 全体構成

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  求人票データ    │────▶│   Supabase      │     │  Pinecone       │
│  (正規化)       │     │   (構造化DB)     │     │  (ベクトルDB)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                         ▲
                              ▼                         │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 候補者レジュメ   │────▶│  Gemini API     │────▶│  1536次元       │
│ ピックアップ情報 │     │  (Embedding)    │     │  ベクトル       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                              ▼                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ 新規候補者      │────▶│  DeepResearch   │────▶│  最終判定       │
│                │     │  3段階評価      │     │  (A/B/C/D)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## 技術スタック

- **ベクトルDB**: Pinecone (無料枠: 10万ベクトル)
- **構造化DB**: Supabase (既存インフラ活用)
- **埋め込みモデル**: Gemini API (text-embedding-004, 1536次元)
- **評価エンジン**: DeepResearchアルゴリズム + RAG

## データ構造

### 1. Supabase テーブル設計

```sql
-- 求人票マスタテーブル
CREATE TABLE job_postings (
    id TEXT PRIMARY KEY,
    position TEXT NOT NULL,
    job_description TEXT NOT NULL,
    memo TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 候補者評価テーブル
CREATE TABLE candidate_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id TEXT REFERENCES job_postings(id),
    candidate_id TEXT NOT NULL,
    company TEXT,
    pickup_memo TEXT,
    judgement CHAR(1) CHECK (judgement IN ('A','B','C','D')),
    note TEXT,
    added_date DATE,
    added_by TEXT,
    vector_id TEXT, -- Pineconeでの識別子
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2. ベクトル化データ構造

```python
# ベクトル化用テキストフォーマット
vector_text = """
【求人情報】
ポジション: {position}
要件サマリー: {job_description[:1000]}

【候補者情報】
会社: {company}
レジュメ: {resume_text}

【評価情報】
ピックアップメモ: {pickup_memo}
判定: {judgement}
評価詳細: {note}
"""

# Pineconeメタデータ
metadata = {
    "job_id": "job_001",
    "position": "Treasury Specialist",
    "candidate_id": "BU2899504",
    "company": "SBIホールディングス",
    "judgement": "B",
    "judgement_score": 3,  # A:4, B:3, C:2, D:1
    "added_date": "2025-04-15",
    "added_by": "sugawara"
}
```

## 実装詳細

### 1. ベクトル化処理

```python
import google.generativeai as genai
from pinecone import Pinecone
from supabase import create_client

class VectorEmbeddingSystem:
    def __init__(self):
        # Gemini設定
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.embedding_model = 'models/text-embedding-004'
        
        # Pinecone設定
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = self.pc.Index("recruitment-matching")
        
        # Supabase設定
        self.supabase = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    
    def create_embedding(self, text):
        """テキストを1536次元のベクトルに変換"""
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document",
            output_dimensionality=1536
        )
        return result['embedding']
```

### 2. DeepResearch評価エンジン

```python
class DeepResearchMatcher:
    def evaluate_candidate(self, candidate_data, job_requirement):
        """3段階の深掘り評価"""
        
        # Phase 1: 表層マッチング（基本要件チェック）
        phase1_result = {
            "skill_match": self.check_required_skills(candidate_data, job_requirement),
            "experience_match": self.check_experience_years(candidate_data, job_requirement),
            "score": self.calculate_surface_score()
        }
        
        # 早期終了判定
        if phase1_result['score'] < 40:
            return self.create_judgement('D', phase1_result)
        elif phase1_result['score'] > 90:
            return self.create_judgement('A', phase1_result)
        
        # Phase 2: 経験の質的評価（RAG活用）
        similar_cases = self.search_similar_cases(candidate_data, job_requirement)
        phase2_result = {
            "experience_quality": self.analyze_experience_depth(candidate_data, similar_cases),
            "project_relevance": self.assess_project_match(candidate_data, job_requirement),
            "score": self.calculate_deep_score()
        }
        
        # Phase 3: 潜在能力評価（高スコア候補のみ）
        if phase2_result['score'] > 70:
            phase3_result = {
                "growth_trajectory": self.analyze_career_growth(candidate_data),
                "adaptability": self.assess_learning_ability(candidate_data, similar_cases),
                "culture_fit": self.evaluate_culture_match(candidate_data, job_requirement)
            }
            
            return self.synthesize_all_phases([phase1_result, phase2_result, phase3_result])
        
        return self.synthesize_phases([phase1_result, phase2_result])
```

### 3. RAG検索システム

```python
class RAGSearchEngine:
    def search_similar_candidates(self, query_text, filters=None):
        """類似候補者の検索と評価パターンの抽出"""
        
        # クエリベクトル化
        query_vector = self.embedding_system.create_embedding(query_text)
        
        # Pinecone検索
        search_filters = {}
        if filters:
            if 'position' in filters:
                search_filters['position'] = {"$eq": filters['position']}
            if 'min_score' in filters:
                search_filters['judgement_score'] = {"$gte": filters['min_score']}
        
        results = self.index.query(
            vector=query_vector,
            filter=search_filters,
            top_k=10,
            include_metadata=True
        )
        
        # 詳細データの取得と評価パターンの抽出
        patterns = self.extract_evaluation_patterns(results)
        return patterns
    
    def extract_evaluation_patterns(self, search_results):
        """過去の評価から成功/失敗パターンを抽出"""
        patterns = {
            "success_patterns": [],  # A/B評価の共通要因
            "failure_patterns": [],  # C/D評価の共通要因
            "key_factors": {}       # 重要な判定要因
        }
        
        for match in search_results.matches:
            judgement = match.metadata['judgement']
            
            if judgement in ['A', 'B']:
                patterns['success_patterns'].append({
                    'factor': self.extract_success_factor(match),
                    'weight': match.score,
                    'example': match.metadata
                })
            elif judgement in ['C', 'D']:
                patterns['failure_patterns'].append({
                    'factor': self.extract_failure_factor(match),
                    'weight': match.score,
                    'example': match.metadata
                })
        
        return patterns
```

### 4. 判定基準

```python
class JudgementCriteria:
    """評価基準の定義"""
    
    # スコアリング重み付け
    SCORING_WEIGHTS = {
        "skill_match": 0.35,        # 必須スキルの充足度
        "experience_quality": 0.25,  # 経験の質と深さ
        "culture_fit": 0.20,        # 企業文化との適合性
        "growth_potential": 0.20     # 成長可能性
    }
    
    # 判定基準
    JUDGEMENT_THRESHOLDS = {
        'A': 85,  # Excellent評価
        'B': 70,  # Good評価（HM面談推奨）
        'C': 50,  # その他で検討
        'D': 0    # NG
    }
    
    # 評価パターン（実際のデータから学習）
    EVALUATION_PATTERNS = {
        'treasury_specialist': {
            'success_factors': [
                '出納業務の実務経験',
                '複数金融機関管理',
                'システム導入経験',
                'ベンチャー適性'
            ],
            'failure_factors': [
                '経理寄りで Treasury 経験薄い',
                'IT/プロダクト連携経験なし',
                '大企業文化のみ'
            ]
        }
    }
```

## 継続的学習システム

```python
class ContinuousLearningSystem:
    def update_with_human_feedback(self, evaluation_id, human_review):
        """人間のフィードバックを学習データに反映"""
        
        # 元の評価を取得
        original = self.get_original_evaluation(evaluation_id)
        
        # 学習データの作成
        learning_data = {
            "original_ai_judgement": original['ai_judgement'],
            "human_judgement": human_review['judgement'],
            "human_reasoning": human_review['note'],
            "gap_analysis": self.analyze_judgement_gap(original, human_review)
        }
        
        # 強化されたベクトルの作成
        enhanced_text = f"""
        {original['vector_text']}
        
        【人間による最終評価】
        判定: {human_review['judgement']}
        理由: {human_review['note']}
        AI評価との差異: {learning_data['gap_analysis']}
        """
        
        # 新しいベクトルとして保存
        enhanced_vector = self.create_embedding(enhanced_text)
        self.store_learning_vector(enhanced_vector, learning_data)
```

## 実装優先順位

1. **Phase 1: 基盤構築（1-2週間）**
   - Pineconeアカウント設定
   - Supabaseテーブル作成
   - Gemini API連携

2. **Phase 2: 基本機能実装（2-3週間）**
   - ベクトル化処理
   - 基本的な類似検索
   - シンプルな判定ロジック

3. **Phase 3: 高度化（1ヶ月）**
   - DeepResearch実装
   - 評価パターン学習
   - フィードバックループ

4. **Phase 4: 最適化（継続的）**
   - 判定精度の測定
   - パラメータ調整
   - UIとの統合

## 期待される成果

- **初期精度**: 60-70%（基本的なキーワードマッチング）
- **3ヶ月後**: 75-80%（パターン学習の効果）
- **6ヶ月後**: 80-85%（十分なデータ蓄積）

## 注意事項

1. **データプライバシー**
   - 候補者の個人情報は適切に匿名化
   - アクセス制御の実装

2. **コスト管理**
   - Gemini API: 埋め込み生成の回数に注意
   - Pinecone: 無料枠（10万ベクトル）の監視

3. **品質保証**
   - 定期的な精度測定
   - A/Bテストの実施
   - 人間のレビュー必須

## 参考資料

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Gemini API Embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [DeepResearchアルゴリズム設計](./ai-matching-deepresearch-design.md)
- [AIマッチング精度向上ガイド](./ai_matching_improvement_guide.md)