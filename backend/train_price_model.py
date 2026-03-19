"""
Script to train the smart price predictor model
Run this once to train the model on real data
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from models.price_predictor import PricePredictor
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Train the price predictor model"""
    logger.info("=" * 80)
    logger.info("SMART PRICE PREDICTOR - MODEL TRAINING")
    logger.info("=" * 80)
    
    try:
        logger.info("Initializing Price Predictor...")
        predictor = PricePredictor()
        
        # Test a prediction
        logger.info("\n" + "=" * 80)
        logger.info("TESTING MODEL WITH SAMPLE PREDICTION")
        logger.info("=" * 80)
        
        test_features = {
            'location': 'Andheri West, Mumbai',
            'bhk': 2,
            'size': 1100,
            'amenities': ['gym', 'parking', 'security'],
            'furnishing': 'Semi-Furnished',
            'construction_status': 'Ready to Move'
        }
        
        logger.info(f"Input: {test_features}")
        result = predictor.predict(test_features)
        
        logger.info(f"\n✅ Prediction Results:")
        logger.info(f"   Predicted Price: ₹{result['predicted_price']/10000000:.2f} Cr")
        logger.info(f"   Price Range: ₹{result['price_range']['min']/10000000:.2f} Cr - ₹{result['price_range']['max']/10000000:.2f} Cr")
        logger.info(f"   Confidence: {result['confidence']*100:.1f}%")
        logger.info(f"   Market Trend: {result.get('market_trend', 'N/A')}")
        
        logger.info(f"\n📊 Price Factors:")
        for factor_name, factor_data in result['factors'].items():
            if isinstance(factor_data, dict):
                logger.info(f"   {factor_name}: {factor_data.get('impact', 'N/A')}")
                logger.info(f"      → {factor_data.get('description', 'N/A')}")
            else:
                logger.info(f"   {factor_name}: {factor_data}")
        
        # Get feature importance
        if hasattr(predictor, 'get_feature_importance'):
            importance = predictor.get_feature_importance()
            if importance:
                logger.info(f"\n🔍 Feature Importance:")
                for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"   {feature}: {score:.3f}")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ MODEL TRAINING COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info("The model is now ready to use in the API")
        logger.info("You can start the backend server with: uvicorn main:app --port 8000")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ ERROR: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
