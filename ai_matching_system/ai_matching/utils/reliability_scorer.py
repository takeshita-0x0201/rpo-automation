"""
情報信頼性評価モジュール
Web検索結果の信頼性をスコアリング
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
from urllib.parse import urlparse


class ReliabilityScorer:
    """情報ソースの信頼性を評価"""
    
    # 信頼できるドメインとそのスコア
    TRUSTED_DOMAINS = {
        # ニュースサイト
        "nikkei.com": 0.9,
        "reuters.com": 0.9,
        "bloomberg.com": 0.9,
        "toyokeizai.net": 0.85,
        "diamond.jp": 0.85,
        
        # 企業情報サイト
        "kabutan.jp": 0.85,
        "ullet.com": 0.85,
        "shikiho.jp": 0.9,
        
        # 技術情報サイト
        "github.com": 0.85,
        "stackoverflow.com": 0.8,
        "qiita.com": 0.75,
        "zenn.dev": 0.75,
        
        # 政府・公的機関
        ".go.jp": 0.95,
        ".gov": 0.95,
        
        # 求人・キャリア情報
        "indeed.com": 0.8,
        "linkedin.com": 0.8,
        "bizreach.jp": 0.8,
        "rikunabi.com": 0.75,
        "mynavi.jp": 0.75
    }
    
    # 信頼性が低いドメイン
    UNRELIABLE_DOMAINS = {
        "wikipedia.org": 0.6,  # 編集可能なため
        "yahoo.co.jp": 0.5,   # 知恵袋などUGCが混在
        "5ch.net": 0.3,       # 匿名掲示板
        "twitter.com": 0.4,   # SNS
        "x.com": 0.4,         # SNS
        "facebook.com": 0.4,  # SNS
    }
    
    @classmethod
    def score_source(cls, source_url: str, content: str, published_date: Optional[str] = None) -> Dict[str, any]:
        """
        情報ソースの信頼性をスコアリング
        
        Returns:
            Dict containing:
            - reliability_score: 0.0-1.0の信頼性スコア
            - factors: スコアリングの要因
            - warnings: 警告メッセージのリスト
        """
        factors = {}
        warnings = []
        
        # 1. ドメイン信頼度
        domain_score = cls._score_domain(source_url)
        factors['domain_trust'] = domain_score
        
        # 2. コンテンツの鮮度
        freshness_score = cls._score_freshness(published_date, content)
        factors['freshness'] = freshness_score
        
        # 3. コンテンツの質
        quality_score = cls._score_content_quality(content)
        factors['content_quality'] = quality_score
        
        # 4. 情報の一貫性
        consistency_score = cls._score_consistency(content)
        factors['consistency'] = consistency_score
        
        # 総合スコア計算（重み付け平均）
        weights = {
            'domain_trust': 0.4,
            'freshness': 0.3,
            'content_quality': 0.2,
            'consistency': 0.1
        }
        
        reliability_score = sum(
            factors[key] * weights[key] 
            for key in weights if key in factors
        )
        
        # 警告の生成
        if domain_score < 0.5:
            warnings.append("信頼性の低いドメインです")
        if freshness_score < 0.5:
            warnings.append("情報が古い可能性があります")
        if quality_score < 0.5:
            warnings.append("コンテンツの質に問題がある可能性があります")
        
        return {
            'reliability_score': round(reliability_score, 2),
            'factors': factors,
            'warnings': warnings
        }
    
    @classmethod
    def _score_domain(cls, url: str) -> float:
        """ドメインの信頼度をスコアリング"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # 完全一致をチェック
            for trusted_domain, score in cls.TRUSTED_DOMAINS.items():
                if domain == trusted_domain or domain.endswith('.' + trusted_domain):
                    return score
            
            # 信頼性が低いドメイン
            for unreliable_domain, score in cls.UNRELIABLE_DOMAINS.items():
                if domain == unreliable_domain or domain.endswith('.' + unreliable_domain):
                    return score
            
            # HTTPSかどうか
            if parsed.scheme == 'https':
                return 0.65  # デフォルトより少し高い
            
            return 0.5  # デフォルト
            
        except:
            return 0.5
    
    @classmethod
    def _score_freshness(cls, published_date: Optional[str], content: str) -> float:
        """情報の鮮度をスコアリング"""
        # 日付を抽出する試み
        date_patterns = [
            r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})',
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',
            r'(\d{1,2})/(\d{1,2})/(\d{4})'
        ]
        
        extracted_date = None
        for pattern in date_patterns:
            match = re.search(pattern, content[:500])  # 最初の500文字をチェック
            if match:
                try:
                    if pattern == date_patterns[2]:  # MM/DD/YYYY format
                        extracted_date = datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)))
                    else:
                        extracted_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                    break
                except:
                    continue
        
        if not extracted_date and published_date:
            # パブリッシュ日付から変換を試みる
            try:
                extracted_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            except:
                pass
        
        if not extracted_date:
            return 0.5  # 日付が不明な場合は中間値
        
        # 経過日数に基づくスコア
        days_old = (datetime.now() - extracted_date).days
        
        if days_old < 30:
            return 1.0
        elif days_old < 90:
            return 0.8
        elif days_old < 180:
            return 0.6
        elif days_old < 365:
            return 0.4
        else:
            return 0.2
    
    @classmethod
    def _score_content_quality(cls, content: str) -> float:
        """コンテンツの質をスコアリング"""
        score = 1.0
        
        # 文章の長さ
        if len(content) < 200:
            score -= 0.2
        
        # 数字やデータの存在
        numbers = re.findall(r'\d+(?:\.\d+)?[%％]?', content)
        if len(numbers) > 2:
            score += 0.1
        
        # 引用や出典の存在
        citation_patterns = ['出典', '引用', 'ソース', '参考', '参照', 'による', '発表']
        if any(pattern in content for pattern in citation_patterns):
            score += 0.1
        
        # 広告や宣伝文句の存在
        ad_patterns = ['PR', '広告', 'スポンサー', '今すぐ', '無料', 'クリック']
        if any(pattern in content for pattern in ad_patterns):
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    @classmethod
    def _score_consistency(cls, content: str) -> float:
        """情報の一貫性をスコアリング"""
        # 矛盾を示唆する表現
        contradiction_patterns = [
            'しかし', 'ただし', '一方で', '異なる', '矛盾',
            '不確実', '不明', '推測', '可能性', 'かもしれない'
        ]
        
        contradiction_count = sum(
            1 for pattern in contradiction_patterns 
            if pattern in content
        )
        
        # 矛盾が多いほどスコアを下げる
        return max(0.3, 1.0 - (contradiction_count * 0.1))
    
    @classmethod
    def resolve_contradictions(cls, results: List[Dict]) -> Dict:
        """
        複数の検索結果から矛盾を検出し解決
        
        Returns:
            Dict containing:
            - consensus: 合意事項
            - contradictions: 矛盾のリスト
            - resolution: 解決案
        """
        # 信頼性スコアでソート
        scored_results = []
        for result in results:
            if 'url' in result and 'content' in result:
                score_info = cls.score_source(
                    result['url'], 
                    result.get('content', ''),
                    result.get('published_date')
                )
                scored_results.append({
                    **result,
                    'reliability': score_info['reliability_score']
                })
        
        # 信頼性の高い順にソート
        scored_results.sort(key=lambda x: x.get('reliability', 0), reverse=True)
        
        # 数値情報の抽出と比較
        numeric_data = cls._extract_numeric_data(scored_results)
        contradictions = cls._find_contradictions(numeric_data)
        
        # 最も信頼性の高い情報源を基準に解決
        resolution = {}
        if scored_results:
            most_reliable = scored_results[0]
            resolution = {
                'preferred_source': most_reliable.get('url', ''),
                'reliability_score': most_reliable.get('reliability', 0),
                'data': cls._extract_key_facts(most_reliable.get('content', ''))
            }
        
        return {
            'consensus': cls._find_consensus(scored_results),
            'contradictions': contradictions,
            'resolution': resolution
        }
    
    @classmethod
    def _extract_numeric_data(cls, results: List[Dict]) -> Dict[str, List[Tuple[float, str]]]:
        """数値データを抽出"""
        numeric_data = {}
        
        for result in results:
            content = result.get('content', '')
            url = result.get('url', '')
            
            # 従業員数
            emp_pattern = r'従業員[数]?\s*[:：]?\s*(\d+(?:,\d+)?)\s*[人名]'
            emp_matches = re.findall(emp_pattern, content)
            if emp_matches:
                if '従業員数' not in numeric_data:
                    numeric_data['従業員数'] = []
                for match in emp_matches:
                    num = float(match.replace(',', ''))
                    numeric_data['従業員数'].append((num, url))
            
            # 売上高
            revenue_pattern = r'売上[高]?\s*[:：]?\s*(\d+(?:\.\d+)?)\s*[億万]'
            revenue_matches = re.findall(revenue_pattern, content)
            if revenue_matches:
                if '売上高' not in numeric_data:
                    numeric_data['売上高'] = []
                for match in revenue_matches:
                    numeric_data['売上高'].append((float(match), url))
        
        return numeric_data
    
    @classmethod
    def _find_contradictions(cls, numeric_data: Dict[str, List[Tuple[float, str]]]) -> List[Dict]:
        """数値データの矛盾を検出"""
        contradictions = []
        
        for key, values in numeric_data.items():
            if len(values) > 1:
                # 値の範囲を計算
                nums = [v[0] for v in values]
                min_val, max_val = min(nums), max(nums)
                
                # 20%以上の差異がある場合は矛盾とみなす
                if max_val > min_val * 1.2:
                    contradictions.append({
                        'type': key,
                        'values': values,
                        'variance': (max_val - min_val) / min_val
                    })
        
        return contradictions
    
    @classmethod
    def _find_consensus(cls, results: List[Dict]) -> List[str]:
        """合意事項を抽出"""
        if not results:
            return []
        
        # 高信頼性（0.7以上）の結果のみを使用
        reliable_results = [r for r in results if r.get('reliability', 0) >= 0.7]
        
        if not reliable_results:
            return []
        
        # 共通のキーワードを抽出（簡易実装）
        common_facts = []
        
        # 最初の結果からキーファクトを抽出
        first_content = reliable_results[0].get('content', '')
        sentences = first_content.split('。')[:5]  # 最初の5文
        
        # 他の結果でも言及されているか確認
        for sentence in sentences:
            if len(sentence) > 20:  # 短すぎる文は除外
                mentioned_count = sum(
                    1 for r in reliable_results[1:] 
                    if any(keyword in r.get('content', '') for keyword in sentence.split()[:3])
                )
                if mentioned_count >= len(reliable_results) * 0.5:
                    common_facts.append(sentence.strip())
        
        return common_facts[:3]  # 最大3つの合意事項
    
    @classmethod
    def _extract_key_facts(cls, content: str) -> List[str]:
        """重要な事実を抽出"""
        facts = []
        
        # 数値を含む文を優先
        sentences = content.split('。')
        for sentence in sentences:
            if re.search(r'\d+', sentence) and len(sentence) > 20:
                facts.append(sentence.strip())
        
        return facts[:5]  # 最大5つの事実