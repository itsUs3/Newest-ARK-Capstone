"""
Advanced ML Training Script
For training and evaluating models with custom data
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import warnings
from config import DATA_PATH

warnings.filterwarnings('ignore')

class AdvancedModelTrainer:
    """Advanced ML model training for price prediction"""
    
    def __init__(self, data_path: str = str(DATA_PATH)):
        self.data_path = data_path
        self.df = None
        self.models = {}
        self.scalers = {}
        
    def load_data(self):
        """Load and explore data"""
        print("📊 Loading data...")
        self.df = pd.read_csv(self.data_path)
        print(f"✓ Loaded {len(self.df)} properties")
        print(f"✓ Columns: {self.df.columns.tolist()}")
        return self.df
    
    def prepare_features(self):
        """Extract and engineer features"""
        print("\n🔨 Preparing features...")
        
        df = self.df.copy()
        
        # Extract BHK
        df['bhk'] = df['title2'].fillna('').str.extract(r'(\d+)\s*BHK', expand=False).fillna(0).astype(int)
        
        # Extract location
        df['location'] = df['title2'].fillna('').str.extract(r'in\s+([^,]+)', expand=False).fillna('Unknown')
        
        # Filter valid entries
        df = df[df['bhk'] > 0].copy()
        
        # Synthetic features (would be real in production)
        np.random.seed(42)
        df['size'] = np.random.uniform(400, 3000, len(df))
        df['age'] = np.random.uniform(0, 50, len(df))
        df['price'] = (df['bhk'] * 800000 + 
                      df['size'] * 8000 + 
                      np.random.normal(0, 500000, len(df)))
        
        # Feature engineering
        df['price_per_sqft'] = df['price'] / df['size']
        df['rooms_per_size'] = df['bhk'] / df['size'] * 1000
        
        print(f"✓ Engineered features: {df.columns.tolist()}")
        print(f"✓ Valid properties: {len(df)}")
        
        return df
    
    def train_models(self, df):
        """Train multiple models"""
        print("\n🤖 Training models...")
        
        # Prepare data
        X = df[['bhk', 'size', 'age']].fillna(0)
        y = df['price']
        
        # Encode location
        le = LabelEncoder()
        location_encoded = le.fit_transform(df['location'])
        X['location'] = location_encoded
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        results = {}
        
        # 1. Linear Regression (baseline)
        print("\n  Training Linear Regression...")
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred = lr.predict(X_test)
        
        results['LinearRegression'] = {
            'model': lr,
            'r2': r2_score(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred)
        }
        print(f"    R² Score: {results['LinearRegression']['r2']:.4f}")
        print(f"    RMSE: ₹{results['LinearRegression']['rmse']:,.0f}")
        
        # 2. Random Forest (main model)
        print("\n  Training Random Forest...")
        rf = RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42)
        rf.fit(X_train, y_train)
        y_pred = rf.predict(X_test)
        
        results['RandomForest'] = {
            'model': rf,
            'r2': r2_score(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred),
            'features': X.columns.tolist(),
            'importances': rf.feature_importances_
        }
        print(f"    R² Score: {results['RandomForest']['r2']:.4f}")
        print(f"    RMSE: ₹{results['RandomForest']['rmse']:,.0f}")
        
        # Feature importance
        print("\n  Feature Importance:")
        for feat, imp in zip(X.columns, rf.feature_importances_):
            print(f"    {feat}: {imp:.4f}")
        
        # 3. Gradient Boosting (advanced)
        print("\n  Training Gradient Boosting...")
        gb = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        gb.fit(X_train, y_train)
        y_pred = gb.predict(X_test)
        
        results['GradientBoosting'] = {
            'model': gb,
            'r2': r2_score(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'mae': mean_absolute_error(y_test, y_pred)
        }
        print(f"    R² Score: {results['GradientBoosting']['r2']:.4f}")
        print(f"    RMSE: ₹{results['GradientBoosting']['rmse']:,.0f}")
        
        self.models = results
        self.scalers['scaler'] = scaler
        self.scalers['location_encoder'] = le
        
        return results
    
    def compare_models(self):
        """Compare model performances"""
        print("\n📊 Model Comparison:")
        print("-" * 60)
        print(f"{'Model':<20} {'R² Score':<15} {'RMSE':<15}")
        print("-" * 60)
        
        for name, data in self.models.items():
            print(f"{name:<20} {data['r2']:<15.4f} ₹{data['rmse']:>13,.0f}")
    
    def save_models(self):
        """Save trained models"""
        print("\n💾 Saving models...")
        
        for name, data in self.models.items():
            path = f"models/{name.lower().replace(' ', '_')}.pkl"
            with open(path, 'wb') as f:
                pickle.dump(data['model'], f)
            print(f"  ✓ Saved {name} to {path}")
        
        # Save scalers
        with open('models/scalers.pkl', 'wb') as f:
            pickle.dump(self.scalers, f)
        print("  ✓ Saved scalers")

def visualize_results(trainer):
    """Create visualizations"""
    print("\n📈 Creating visualizations...")
    
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # Prepare data
        df = trainer.prepare_features()
        
        # 1. Price distribution
        plt.figure(figsize=(12, 4))
        
        plt.subplot(1, 3, 1)
        plt.hist(df['price']/1000000, bins=20, color='indigo', alpha=0.7)
        plt.xlabel('Price (₹ Crores)')
        plt.ylabel('Count')
        plt.title('Price Distribution')
        
        # 2. BHK distribution
        plt.subplot(1, 3, 2)
        df['bhk'].value_counts().plot(kind='bar', color='pink')
        plt.xlabel('BHK')
        plt.ylabel('Count')
        plt.title('BHK Distribution')
        
        # 3. Model comparison
        plt.subplot(1, 3, 3)
        models = list(trainer.models.keys())
        scores = [trainer.models[m]['r2'] for m in models]
        plt.bar(models, scores, color=['indigo', 'pink', 'teal'])
        plt.ylabel('R² Score')
        plt.title('Model Performance')
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig('models/results.png', dpi=150, bbox_inches='tight')
        print("✓ Saved visualization to models/results.png")
        
    except Exception as e:
        print(f"⚠ Could not create visualization: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🏠 myNivas - Advanced ML Training")
    print("=" * 60)
    
    trainer = AdvancedModelTrainer()
    
    try:
        # Load data
        trainer.load_data()
        
        # Prepare features
        df = trainer.prepare_features()
        
        # Train models
        trainer.train_models(df)
        
        # Compare
        trainer.compare_models()
        
        # Save
        trainer.save_models()
        
        # Visualize
        visualize_results(trainer)
        
        print("\n" + "=" * 60)
        print("✅ Training Complete!")
        print("=" * 60)
        print("\n💡 Next Steps:")
        print("  1. Use RandomForest model - best balance of accuracy & speed")
        print("  2. Train with more data for better performance")
        print("  3. Adjust hyperparameters based on your use case")
        print("  4. Cross-validate with new properties")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
