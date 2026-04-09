"""
Real Estate Domain Vocabulary and Optimization
Provides domain-specific normalization and re-ranking for RAG system
"""

import logging
from typing import List, Dict
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Fraud Red Flags
FRAUD_RED_FLAGS = [
    r"urgent.*sale", r"limited.*time", r"last.*chance", r"cash.*only",
    r"no.*questions", r"fake.*documents?", r"act.*fast", r"incredible.*price",
]

# Positive Market Indicators
POSITIVE_MARKET_INDICATORS = [
    r"metro.*coming", r"infrastructure.*development", r"price.*appreciation",
    r"commercial.*hub", r"tech.*corridor", r"rental.*yield",
]


class RealEstateVocabulary:
    """Handles real estate domain vocabulary normalization"""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize real estate terminology"""
        if not text:
            return text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def get_vocabulary_similarity(text1: str, text2: str) -> float:
        """Calculate vocabulary-based similarity"""
        text1_norm = RealEstateVocabulary.normalize_text(text1)
        text2_norm = RealEstateVocabulary.normalize_text(text2)
        words1 = set(text1_norm.split())
        words2 = set(text2_norm.split())
        if not words1 or not words2:
            return 0.0
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0

    @staticmethod
    def detect_fraud_indicators(text: str) -> List[Dict]:
        """Detect fraud indicators in text"""
        if not text:
            return []
        indicators = []
        text_lower = text.lower()
        for pattern in FRAUD_RED_FLAGS:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                if match:
                    indicators.append({'type': 'fraud_red_flag', 'detected': match.group()})
        return indicators

    @staticmethod
    def detect_positive_indicators(text: str) -> List[Dict]:
        """Detect positive market indicators"""
        if not text:
            return []
        indicators = []
        text_lower = text.lower()
        for pattern in POSITIVE_MARKET_INDICATORS:
            if re.search(pattern, text_lower):
                match = re.search(pattern, text_lower)
                if match:
                    indicators.append({'type': 'positive_market_indicator', 'detected': match.group()})
        return indicators


class ArticleReranker:
    """Re-ranks articles using domain-specific scoring"""

    @staticmethod
    def calculate_domain_score(article: Dict, location: str, query: str = None) -> float:
        """Calculate domain-specific score for an article"""
        base_score = article.get('relevance_score', 0.5)
        if article.get('location', '').lower() == location.lower():
            base_score = min(base_score + 0.3, 1.0)
        date_str = article.get('date', '')
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                days_old = (datetime.now() - date_obj).days
                if days_old < 7:
                    base_score = min(base_score + 0.2, 1.0)
            except (ValueError, TypeError):
                pass
        impact_score = float(article.get('impact_score', 0.5))
        if impact_score >= 0.7:
            base_score = min(base_score + (impact_score * 0.2), 1.0)
        if query:
            article_text = f"{article.get('title', '')} {article.get('content', '')}".lower()
            if query.lower() in article_text:
                base_score = min(base_score + 0.15, 1.0)
        content = f"{article.get('title', '')} {article.get('content', '')}"
        fraud_flags = RealEstateVocabulary.detect_fraud_indicators(content)
        if fraud_flags:
            base_score = max(base_score - (len(fraud_flags) * 0.1), 0.0)
        return base_score

    @staticmethod
    def rerank_articles(articles: List[Dict], location: str, query: str = None) -> List[Dict]:
        """Re-rank articles using domain-specific scoring"""
        reranked = []
        for article in articles:
            final_score = ArticleReranker.calculate_domain_score(article, location, query)
            reranked.append({**article, 'domain_score': final_score})
        reranked.sort(key=lambda x: x['domain_score'], reverse=True)
        return reranked


class DomainOptimizer:
    """Comprehensive domain optimization for RAG"""

    @staticmethod
    def optimize_retrieval(articles: List[Dict], location: str, query: str = None, apply_dedup: bool = True) -> List[Dict]:
        """Apply all domain optimizations to retrieval results"""
        if not articles:
            return articles
        optimized = []
        for article in articles:
            normalized_title = RealEstateVocabulary.normalize_text(article.get('title', ''))
            optimized.append({**article, 'normalized_title': normalized_title})
        if apply_dedup:
            unique_articles = []
            for article in optimized:
                is_duplicate = False
                for existing in unique_articles:
                    similarity = RealEstateVocabulary.get_vocabulary_similarity(
                        article.get('normalized_title', ''), existing.get('normalized_title', ''))
                    if similarity > 0.95:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    unique_articles.append(article)
            optimized = unique_articles
        for article in optimized:
            content = f"{article.get('title', '')} {article.get('content', '')}"
            article['fraud_indicators'] = RealEstateVocabulary.detect_fraud_indicators(content)
            article['positive_indicators'] = RealEstateVocabulary.detect_positive_indicators(content)
        reranked = ArticleReranker.rerank_articles(optimized, location, query)
        return reranked
