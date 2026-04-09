"""
Multi-Domain RAG System
Expands RAG coverage to all important domains in real estate
Manages ChromaDB collections for different knowledge domains
"""

import os
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

os.environ.setdefault("ANONYMIZED_TELEMETRY", "FALSE")

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    from chromadb.config import Settings
    RAG_AVAILABLE = True
except Exception as e:
    SentenceTransformer = None
    chromadb = None
    Settings = None
    RAG_AVAILABLE = False

import config

logger = logging.getLogger(__name__)


class MultiDomainRAG:
    """
    Comprehensive RAG system covering all real estate domains:
    - Market News & Trends
    - RERA Laws & Regulations
    - Contract Templates & Legal
    - Property Features & Amenities
    - Fraud Patterns & Red Flags
    - Community Insights & Sentiment
    """

    DOMAINS = {
        "market_news": {
            "description": "Real estate market trends, price movements, news",
            "collection_name": "market_news"
        },
        "rera_laws": {
            "description": "RERA regulations, legal compliance, buyer rights",
            "collection_name": "rera_laws"
        },
        "contracts": {
            "description": "Contract templates, clauses, legal documents",
            "collection_name": "contracts"
        },
        "properties": {
            "description": "Property features, amenities, location guides",
            "collection_name": "properties"
        },
        "fraud_patterns": {
            "description": "Common fraud schemes, red flags, scam patterns",
            "collection_name": "fraud_patterns"
        },
        "community": {
            "description": "Community insights, neighborhood info, social sentiment",
            "collection_name": "community"
        }
    }

    def __init__(self, embedding_model: str = None, persist_dir: str = None):
        """
        Initialize multi-domain RAG system
        
        Args:
            embedding_model: Embedding model name (default: all-MiniLM-L6-v2)
            persist_dir: Directory for persistent ChromaDB storage
        """
        if not RAG_AVAILABLE:
            logger.warning("ChromaDB or sentence-transformers not available. RAG disabled.")
            self.available = False
            return
        
        self.available = True
        self.embedding_model_name = embedding_model or config.RAG_EMBEDDING_MODEL
        self.persist_dir = persist_dir or config.RAG_PERSIST_DIR
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Loaded embedding model: {self.embedding_model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.available = False
            return
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"Initialized ChromaDB at {self.persist_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.available = False
            return
        
        # Initialize/get collections for all domains
        self.collections = {}
        for domain_key, domain_info in self.DOMAINS.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=domain_info["collection_name"],
                    metadata={"domain": domain_key, "description": domain_info["description"]}
                )
                self.collections[domain_key] = collection
                logger.info(f"Initialized collection: {domain_info['collection_name']}")
            except Exception as e:
                logger.error(f"Failed to initialize collection {domain_key}: {e}")

    def add_documents(
        self,
        domain: str,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to a domain collection
        
        Args:
            domain: Domain key (market_news, rera_laws, etc.)
            documents: List of document texts
            metadatas: List of metadata dicts for each document
            doc_ids: Optional document IDs
        
        Returns:
            Success status
        """
        if not self.available or domain not in self.collections:
            logger.warning(f"Domain {domain} not available for adding documents")
            return False
        
        try:
            collection = self.collections[domain]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(documents)
            
            # Prepare metadata
            if metadatas is None:
                metadatas = [{"domain": domain} for _ in documents]
            else:
                for meta in metadatas:
                    meta["domain"] = domain
            
            # Generate IDs if not provided
            if doc_ids is None:
                doc_ids = [f"{domain}_{i}_{int(datetime.now().timestamp())}" for i in range(len(documents))]
            
            # Add to collection
            collection.add(
                embeddings=embeddings.tolist(),
                documents=documents,
                metadatas=metadatas,
                ids=doc_ids
            )
            
            logger.info(f"Added {len(documents)} documents to {domain} collection")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to {domain}: {e}")
            return False

    def search(
        self,
        domain: str,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Tuple[str, float, Dict]]:
        """
        Search within a specific domain
        
        Args:
            domain: Domain to search in
            query: Search query
            top_k: Number of results to return
            filters: Optional filter criteria
        
        Returns:
            List of (document_text, similarity_score, metadata) tuples
        """
        if not self.available or domain not in self.collections:
            logger.warning(f"Domain {domain} not available for search")
            return []
        
        try:
            collection = self.collections[domain]
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query).tolist()
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filters if filters else None
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]
                distances = results['distances'][0] if results['distances'] else [0] * len(docs)
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs)
                
                for doc, distance, meta in zip(docs, distances, metadatas):
                    # Convert distance to similarity (ChromaDB uses L2 distance)
                    similarity = 1 / (1 + distance) if distance is not None else 0
                    formatted_results.append((doc, similarity, meta))
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching domain {domain}: {e}")
            return []

    def search_all_domains(
        self,
        query: str,
        top_k_per_domain: int = 3
    ) -> Dict[str, List[Tuple[str, float, Dict]]]:
        """
        Search across all domains
        
        Args:
            query: Search query
            top_k_per_domain: Results per domain
        
        Returns:
            Dict mapping domain names to results
        """
        results = {}
        
        for domain in self.DOMAINS.keys():
            results[domain] = self.search(domain, query, top_k=top_k_per_domain)
        
        return results

    def get_domain_summary(self, domain: str) -> Dict:
        """Get information about a domain collection"""
        if not self.available or domain not in self.collections:
            return {}
        
        try:
            collection = self.collections[domain]
            count = collection.count()
            
            return {
                "domain": domain,
                "description": self.DOMAINS[domain]["description"],
                "collection_name": self.DOMAINS[domain]["collection_name"],
                "document_count": count,
                "embedding_model": self.embedding_model_name
            }
        except Exception as e:
            logger.error(f"Error getting summary for {domain}: {e}")
            return {}

    def get_all_summaries(self) -> Dict[str, Dict]:
        """Get summaries of all domain collections"""
        summaries = {}
        
        for domain in self.DOMAINS.keys():
            summary = self.get_domain_summary(domain)
            if summary:
                summaries[domain] = summary
        
        return summaries

    def initialize_default_content(self) -> bool:
        """
        Initialize domains with default/sample content
        Loads from provided CSV files or creates defaults
        """
        try:
            # Initialize Market News domain
            if config.RAG_NEWS_CSV_PATH.exists():
                self._load_market_news()
            
            # Initialize RERA Laws domain
            self._initialize_rera_laws()
            
            # Initialize Fraud Patterns domain
            self._initialize_fraud_patterns()
            
            # Initialize Community domain
            self._initialize_community_domain()
            
            logger.info("Initialized default content for all domains")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing default content: {e}")
            return False

    def _load_market_news(self):
        """Load market news from CSV"""
        try:
            import pandas as pd
            df = pd.read_csv(config.RAG_NEWS_CSV_PATH)
            
            docs = []
            metadatas = []
            
            for idx, row in df.iterrows():
                title = row.get('title', '')
                content = row.get('content', '')
                source = row.get('source', 'Unknown')
                
                doc = f"{title}\n{content}"
                docs.append(doc)
                metadatas.append({
                    "source": source,
                    "date": str(row.get('date', datetime.now().isoformat())),
                    "title": title
                })
            
            if docs:
                self.add_documents("market_news", docs, metadatas)
                logger.info(f"Loaded {len(docs)} market news articles")
        
        except Exception as e:
            logger.warning(f"Could not load market news CSV: {e}")

    def _initialize_rera_laws(self):
        """Initialize RERA laws and regulations"""
        rera_content = [
            "RERA Section 19: Authority must adjudicate complaint within 60 days. Extension of 30 days allowed if complex investigation needed. Penalties up to ₹10 lakh for non-compliance.",
            "Section 18 Rights: Every property buyer has right to receive possession of project within agreed timeline. Failure to do so entitles buyer to refund with interest.",
            "Project Registration: All ongoing and new projects must be registered within 14 days of receiving planning permission. Non-registration is violation of RERA.",
            "Structural Defect Liability: Developer liable for structural defects up to 5 years from date of possession. Buyer can demand repair or refund.",
            "Maintenance of Accounts: Builders must maintain separate bank account for project funds. No mixing of project money with personal funds.",
            "Section 12 Obligations: Promoter must display layout plan, sanctioned plans, status certificate, estimate of total cost, and completion timeline.",
            "Cancellation Rights: Buyer can cancel buyer's agreement without penalty and get refund with interest if project is cancelled or is abandoned.",
            "Phase-wise Development: Completion percentage of various phases must be clearly communicated. Buyer cannot be forced to take possession before phase completion."
        ]
        
        metadatas = [
            {"source": "RERA Act", "category": "Buyer Rights", "section": f"Section {i}"} 
            for i in range(1, len(rera_content) + 1)
        ]
        
        self.add_documents("rera_laws", rera_content, metadatas)

    def _initialize_fraud_patterns(self):
        """Initialize common fraud patterns and red flags"""
        fraud_content = [
            "Land title fraud: Fake ownership documents, forged property deeds, and unauthorized transfer of property by non-owners. Verify all papers with government records.",
            "Advance fraud: Scammers demand large advance payments for non-existent properties or for properties they don't own. Always verify seller identity and payment to authorized parties.",
            "Document forgery: Fake sale deeds, fake mutations, fake tax receipts. Verify all documents with concerned government offices.",
            "Financing fraud: False representations about property, mortgage fraud involving falsified documents, or fake loan approvals.",
            "Possession fraud: Properties where multiple possession documents given or where possession never transferred despite payment.",
            "Sub-prime property: Auctioned properties, properties with legal claims, or properties on sensitive lands sold fraudulently.",
            "Bait and switch: Agent shows one property, buyer buys different one. Always verify exact property details independently.",
            "Builder abandonment: Developer abandons project, leaves property incomplete, disappears. Check developer track record and financial statements.",
            "Unauthorized construction: Structure built beyond approved plan, illegal structures, or structures in restricted areas causing future demolition.",
            "Undisclosed liabilities: Properties with outstanding dues, loans, or legal cases not disclosed. Get legal opinion before purchasing."
        ]
        
        metadatas = [
            {"source": "Fraud Database", "risk_level": "High", "type": "Common Scam"} 
            for _ in fraud_content
        ]
        
        self.add_documents("fraud_patterns", fraud_content, metadatas)

    def _initialize_community_domain(self):
        """Initialize community and location insights"""
        community_content = [
            "Mumbai's Bandra locality is known for nightlife, cafes, and cultural events. Prime location with high property appreciation. Good connectivity via metro and roads.",
            "Bangalore's Indiranagar offers IT hub proximity, good restaurants, and family-friendly environment. Growing commercial space with steady appreciation.",
            "Delhi's South Delhi areas like Hauz Khas offer excellent connectivity, malls, parks and high property values. Upscale neighborhood with good schools.",
            "Pune's Hinjewadi is IT hub with modern infrastructure, good connectivity, and young demographic. Rapidly developing area with strong rental demand.",
            "Hyderabad's Gachibowli offers IT presence, malls, restaurants, and good infrastructure. Regular appreciation and balanced demographic.",
            "Location accessibility: Properties near metro stations command 15-20% premium. Walkability to shops/schools affects resale value.",
            "School proximity: Properties within 2km of top-rated schools see 20-30% higher buyer interest. Impacts family demographics.",
            "Traffic and commute: Areas with high traffic suffer 10-15% valuation lower compared to low-traffic areas. Affects buyer quality.",
            "Green spaces: Properties near parks/gardens command 10% premium. Impact on health, community, and property value appreciation.",
            "Water and power: Areas with regular power cuts, water issues see lower demand and values. Infrastructure reliability is key factor."
        ]
        
        metadatas = [
            {"source": "Community Feedback", "category": "Location Insight", "reliability": "Good"} 
            for _ in community_content
        ]
        
        self.add_documents("community", community_content, metadatas)

    def delete_documents(self, domain: str, doc_ids: List[str]) -> bool:
        """Delete specific documents from a domain"""
        if not self.available or domain not in self.collections:
            return False
        
        try:
            collection = self.collections[domain]
            collection.delete(ids=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents from {domain}")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents from {domain}: {e}")
            return False

    def reset_domain(self, domain: str) -> bool:
        """Clear all documents from a domain collection"""
        if not self.available or domain not in self.collections:
            return False
        
        try:
            collection = self.collections[domain]
            # Get all IDs and delete
            all_docs = collection.get()
            if all_docs and all_docs['ids']:
                collection.delete(ids=all_docs['ids'])
            logger.info(f"Reset domain {domain}")
            return True
        except Exception as e:
            logger.error(f"Error resetting domain {domain}: {e}")
            return False
