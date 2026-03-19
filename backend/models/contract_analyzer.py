"""
RAG-Powered Lease/Contract Analyzer for Compliance Checks
Analyzes property leases and contracts against Indian RERA guidelines
Generates risk assessments and what-if scenario analysis
"""

import os
import json
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import pandas as pd
from pathlib import Path
import logging

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    RAG_AVAILABLE = True
except Exception as e:
    SentenceTransformer = None
    chromadb = None
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)


# Comprehensive RERA Guidelines & Violation Patterns
RERA_KNOWLEDGE_BASE = [
    {
        "section": "RERA Section 13",
        "title": "Possession Timeline",
        "content": "Builder must deliver possession within agreed timeline. Delay compensation: interest at prescribed rate (typically 8-12% p.a.) on purchase price for period exceeding 6 months. Buyer can terminate agreement if possession not delivered within 18 months of agreed date.",
        "risk_level": "critical"
    },
    {
        "section": "RERA Section 14",
        "title": "Penalty for Non-Completion",
        "content": "If builder fails to deliver possession within stipulated time, buyer entitled to possession at reduced price (as per RERA rules) or refund with interest. No penalty clause can exempt builder from RERA provisions.",
        "risk_level": "critical"
    },
    {
        "section": "RERA Section 15",
        "title": "Refund Policy",
        "content": "If buyer cancels after 30% construction, builder can retain up to 10% of amount paid. Full refund (with interest at 10.35% p.a.) required if builder cannot deliver within agreed timeline or if project is stalled for 1+ year.",
        "risk_level": "high"
    },
    {
        "section": "RERA Section 18",
        "title": "Structural Defects",
        "content": "Builder responsible for structural defects for 5 years from completion. Non-structural defects: 2 years liability. Defects must be rectified at builder's cost within 30 days of notice.",
        "risk_level": "high"
    },
    {
        "section": "RERA Section 22",
        "title": "Unfair Contract Terms",
        "content": "Any clause exempting builder from liability, shifting risks unfairly to buyer, or violating buyer's statutory rights is void. Terms must be fair and transparent.",
        "risk_level": "high"
    },
    {
        "section": "Tenancy Act Section 108",
        "title": "Security Deposit Rules",
        "content": "Security deposit caps: 1-2 months rent typically. Cannot exceed state limits. Refund within 30-45 days post-vacation. Deductions only for damages beyond normal wear.",
        "risk_level": "high"
    },
    {
        "section": "Tenancy Act Section 106",
        "title": "Possession Guarantee",
        "content": "Lessor must guarantee peaceful and uninterrupted possession. Cannot evict without legal cause or notice (30-60 days). Possession must be defined, not vague.",
        "risk_level": "critical"
    },
    {
        "section": "Stamp Duty Rules",
        "title": "Document Registration",
        "content": "All property agreements must be registered. Unregistered documents have no legal standing. Market value must be declared.",
        "risk_level": "critical"
    },
    {
        "section": "Property Rights Act",
        "title": "Clear Title Guarantee",
        "content": "Lessor must guarantee clear title, free from encumbrances. Title should be verifiable and insurable.",
        "risk_level": "critical"
    },
    {
        "section": "Indian Contract Act",
        "title": "Waiver of Rights",
        "content": "Parties cannot waive statutory rights. Any clause attempting to waive tenant rights, legal protections, or access to courts is VOID.",
        "risk_level": "critical"
    },
    {
        "section": "Consumer Protection Act",
        "title": "Unfair Practices",
        "content": "Unilateral changes, arbitrary charges, no notice clauses are unfair practices. Lessor must provide written notice (30 days) for any changes.",
        "risk_level": "high"
    },
]

# Critical Risk Patterns - These MUST be flagged
CRITICAL_VIOLATION_PATTERNS = {
    # Non-refundable deposits/advances
    'non_refundable_advance': {
        'patterns': [
            r'non[\s-]*refundable\s+(advance|deposit|payment|amount)',
            r'advance\s+payment.*non[\s-]*refundable',
            r'all.*non[\s-]*refundable',
            r'no refund.*any.*circumstance',
            r'advance.*cannot.*refunded',
        ],
        'risk_level': 'critical',
        'reason': 'Non-refundable advance violates RERA Section 15 - refunds must be guaranteed',
        'rera_section': 'RERA Section 15, 32'
    },
    
    # Waiver of legal rights
    'waiver_of_rights': {
        'patterns': [
            r'waive.*legal rights',
            r'waive.*statutory rights',
            r'waive.*rights.*under.*law',
            r'cannot.*approach.*court',
            r'shall not.*court',
            r'agree.*not.*approach.*tribunal',
            r'waives all.*legal.*recourse',
            r'forfeits.*all.*legal',
        ],
        'risk_level': 'critical',
        'reason': 'Waiver of legal rights is VOID - violates Indian Contract Act & Consumer Protection',
        'rera_section': 'Indian Contract Act, Consumer Protection Act'
    },
    
    # No possession guarantee
    'no_possession_guarantee': {
        'patterns': [
            r'may\s+delay\s+possession\s+indefinitely',
            r'no.*possession.*guarantee',
            r'never\s+given.*cannot.*claim',
            r'possession.*not\s+guaranteed',
            r'never.*guarantee.*possession',
        ],
        'risk_level': 'critical',
        'reason': 'Violates RERA Section 13 - possession timeline must be guaranteed',
        'rera_section': 'RERA Section 13, 106'
    },
    
    # Disclaimer of structural liability
    'structural_liability_disclaimer': {
        'patterns': [
            r'disclaim.*structural',
            r'no.*responsibility.*structural',
            r'structural.*tenant.*sole',
            r'foundation.*tenant.*responsibility',
            r'roof.*collapse.*tenant',
            r'building.*approval.*not.*guaranteed',
            r'not.*responsible.*structural',
            r'disclaims.*structural',
            r'disclaims.*defects',
        ],
        'risk_level': 'critical',
        'reason': 'Violates RERA Section 18 - builder/owner liable for structural defects (5 years)',
        'rera_section': 'RERA Section 18, 32'
    },
    
    # Unilateral changes without notice
    'unilateral_changes': {
        'patterns': [
            r'increase\s+rent.*any time.*without notice',
            r'may.*change.*charges.*arbitrarily',
            r'introduce\s+new\s+fees.*without.*consent',
            r'modify.*terms.*without.*consent',
            r'automatically.*agree.*future.*changes',
            r'unilateral.*change',
        ],
        'risk_level': 'critical',
        'reason': 'Violates Consumer Protection Act - changes require 30-day written notice',
        'rera_section': 'Consumer Protection Act, Section 106'
    },
    
    # Entry without notice / Harassment
    'entry_without_notice': {
        'patterns': [
            r'may.*enter.*anytime.*without notice',
            r'owner.*may.*enter.*property.*anytime',
            r'change\s+locks.*without.*notice',
            r'disconnect\s+(water|electricity|utilities?).*without notice',
            r'disconnect.*services.*without notice',
            r'unauthorized.*entry',
        ],
        'risk_level': 'critical',
        'reason': 'Violates tenancy laws - lessor needs 24-48 hours notice for entry',
        'rera_section': 'Tenancy Act, Section 106'
    },
    
    # Forfeiture without due process
    'improper_forfeiture': {
        'patterns': [
            r'terminate.*without notice',
            r'entire\s+deposit\s+forfeited',
            r'vacate\s+within\s+24\s+hours',
            r'failure.*triple\s+rent.*penalty',
            r'forfeiture.*no.*court',
            r'no eviction.*protection',
        ],
        'risk_level': 'critical',
        'reason': 'Violates tenancy laws - eviction requires legal notice and court proceedings',
        'rera_section': 'Tenancy Act'
    },
    
    # Undisclosed/undefined property
    'undefined_property': {
        'patterns': [
            r'residential\s+unit.*without.*address',
            r'property.*not.*specified',
            r'no.*title.*details',
            r'address.*undisclosed',
            r'location.*not.*specified',
            r'property\s+address.*not.*disclosed',
        ],
        'risk_level': 'critical',
        'reason': 'Property must be precisely defined - violates basic contract principles',
        'rera_section': 'RERA Section 13, Indian Contract Act'
    },
    
    # No ownership guarantee
    'no_ownership_guarantee': {
        'patterns': [
            r'not.*guarantee.*ownership',
            r'owner.*does not.*guarantee.*legal.*ownership',
            r'no.*title.*guarantee',
            r'title.*not.*guaranteed',
        ],
        'risk_level': 'critical',
        'reason': 'Owner must guarantee clear title - violates Property Rights Act',
        'rera_section': 'Property Rights Act, RERA Section 13'
    },
    
    # No registration clause
    'no_registration': {
        'patterns': [
            r'shall\s+not\s+be\s+registered',
            r'not.*register.*with.*authority',
            r'unregistered.*agreement',
            r'no.*registration',
        ],
        'risk_level': 'critical',
        'reason': 'Unregistered agreements have no legal standing - violates Stamp Duty Rules',
        'rera_section': 'Stamp Duty Rules, Registration Act'
    },
    
    # No occupancy certificate
    'no_occupancy_certificate': {
        'patterns': [
            r'no\s+occupancy\s+certificate',
            r'without\s+occupancy\s+certificate',
            r'occupancy\s+certificate.*not.*required',
            r'not.*occupancy\s+cert',
        ],
        'risk_level': 'critical',
        'reason': 'Property must have valid occupancy certificate - required by RERA',
        'rera_section': 'RERA Section 32, Building Code'
    },
}

# High Risk Patterns
HIGH_RISK_PATTERNS = {
    'excessive_deposit': {
        'patterns': [
            r'(\d+)\s+months.*deposit',
            r'deposit.*(\d+)\s+months',
            r'security\s+deposit.*(\d+)\s+months',
        ],
        'risk_level': 'high',
        'reason': 'Security deposit exceeds standard 1-2 months limit',
        'rera_section': 'Tenancy Act Section 108',
        'check': lambda m: int(m.group(1)) > 3 if m and m.group(1) else False
    },
    
    'arbitrary_charges': {
        'patterns': [
            r'goodwill\s+fee',
            r'additional.*charges.*later',
            r'arbitrary.*deduction',
            r'future\s+repair\s+estimate',
            r'undisclosed.*charges',
        ],
        'risk_level': 'high',
        'reason': 'Arbitrary charges not allowed - must be pre-specified',
        'rera_section': 'Consumer Protection Act'
    },
    
    'no_receipts': {
        'patterns': [
            r'not.*obliged.*issue.*receipt',
            r'no\s+written.*acknowledgment',
            r'no.*rent.*receipt',
            r'no\s+proof',
        ],
        'risk_level': 'high',
        'reason': 'Lessor must issue receipts - required for tax and documentation',
        'rera_section': 'Indian Income Tax Act'
    },
    
    'tenant_pays_owner_dues': {
        'patterns': [
            r'tenant.*pay.*past.*due',
            r'any\s+past\s+unpaid\s+dues\s+of\s+owner',
            r'tenant.*municipal.*penalties',
            r'tenant.*previous.*owner.*dues',
        ],
        'risk_level': 'high',
        'reason': 'Tenant cannot be liable for owner\'s past dues',
        'rera_section': 'RERA Section 22, Consumer Protection Act'
    },
    
    'all_repairs_tenant': {
        'patterns': [
            r'all\s+repairs.*tenant',
            r'structural.*tenant.*sole',
            r'plumbing.*tenant.*responsibility',
            r'foundation.*tenant.*liable',
            r'tenant.*all.*repairs',
        ],
        'risk_level': 'high',
        'reason': 'Structural repairs are lessor responsibility, not tenant',
        'rera_section': 'RERA Section 18, 32'
    },
    
    'no_possession_definition': {
        'patterns': [
            r'possession.*vague',
            r'will.*provide.*possession.*later',
            r'possession.*timeline.*not.*defined',
        ],
        'risk_level': 'high',
        'reason': 'Possession timeline must be clearly defined',
        'rera_section': 'RERA Section 13, 106'
    },
}


class ContractAnalyzer:
    """
    Advanced RAG-based analyzer for property leases and contract compliance
    Uses pattern matching + semantic search for comprehensive RERA analysis
    """
    
    def __init__(self, persist_directory: str = "chroma_db"):
        """Initialize Contract Analyzer"""
        self.persist_directory = persist_directory
        self.embedding_model = None
        self.chroma_client = None
        self.collection_name = "rera_laws"
        self.rag_enabled = RAG_AVAILABLE

        if self.rag_enabled:
            try:
                logger.info("Loading embedding model for contract analysis...")
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Initializing ChromaDB for contracts...")
                self.chroma_client = chromadb.PersistentClient(path=persist_directory)
            except Exception as e:
                logger.warning(f"Contract analyzer RAG unavailable ({e}); falling back to pattern-only mode")
                self.rag_enabled = False
        else:
            logger.warning("Contract analyzer running in pattern-only mode (RAG dependencies unavailable)")
        
        # Initialize law knowledge base
        self._initialize_law_kb()
    
    def _ensure_collection_exists(self):
        """Ensure collection exists"""
        if not self.rag_enabled or not self.chroma_client:
            return None
        try:
            return self.chroma_client.get_collection(name=self.collection_name)
        except Exception:
            return self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def _initialize_law_kb(self):
        """Initialize RERA law knowledge base in ChromaDB"""
        try:
            if not self.rag_enabled or not self.embedding_model:
                return

            collection = self._ensure_collection_exists()
            if collection is None:
                return
            
            # Get existing docs
            existing = collection.get()
            if existing['ids']:
                logger.info(f"Law KB already initialized with {len(existing['ids'])} laws")
                return
            
            # Vectorize and store RERA laws
            ids = []
            embeddings = []
            documents = []
            metadatas = []
            
            for idx, law in enumerate(RERA_KNOWLEDGE_BASE):
                doc_text = f"{law['section']} - {law['title']}: {law['content']}"
                embedding = self.embedding_model.encode(doc_text).tolist()
                
                ids.append(f"law_{idx}")
                embeddings.append(embedding)
                documents.append(doc_text)
                metadatas.append({
                    'section': law['section'],
                    'title': law['title'],
                    'risk_level': law['risk_level']
                })
            
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Initialized law KB with {len(ids)} RERA guidelines")
        
        except Exception as e:
            logger.error(f"Error initializing law KB: {e}")
    
    def analyze_contract(self, contract_text: str, contract_type: str = "lease") -> Dict:
        """
        Comprehensive contract analysis with pattern matching + RAG
        """
        try:
            # Phase 0: Validate input is actual contract text, not garbage
            validation_result = self._validate_contract_text(contract_text)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': 'Invalid contract text',
                    'message': validation_result['reason'],
                    'compliance_score': 0,
                    'risk_level': 'critical'
                }
            
            if not contract_text or len(contract_text.strip()) < 50:
                return {
                    'success': False,
                    'error': 'Contract text too short',
                    'message': 'Minimum 50 characters required',
                    'compliance_score': 0,
                    'risk_level': 'critical'
                }
            
            # Phase 1: Pattern-based violation detection
            critical_findings = self._detect_critical_violations(contract_text)
            high_findings = self._detect_high_risk_violations(contract_text)
            
            # Combine findings
            all_findings = critical_findings + high_findings
            
            # Phase 2: Extract clauses
            clauses = self._extract_clauses(contract_text)
            
            # Phase 3: Calculate compliance score
            compliance_score = self._calculate_compliance_score(
                len(critical_findings),
                len(high_findings),
                len(clauses)
            )
            
            # Phase 4: Generate recommendations
            recommendations = self._generate_recommendations(
                critical_findings, high_findings, compliance_score
            )
            
            return {
                'success': True,
                'contract_type': contract_type,
                'compliance_score': compliance_score,
                'risk_level': self._get_risk_level(compliance_score),
                'total_clauses_reviewed': len(clauses),
                'flagged_clauses': all_findings,
                'findings': all_findings,
                'recommendations': recommendations,
                'analysis_date': datetime.now().isoformat(),
                'critical_count': len(critical_findings),
                'high_count': len(high_findings)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing contract: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze contract'
            }
    
    def _extract_clauses(self, contract_text: str) -> List[str]:
        """Extract clauses from contract"""
        clauses = []
        lines = contract_text.split('\n')
        current_clause = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_clause and len(' '.join(current_clause)) > 20:
                    clauses.append(' '.join(current_clause))
                current_clause = []
            else:
                if any(marker in line for marker in ['.', ':', '1.', '2.', '3.']):
                    if current_clause and len(' '.join(current_clause)) > 20:
                        clauses.append(' '.join(current_clause))
                    current_clause = [line]
                else:
                    current_clause.append(line)
        
        if current_clause and len(' '.join(current_clause)) > 20:
            clauses.append(' '.join(current_clause))
        
        return clauses
    
    def _detect_critical_violations(self, text: str) -> List[Dict]:
        """Detect CRITICAL violations using pattern matching"""
        findings = []
        text_lower = text.lower()
        
        for violation_type, violation_info in CRITICAL_VIOLATION_PATTERNS.items():
            for pattern in violation_info['patterns']:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Extract context
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    
                    findings.append({
                        'clause': context[:150] + "..." if len(context) > 150 else context,
                        'risk_level': 'critical',
                        'reason': violation_info['reason'],
                        'rera_section': violation_info['rera_section'],
                        'violation_type': violation_type,
                        'deduction': 15
                    })
        
        return findings[:20]  # Limit to 20
    
    def _detect_high_risk_violations(self, text: str) -> List[Dict]:
        """Detect HIGH-RISK violations"""
        findings = []
        text_lower = text.lower()
        
        for violation_type, violation_info in HIGH_RISK_PATTERNS.items():
            for pattern in violation_info['patterns']:
                matches = re.finditer(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    # Check conditional validators
                    if 'check' in violation_info and not violation_info['check'](match):
                        continue
                    
                    start = max(0, match.start() - 80)
                    end = min(len(text), match.end() + 80)
                    context = text[start:end].strip()
                    
                    findings.append({
                        'clause': context[:150] + "..." if len(context) > 150 else context,
                        'risk_level': 'high',
                        'reason': violation_info['reason'],
                        'rera_section': violation_info['rera_section'],
                        'violation_type': violation_type,
                        'deduction': 10
                    })
        
        return findings[:15]
    
    def _validate_contract_text(self, contract_text: str) -> Dict:
        """
        Validate that input is actually a contract, not garbage or random text
        Returns: {'is_valid': bool, 'reason': str}
        """
        if not contract_text or len(contract_text.strip()) < 50:
            return {'is_valid': False, 'reason': 'Text too short to be a valid contract'}
        
        text_lower = contract_text.lower()
        text = contract_text.strip()
        
        # Check 1: Minimum alphabetic content (not just symbols/garbage)
        alpha_count = sum(1 for c in text if c.isalpha())
        total_count = len(text)
        if alpha_count / total_count < 0.5:
            return {'is_valid': False, 'reason': 'Text appears to be garbage - too few alphabetic characters. Please paste actual contract text.'}
        
        # Check 2: Must contain contract-related legal keywords
        required_legal_terms = [
            'party', 'parties', 'agreement', 'contract', 'hereby', 'lease', 'rent',
            'tenant', 'landlord', 'owner', 'purchaser', 'seller', 'buyer',
            'terms', 'conditions', 'clause', 'section', 'article',
            'whereas', 'witnesseth', 'consideration', 'undertake'
        ]
        
        found_terms = sum(1 for term in required_legal_terms if term in text_lower)
        if found_terms < 2:
            return {'is_valid': False, 'reason': 'Text does not appear to be a legal contract - missing standard legal terminology. Please provide actual lease/contract text.'}
        
        # Check 3: Excessive special characters indicate garbage
        special_chars = sum(1 for c in text if not c.isalnum() and c not in ' .,;:!?-()\n\r"\'')
        if special_chars / total_count > 0.3:
            return {'is_valid': False, 'reason': 'Text contains excessive special characters - appears to be corrupted or garbage data.'}
        
        # Check 4: Very repetitive text (same char/word repeated)
        unique_chars = len(set(text.lower().replace(' ', '')))
        if unique_chars < 10:
            return {'is_valid': False, 'reason': 'Text is too repetitive - does not appear to be meaningful contract content.'}
        
        # Check 5: Contains sentence-like structure (words separated by spaces)
        words = text.split()
        if len(words) < 20:
            return {'is_valid': False, 'reason': 'Text too short - contracts typically contain at least 20 words.'}
        
        # Check 6: Average word length should be reasonable (2-15 chars)
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        if avg_word_len < 2 or avg_word_len > 20:
            return {'is_valid': False, 'reason': 'Text structure is abnormal - not typical contract language.'}
        
        return {'is_valid': True, 'reason': 'Valid contract text'}
    
    def _calculate_compliance_score(self, critical_count: int, high_count: int, 
                                    total_clauses: int) -> int:
        """
        Calculate compliance score with weighted deduction
        Critical violations: -15 points each
        High violations: -10 points each
        """
        score = 100
        score -= critical_count * 15
        score -= high_count * 10
        
        return max(0, min(100, score))
    
    def _get_risk_level(self, score: int) -> str:
        """Determine overall risk level"""
        if score >= 80:
            return "low"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "high"
        else:
            return "critical"
    
    def _generate_recommendations(self, critical_findings: List[Dict], 
                                  high_findings: List[Dict], score: int) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        critical_count = len(critical_findings)
        high_count = len(high_findings)
        
        if critical_count > 5:
            recommendations.append(f"🚨 CRITICAL: {critical_count} critical violations found. DO NOT SIGN - seek immediate legal help.")
        elif critical_count > 0:
            recommendations.append(f"⚠️ {critical_count} critical issues detected. Consult lawyer before signing.")
        
        if high_count > 0:
            recommendations.append(f"⚡ {high_count} high-risk clauses need negotiation.")
        
        if critical_count == 0 and high_count == 0:
            recommendations.append("✅ No major violations detected. Still recommend legal review.")
        else:
            recommendations.append("❌ Request builder/lessor to remove all flagged clauses.")
            recommendations.append("📋 Demand registration with proper stamp duty.")
            recommendations.append("🔍 Verify property title and obtain title insurance.")
            recommendations.append("⚖️ Engage registered property lawyer for final review.")
        
        return recommendations
    
    def get_what_if_analysis(self, clause_text: str, scenario: str) -> Dict:
        """What-if scenario analysis"""
        scenarios = {
            "possession delay 6 months": {
                'consequence': 'Triggers compensation provisions under RERA',
                'rera_citation': 'RERA Section 13',
                'compensation': 'Interest at 8-12% p.a. on purchase price',
                'relief': 'Can terminate agreement after 18 months delay',
            },
            "cancel after 30% construction": {
                'consequence': 'Refund rules apply with deduction limits',
                'rera_citation': 'RERA Section 15',
                'deduction_limit': 'Builder can retain max 10%',
                'interest': '10.35% p.a. on refunded amount',
            },
            "structural defect found": {
                'consequence': 'Builder liability for repairs',
                'rera_citation': 'RERA Section 18',
                'liability': '5 years from completion',
                'cost': 'All repairs at builder\'s cost within 30 days',
            },
        }
        
        scenario_lower = scenario.lower()
        for key, details in scenarios.items():
            if key in scenario_lower:
                return {
                    'success': True,
                    'scenario': scenario,
                    **details
                }
        
        return {
            'success': False,
            'message': 'Custom scenario - consult lawyer',
            'note': 'RERA is complex; specific advice needed'
        }
    
    def get_trust_score(self, contract_data: Dict) -> int:
        """Calculate deal trust score (0-100)"""
        score = 100
        
        if not contract_data.get('is_registered'):
            score -= 25
        if not contract_data.get('title_clear'):
            score -= 15
        if contract_data.get('has_unfair_clauses'):
            score -= 20
        if contract_data.get('builder_exemptions'):
            score -= 15
        if contract_data.get('dispute_history'):
            score -= 10
        if not contract_data.get('stamp_duty_paid'):
            score -= 5
        
        return max(0, min(100, score))
