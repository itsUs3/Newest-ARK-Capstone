import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import hashlib
from typing import Dict, List
import logging
import re

from models.graph_fraud_engine import GraphFraudEngine


logger = logging.getLogger(__name__)

class FraudDetector:
    """
    Detect fraudulent, duplicate, and suspicious property listings
    Uses text similarity, image hashing, and behavioral analysis
    """
    
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
        self.listings_database = {}
        self.graph_engine = GraphFraudEngine()
        self.tfidf_weight = 0.70
        self.graph_weight = 0.30
        self.trust_thresholds = {
            'high': 75,
            'medium': 50,
            'low': 25
        }
    
    def _extract_phone_from_text(self, text: str) -> str:
        if not text:
            return ""
        # Simple Indian phone extraction: optional +91 then 10 digits.
        match = re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)
        return match.group(0) if match else ""

    def analyze(
        self,
        property_id: str,
        title: str,
        description: str = "",
        broker_name: str = "",
        phone_number: str = "",
        image_hash: str = "",
    ) -> Dict:
        """
        Analyze single listing for fraud indicators
        
        Returns:
            Dict with trust_score (0-100), risk_level, and flags
        """
        flags = []
        scores = {}
        
        # Check 1: Text quality and length
        text_quality_score = self._check_text_quality(title, description)
        scores['text_quality'] = text_quality_score
        if text_quality_score < 40:
            flags.append("Poor quality listing text")
        
        # Check 2: Duplicate detection
        duplicate_score = self._check_duplicates(property_id, title, description)
        scores['duplicate_risk'] = duplicate_score
        if duplicate_score > 60:
            flags.append("Similar listings found - possible duplicate")
        
        # Check 3: Suspicious/illegal keywords - returns flags AND a penalty score
        keyword_result = self._check_suspicious_keywords(title, description)
        keyword_flags = keyword_result['flags']
        keyword_penalty = keyword_result['penalty']
        flags.extend(keyword_flags)
        scores['keyword_penalty'] = keyword_penalty
        
        # Check 4: Pricing anomalies
        pricing_score = self._check_pricing_anomalies(title)
        scores['pricing'] = pricing_score
        
        # Check 5: Description relevance - is it actually about real estate?
        relevance_score = self._check_description_relevance(title, description)
        scores['relevance'] = relevance_score
        if relevance_score < 30:
            flags.append("Description not relevant to real estate")
        
        # Calculate overall trust score (weighted) 
        trust_score = (
            text_quality_score * 0.20 +
            (100 - duplicate_score) * 0.15 +
            pricing_score * 0.15 +
            relevance_score * 0.20 +
            (100 - keyword_penalty) * 0.30  # Keywords are biggest factor
        )
        
        # Derive graph attributes and persist relation graph when possible.
        derived_phone = phone_number.strip() or self._extract_phone_from_text(f"{title} {description}")
        listing_payload = {
            "property_id": property_id,
            "broker_name": broker_name.strip() or "unknown",
            "phone_number": derived_phone,
            "image_hash": image_hash.strip(),
        }
        graph_insert = self.graph_engine.insert_listing(listing_payload)
        graph_metrics = self.graph_engine.compute_fraud_score(property_id)
        graph_fraud_score = float(graph_metrics.get("graph_fraud_score", 0.0))

        # TF-IDF score is trust-oriented (higher is safer).
        # Graph score is risk-oriented (higher is riskier), so invert for trust blending.
        blended_trust_score = (
            self.tfidf_weight * trust_score +
            self.graph_weight * (100.0 - graph_fraud_score)
        )

        if graph_fraud_score >= 60:
            flags.append("Graph risk: listing linked to suspicious shared entities")
        elif graph_fraud_score >= 35:
            flags.append("Graph signal: moderate relational overlap detected")

        scores['graph_risk'] = graph_fraud_score

        # Determine risk level
        if blended_trust_score >= self.trust_thresholds['high']:
            risk_level = 'LOW'
        elif blended_trust_score >= self.trust_thresholds['medium']:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        return {
            'trust_score': min(100, max(0, blended_trust_score)),
            'tfidf_trust_score': min(100, max(0, trust_score)),
            'graph_fraud_score': graph_fraud_score,
            'graph_available': bool(graph_metrics.get('available', False)),
            'graph_metrics': graph_metrics,
            'graph_insert': graph_insert,
            'risk_level': risk_level,
            'flags': list(set(flags)),  # Remove duplicates
            'confidence': 0.75
        }
    
    def batch_analyze(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze multiple listings"""
        results = []
        for idx, row in df.iterrows():
            result = self.analyze(
                property_id=str(idx),
                title=str(row.get('title', '')),
                description=str(row.get('title2', ''))
            )
            result['listing_index'] = idx
            results.append(result)
        return results
    
    def _check_text_quality(self, title: str, description: str) -> float:
        """Score text quality (grammar, length, coherence)"""
        score = 100
        
        # Check title length
        if len(title) < 10:
            score -= 30
        elif len(title) > 200:
            score -= 10
        
        # Check for all caps
        if title.isupper():
            score -= 20
        
        # Check for excessive special characters in title
        special_char_count = sum(1 for c in title if not c.isalnum() and c != ' ')
        if special_char_count > len(title) * 0.1:
            score -= 20
        
        # ENHANCED: Comprehensive description quality checks
        if description:
            desc_len = len(description.strip())
            
            # Very short description is suspicious
            if desc_len < 20:
                score -= 25
            elif desc_len < 50:
                score -= 15
            
            # Check for garbage/nonsense text in description
            alpha_count = sum(1 for c in description if c.isalpha())
            if desc_len > 0:
                # If less than 40% alphabetic characters, likely garbage
                if alpha_count / desc_len < 0.4:
                    score -= 40
            
            # Check for excessive special chars in description
            desc_special = sum(1 for c in description if not c.isalnum() and c not in ' .,!?-')
            if desc_len > 0 and desc_special / desc_len > 0.15:
                score -= 30
            
            # Check if description is just repetitive characters
            if len(set(description.lower().replace(' ', ''))) < 5:
                score -= 35
            
            # Check for all caps description (shouting/spam)
            if description.isupper() and desc_len > 20:
                score -= 25
        else:
            # No description at all is suspicious
            score -= 20
        
        return max(0, score)
    
    def _check_duplicates(self, property_id: str, title: str, description: str) -> float:
        """Detect duplicate or similar listings"""
        text = f"{title} {description}"
        
        if len(self.listings_database) == 0:
            self.listings_database[property_id] = text
            return 0
        
        try:
            # Vectorize current text
            existing_texts = list(self.listings_database.values()) + [text]
            vectorizer = TfidfVectorizer(max_features=50, stop_words='english')
            vectors = vectorizer.fit_transform(existing_texts)
            
            # Compare with existing listings
            similarities = cosine_similarity(vectors[-1], vectors[:-1])[0]
            max_similarity = np.max(similarities) if len(similarities) > 0 else 0
            
            # Store this listing
            self.listings_database[property_id] = text
            
            # Convert similarity to risk score (0-100)
            return min(100, max_similarity * 100)
        except:
            return 0
    
    def _check_suspicious_keywords(self, title: str, description: str) -> Dict:
        """
        Comprehensive suspicious/illegal content detection.
        Returns dict with 'flags' (list of strings) and 'penalty' (0-100 score, higher = worse).
        """
        flags = []
        penalty = 0
        text = f"{title} {description}".lower()
        
        # ============================================
        # CATEGORY 1: ILLEGAL CONTENT (Critical - instant high risk)
        # Each match: +40 penalty
        # ============================================
        illegal_content = {
            # Weapons & Violence
            'gun': 'Illegal content: weapons reference',
            'guns': 'Illegal content: weapons reference',
            'firearm': 'Illegal content: firearms reference',
            'firearms': 'Illegal content: firearms reference',
            'pistol': 'Illegal content: weapons reference',
            'rifle': 'Illegal content: weapons reference',
            'ammunition': 'Illegal content: ammunition reference',
            'ammo': 'Illegal content: ammunition reference',
            'explosiv': 'Illegal content: explosives reference',
            'bomb': 'Illegal content: explosives reference',
            'grenade': 'Illegal content: explosives reference',
            'weapon': 'Illegal content: weapons reference',
            'weapons': 'Illegal content: weapons reference',
            'knife attack': 'Illegal content: violence reference',
            'murder': 'Illegal content: violence reference',
            'kill': 'Illegal content: violence reference',
            'assault': 'Illegal content: violence reference',
            'kidnap': 'Illegal content: kidnapping reference',
            'ransom': 'Illegal content: ransom reference',
            'hitman': 'Illegal content: violence reference',
            'smuggl': 'Illegal content: smuggling reference',
            'trafficking': 'Illegal content: trafficking reference',
            'extremis': 'Illegal content: extremism reference',
            'terroris': 'Illegal content: terrorism reference',
            
            # Drugs & Narcotics
            'drugs': 'Illegal content: narcotics reference',
            'drug': 'Illegal content: narcotics reference',
            'cocaine': 'Illegal content: narcotics reference',
            'heroin': 'Illegal content: narcotics reference',
            'marijuana': 'Illegal content: narcotics reference',
            'cannabis': 'Illegal content: narcotics reference',
            'weed': 'Illegal content: narcotics reference',
            'ganja': 'Illegal content: narcotics reference',
            'meth': 'Illegal content: narcotics reference',
            'narcotic': 'Illegal content: narcotics reference',
            'opium': 'Illegal content: narcotics reference',
            'lsd': 'Illegal content: narcotics reference',
            'ecstasy': 'Illegal content: narcotics reference',
            'mdma': 'Illegal content: narcotics reference',
            'ketamine': 'Illegal content: narcotics reference',
            'fentanyl': 'Illegal content: narcotics reference',
            'crack': 'Illegal content: narcotics reference',
            'dope': 'Illegal content: narcotics reference',
            'hash': 'Illegal content: narcotics reference',
            'charas': 'Illegal content: narcotics reference',
            'smack': 'Illegal content: narcotics reference',
            'brown sugar': 'Illegal content: narcotics reference',
            
            # Adult/Explicit Content
            'adult services': 'Illegal content: inappropriate listing',
            'escort': 'Illegal content: inappropriate listing',
            'prostitut': 'Illegal content: inappropriate listing',
            'massage parlour': 'Illegal content: inappropriate listing',
            'sex work': 'Illegal content: inappropriate listing',
            'red light': 'Illegal content: inappropriate listing',
            'pornograph': 'Illegal content: inappropriate listing',
            
            # Gambling & Betting
            'gambling': 'Illegal content: gambling reference',
            'betting': 'Illegal content: betting reference',
            'casino': 'Illegal content: gambling reference',
            'satta': 'Illegal content: illegal betting reference',
            'matka': 'Illegal content: illegal betting reference',
            
            # Fraud & Identity
            'fake id': 'Illegal content: identity fraud',
            'fake identity': 'Illegal content: identity fraud',
            'forged': 'Illegal content: forgery reference',
            'counterfeit': 'Illegal content: counterfeiting reference',
            'fake document': 'Illegal content: document fraud',
            'fake passport': 'Illegal content: document fraud',
            'fake aadhaar': 'Illegal content: identity fraud',
            'fake pan': 'Illegal content: identity fraud',
            'hawala': 'Illegal content: illegal money transfer',
            'money laundering': 'Illegal content: money laundering reference',
            
            # Theft & Stolen Property
            'stolen': 'Illegal content: stolen property reference',
            'theft': 'Illegal content: theft reference',
            'burglary': 'Illegal content: crime reference',
            'robbery': 'Illegal content: crime reference',
            'loot': 'Illegal content: crime reference',
        }
        
        for pattern, message in illegal_content.items():
            if re.search(r'\b' + re.escape(pattern), text):
                if message not in flags:
                    flags.append(message)
                    penalty += 40
        
        # ============================================
        # CATEGORY 2: SCAM PATTERNS (High risk)
        # Each match: +20 penalty
        # ============================================
        scam_patterns = {
            # Payment scams
            'money transfer': 'Scam: suspicious payment request',
            'western union': 'Scam: untraceable payment method',
            'bitcoin': 'Scam: cryptocurrency payment - high risk',
            'crypto': 'Scam: cryptocurrency payment request',
            'advance payment': 'Scam: advance fee fraud risk',
            'pay now': 'Scam: upfront payment pressure',
            'send money': 'Scam: money transfer request',
            'cash only': 'Scam: tax evasion / untraceable payment',
            'no receipt': 'Scam: unaccounted transaction',
            'upi transfer': 'Scam: direct transfer before verification',
            'neft urgent': 'Scam: urgent money transfer pressure',
            
            # Pressure tactics
            'urgent': 'Scam: urgency pressure tactic',
            'limited time': 'Scam: artificial deadline pressure',
            'act now': 'Scam: high pressure sales tactic',
            'hurry': 'Scam: urgency manipulation',
            'last chance': 'Scam: artificial scarcity',
            'grab this deal': 'Scam: pressure tactics',
            'only today': 'Scam: fake deadline pressure',
            'first come first served': 'Scam: artificial urgency',
            'going fast': 'Scam: artificial scarcity',
            'dont miss': 'Scam: fear of missing out manipulation',
            
            # False promises
            'guaranteed return': 'Scam: unrealistic guarantee',
            'guaranteed profit': 'Scam: unrealistic guarantee',
            'double your money': 'Scam: investment fraud',
            '100% return': 'Scam: impossible returns claimed',
            '200% return': 'Scam: impossible returns claimed',
            'guaranteed appreciation': 'Scam: no one can guarantee appreciation',
            'risk free': 'Scam: no investment is risk free',
            'no risk': 'Scam: misleading safety claim',
            'too good to be true': 'Scam: unrealistic claim',
            
            # Avoidance of transparency
            'whatsapp only': 'Scam: avoids traceable contact',
            'telegram only': 'Scam: avoids traceable contact',
            'email only': 'Scam: avoids phone verification',
            'no visit required': 'Scam: avoiding property inspection',
            'no inspection': 'Scam: hiding property condition',
            'sight unseen': 'Scam: preventing due diligence',
            'no paperwork': 'Scam: illegal transaction without documentation',
            'no registration needed': 'Scam: avoiding legal registration',
            'no stamp duty': 'Scam: tax evasion claim',
            
            # Identity/ownership fraud
            'owner out of country': 'Scam: absentee owner fraud pattern',
            'owner abroad': 'Scam: absentee owner fraud pattern',
            'nri owner urgent': 'Scam: NRI impersonation common fraud',
            'power of attorney sale': 'Scam: high risk - verify authorization',
            'gpa sale': 'Scam: GPA sales are often fraudulent',
            'benami': 'Scam: benami property is illegal',
            
            # Real estate specific frauds  
            'no brokerage': 'Warning: possible fake owner scam',
            'zero brokerage': 'Warning: possible fake owner scam',
            'tenant will pay': 'Scam: rental income bait',
            'subletting allowed': 'Warning: verify lease terms',
            'deposit refundable at any time': 'Scam: false deposit promise',
            'no agreement needed': 'Scam: avoiding legal binding',
            'oral agreement': 'Scam: no legal protection',
            'investment guaranteed': 'Scam: unrealistic investment claim',
            'rapid appreciation': 'Scam: false price growth promise',
            'government scheme': 'Scam: possible subsidy fraud',
            'black money': 'Illegal: undisclosed cash transaction',
            'under table': 'Illegal: undisclosed payment',
            'under construction bonus': 'Warning: builder distress signal',
            'distress sale': 'Warning: verify - may be scam',
            'foreclosure deal': 'Warning: verify with bank',
            'freehold converted': 'Warning: title fraud risk',
            'token amount': 'Warning: verify before paying token',
            'direct from builder': 'Warning: verify builder RERA registration',
        }
        
        for pattern, message in scam_patterns.items():
            if pattern in text:
                if message not in flags:
                    flags.append(message)
                    penalty += 20
        
        # ============================================
        # CATEGORY 3: SUSPICIOUS BUT NOT NECESSARILY ILLEGAL (Medium risk)
        # Each match: +10 penalty
        # ============================================
        suspicious_patterns = {
            'free': 'Suspicious: nothing in real estate is free',
            'no cost': 'Suspicious: hidden cost likely',
            'cheapest': 'Suspicious: unrealistic pricing claim',
            'lowest price': 'Suspicious: verify actual market rates',
            'below market': 'Suspicious: verify why below market',
            'secret deal': 'Suspicious: lack of transparency',
            'special discount': 'Suspicious: verify through official channels',
            'limited offer': 'Suspicious: artificial scarcity',
            'clearance sale': 'Suspicious: real estate is not retail',
            'must sell': 'Suspicious: desperation may indicate issues',
        }
        
        for pattern, message in suspicious_patterns.items():
            if pattern in text:
                if message not in flags:
                    flags.append(message)
                    penalty += 10
        
        # Check for multiple phone numbers (broker masquerading as owner)
        phone_pattern = r'\d{10}'
        phone_numbers = re.findall(phone_pattern, text)
        if len(set(phone_numbers)) > 2:
            flags.append('Suspicious: multiple phone numbers - possible broker network')
            penalty += 15
        
        # Cap penalty at 100
        penalty = min(100, penalty)
        
        return {'flags': flags, 'penalty': penalty}
    
    def _check_description_relevance(self, title: str, description: str) -> float:
        """
        Check if description is actually relevant to real estate.
        Returns score 0-100 where higher = more relevant.
        """
        if not description or not description.strip():
            return 30  # Missing description is suspicious but not damning
        
        text = f"{title} {description}".lower()
        
        # Real estate related terms - if NONE are present, description is irrelevant
        real_estate_terms = [
            'bhk', 'bedroom', 'bathroom', 'sqft', 'sq ft', 'square feet',
            'flat', 'apartment', 'house', 'villa', 'plot', 'land',
            'floor', 'carpet', 'built-up', 'builtup', 'super built',
            'kitchen', 'balcony', 'parking', 'lift', 'elevator',
            'furnished', 'semi-furnished', 'unfurnished',
            'rent', 'sale', 'lease', 'buy', 'sell', 'price', 'cost',
            'area', 'locality', 'location', 'near', 'close to',
            'amenities', 'gym', 'pool', 'swimming', 'garden',
            'security', 'gated', 'society', 'complex', 'tower',
            'rera', 'registration', 'possession', 'ready to move',
            'under construction', 'new construction', 'resale',
            'east facing', 'west facing', 'north facing', 'south facing',
            'vastu', 'ventilation', 'spacious', 'well maintained',
            'mumbai', 'delhi', 'bangalore', 'hyderabad', 'pune', 
            'chennai', 'kolkata', 'property', 'broker', 'owner',
            'room', 'hall', 'terrace', 'duplex', 'penthouse',
            'commercial', 'residential', 'office', 'shop', 'godown',
            'warehouse', 'industrial', 'builder', 'developer', 'project',
        ]
        
        matches = sum(1 for term in real_estate_terms if term in text)
        
        if matches == 0:
            return 0  # No real estate context whatsoever
        elif matches == 1:
            return 25  # Minimal context
        elif matches <= 3:
            return 50
        elif matches <= 6:
            return 75
        else:
            return 100
    
    def _check_pricing_anomalies(self, title: str) -> float:
        """Check for pricing red flags"""
        # Simplified - would need actual price extraction
        # Check for suspiciously low prices mentioned
        score = 80
        
        if 'free' in title.lower() or 'no cost' in title.lower():
            score -= 40
        
        return max(0, score)
    
    def calculate_similarity_hash(self, image_url: str) -> str:
        """Simple hash for image comparison (in production, use perceptual hashing)"""
        return hashlib.md5(image_url.encode()).hexdigest()

    def get_graph_analysis(self, property_id: str) -> Dict:
        """Return graph fraud analysis and duplicate clusters for a property."""
        graph_score = self.graph_engine.compute_fraud_score(property_id)
        duplicate_clusters = self.graph_engine.detect_duplicate_listings()
        return {
            "property_id": property_id,
            "graph_score": graph_score,
            "duplicate_clusters": duplicate_clusters,
            "example_cypher_queries": self.graph_engine.get_example_cypher_queries(),
        }
