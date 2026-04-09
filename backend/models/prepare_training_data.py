"""
Data Preparation for RAG Fine-Tuning
"""

import pandas as pd
from pathlib import Path
from itertools import combinations
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Real Estate Synonyms
REAL_ESTATE_SYNONYMS = [
    ("2bhk", "2-bedroom apartment"),
    ("2bhk", "2 bedroom flat"),
    ("3bhk", "3-bedroom apartment"),
    ("gym", "fitness center"),
    ("gym", "exercise facility"),
    ("pool", "swimming pool"),
    ("parking", "parking space"),
    ("parking", "garage"),
    ("unfurnished", "bare shell"),
    ("unfurnished", "empty property"),
    ("furnished", "interior included"),
    ("ready to move", "possession available"),
    ("under construction", "under development"),
    ("metro connectivity", "public transport"),
    ("metro connectivity", "railway station nearby"),
    ("highway access", "road connectivity"),
    ("affordable housing", "budget property"),
    ("luxury property", "premium apartment"),
    ("rera registered", "government approved"),
]

# Fraud indicators
FRAUD_INDICATORS = [
    ("urgent limited time offer", "standard property listing"),
    ("cash only no questions asked", "transparent transaction"),
    ("below market price amazing deal", "fair market value property"),
]

# Market positive terms
MARKET_POSITIVE = [
    ("metro line opens soon", "new connectivity launching"),
    ("infrastructure development", "new projects coming"),
    ("price appreciation expected", "growth predicted"),
]

# Location associations
LOCATION_ASSOCIATIONS = [
    ("mumbai property", "mumbai apartment"),
    ("andheri west", "andheri locality"),
    ("bangalore property", "bangalore apartment"),
    ("pune real estate", "pune housing"),
    ("delhi property", "delhi apartment"),
]


def create_training_pairs_from_csv():
    """Create training pairs from existing news CSV files"""
    logger.info("🚀 Creating training pairs from CSV files...")
    training_pairs = []

    # Try to load news CSV
    csv_paths = [
        Path("Datasets/market_news_sample.csv"),
        Path("Datasets/real_estate_news_live.csv"),
        Path("../Datasets/market_news_sample.csv"),
        Path("../Datasets/real_estate_news_live.csv"),
    ]

    df_combined = None
    for csv_path in csv_paths:
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if df_combined is None:
                df_combined = df
            else:
                df_combined = pd.concat([df_combined, df], ignore_index=True)
            logger.info(f"✅ Loaded {len(df)} articles from {csv_path}")

    if df_combined is None:
        logger.warning("⚠️  No CSV files found. Using synthetic pairs only.")
        df_combined = pd.DataFrame()

    # RULE 1: Same location
    if not df_combined.empty and 'location' in df_combined.columns:
        logger.info("📍 Generating same-location pairs...")
        for location in df_combined['location'].unique():
            if pd.isna(location):
                continue
            location_articles = df_combined[df_combined['location'] == location]
            titles = location_articles['title'].dropna().tolist()
            for title1, title2 in combinations(titles[:4], 2):
                if len(title1) > 5 and len(title2) > 5:
                    training_pairs.append({
                        'sentence1': title1[:100],
                        'sentence2': title2[:100],
                        'similarity': 0.95,
                        'category': 'same_location'
                    })

    # RULE 2: Synonyms
    logger.info("📚 Adding real estate synonym pairs...")
    for term1, term2 in REAL_ESTATE_SYNONYMS:
        training_pairs.append({
            'sentence1': term1,
            'sentence2': term2,
            'similarity': 0.90,
            'category': 'synonyms'
        })

    # RULE 3: Market positive
    logger.info("🎯 Adding positive market indicator pairs...")
    for term1, term2 in MARKET_POSITIVE:
        training_pairs.append({
            'sentence1': term1,
            'sentence2': term2,
            'similarity': 0.88,
            'category': 'market_positive'
        })

    # RULE 4: Location associations
    logger.info("🗺️  Adding location association pairs...")
    for term1, term2 in LOCATION_ASSOCIATIONS:
        training_pairs.append({
            'sentence1': term1,
            'sentence2': term2,
            'similarity': 0.92,
            'category': 'location_associations'
        })

    # RULE 5: Fraud indicators
    logger.info("⚠️  Adding fraud indicator pairs...")
    for fraud, normal in FRAUD_INDICATORS:
        training_pairs.append({
            'sentence1': fraud,
            'sentence2': normal,
            'similarity': 0.15,
            'category': 'fraud_detection'
        })

    # RULE 6: Different locations
    if not df_combined.empty and 'location' in df_combined.columns:
        logger.info("🔀 Adding different-location pairs...")
        unique_locations = df_combined['location'].dropna().unique()[:10]
        for loc1, loc2 in combinations(unique_locations, 2):
            if loc1 and loc2 and loc1 != loc2:
                training_pairs.append({
                    'sentence1': f"Property in {loc1}",
                    'sentence2': f"Property in {loc2}",
                    'similarity': 0.20,
                    'category': 'different_location'
                })

    # Save to CSV
    df_pairs = pd.DataFrame(training_pairs)
    output_path = Path("backend/models/training_pairs.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_pairs.to_csv(output_path, index=False)

    logger.info(f"\n✅ Successfully created {len(training_pairs)} training pairs")
    logger.info(f"📊 Distribution:")
    for category in df_pairs['category'].unique():
        count = len(df_pairs[df_pairs['category'] == category])
        logger.info(f"   - {category}: {count} pairs")
    logger.info(f"\n💾 Training pairs saved to {output_path}")
    return df_pairs


if __name__ == "__main__":
    create_training_pairs_from_csv()
