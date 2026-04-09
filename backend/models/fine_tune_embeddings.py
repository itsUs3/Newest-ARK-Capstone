"""
Fine-Tune all-MiniLM-L6-v2 on Real Estate Domain
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path

try:
    import torch
    from sentence_transformers import SentenceTransformer, InputExample, losses
    from torch.utils.data import DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RAGFineTuner:
    """Fine-tunes sentence-transformers embeddings on real estate domain data"""

    def __init__(self, base_model: str = 'all-MiniLM-L6-v2'):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch and sentence-transformers required")
        self.base_model = base_model
        self.model = None
        self.output_path = Path(__file__).resolve().parent / "real_estate_embeddings"

    def load_training_data(self, csv_path: str) -> list:
        """Load training data from CSV"""
        logger.info(f"📖 Loading training data from {csv_path}")
        if not Path(csv_path).exists():
            raise FileNotFoundError(f"Training data not found at {csv_path}")
        df = pd.read_csv(csv_path)
        logger.info(f"✅ Loaded {len(df)} pairs")
        train_examples = [
            InputExample(texts=[str(row['sentence1']), str(row['sentence2'])],
                        label=float(row['similarity'])) for _, row in df.iterrows()
        ]
        logger.info(f"✅ Converted to {len(train_examples)} InputExample objects")
        return train_examples

    def fine_tune(self, train_examples: list, epochs: int = 5, batch_size: int = 16, warmup_steps: int = 100):
        """Fine-tune the embedding model"""
        logger.info("\n" + "="*80)
        logger.info("🚀 Starting Fine-Tuning")
        logger.info("="*80)
        logger.info(f"📚 Loading base model: {self.base_model}")
        self.model = SentenceTransformer(self.base_model)
        train_dataloader = DataLoader(train_examples, shuffle=True, batch_size=batch_size)
        train_loss = losses.CosineSimilarityLoss(self.model)
        logger.info(f"\n📊 Training Configuration:")
        logger.info(f"   - Total Pairs: {len(train_examples)}")
        logger.info(f"   - Epochs: {epochs}")
        logger.info(f"   - Batch Size: {batch_size}")
        logger.info(f"   - Warmup Steps: {warmup_steps}")
        logger.info("\n🎯 Starting training...\n")
        self.model.fit(
            train_objectives=[(train_dataloader, train_loss)],
            epochs=epochs,
            warmup_steps=warmup_steps,
            show_progress_bar=True,
        )
        logger.info("\n✅ Fine-tuning complete!")

    def save_model(self):
        """Save the fine-tuned model"""
        if self.model is None:
            logger.error("❌ No model to save")
            return False
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(str(self.output_path))
        logger.info(f"💾 Model saved to {self.output_path}")
        return True

    def test_model(self):
        """Test the fine-tuned model"""
        if self.model is None:
            logger.error("❌ No model loaded for testing")
            return
        logger.info("\n" + "="*80)
        logger.info("🧪 Testing Fine-Tuned Model")
        logger.info("="*80)
        test_cases = [
            ("2BHK apartment", "2-bedroom flat", "HIGH"),
            ("Metro connectivity", "Public transport access", "HIGH"),
            ("Ready to move", "Possession available", "HIGH"),
            ("Mumbai property", "Delhi property", "LOW"),
            ("Fraud alert", "Legitimate listing", "LOW"),
        ]
        logger.info(f"\n{'Text Pair':<50} {'Similarity':<12} {'Expected':<10}")
        logger.info("-" * 72)
        correct = 0
        for text1, text2, expected in test_cases:
            emb1 = self.model.encode(text1)
            emb2 = self.model.encode(text2)
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            if (expected == "HIGH" and similarity >= 0.8) or (expected == "LOW" and similarity < 0.5):
                correct += 1
                status = "✅"
            else:
                status = "⚠️"
            logger.info(f"{text1} vs {text2:<25} {similarity:.3f}        {expected:<10} {status}")
        accuracy = (correct / len(test_cases)) * 100
        logger.info("-" * 72)
        logger.info(f"\n📊 Test Accuracy: {accuracy:.1f}% ({correct}/{len(test_cases)} passed)")
        if accuracy >= 80:
            logger.info("✅ Model quality is GOOD")


def main():
    """Main execution flow"""
    logger.info("\n" + "="*80)
    logger.info("🎯 RAG Fine-Tuning Pipeline")
    logger.info("="*80)
    try:
        logger.info("\n[Step 1/3] Preparing training data...")
        from prepare_training_data import create_training_pairs_from_csv
        create_training_pairs_from_csv()
        logger.info("\n[Step 2/3] Fine-tuning model...")
        tuner = RAGFineTuner()
        train_examples = tuner.load_training_data("backend/models/training_pairs.csv")
        tuner.fine_tune(train_examples=train_examples, epochs=5, batch_size=16, warmup_steps=100)
        logger.info("\n[Step 3/3] Saving model...")
        tuner.save_model()
        tuner.test_model()
        logger.info("\n" + "="*80)
        logger.info("✅ Fine-tuning pipeline completed successfully!")
        logger.info("="*80)
        logger.info(f"\n📍 Fine-tuned model saved at: {tuner.output_path}")
        logger.info("🚀 The system will automatically use this model on next startup\n")
    except Exception as e:
        logger.error(f"\n❌ Fine-tuning failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
