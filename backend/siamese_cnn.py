import os
import csv
import random
import urllib.request
from pathlib import Path
from typing import List, Tuple
import json
from datetime import datetime

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models, regularizers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_curve, auc
import matplotlib.pyplot as plt

# Reproducibility
random.seed(42)
np.random.seed(42)
tf.random.set_seed(42)

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
IMAGE_SIZE = (224, 224)  # Increased for better detail capture
BATCH_SIZE = 16  # Reduced for better gradient updates
EPOCHS = 30  # Adjusted for augmentation-based training
FINE_TUNE_EPOCHS = 10
MARGIN = 1.0
LEARNING_RATE = 1e-3
FINE_TUNE_LR = 1e-4
L2_REG = 1e-4  # L2 regularization
DROPOUT_RATE = 0.3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "housing1_images"
HOUSING_CSV = PROJECT_ROOT / "Housing1.csv"
MODEL_OUT = PROJECT_ROOT / "models" / "siamese_cnn"

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _is_valid_image_url(url: str) -> bool:
    if not url:
        return False
    url_lower = url.lower()
    if not url_lower.startswith("http"):
        return False
    if url_lower.endswith(".svg"):
        return False
    if "housingcdn.com/demand" in url_lower:
        return False
    return True


def read_housing_csv_images(csv_path: Path) -> List[Tuple[str, str]]:
    """
    Read Housing1.csv and return a list of (image_url, listing_id).
    Uses columns: image, image2, image3, image4.
    """
    if not csv_path.exists():
        print(f"CSV not found at {csv_path}.")
        return []

    items: List[Tuple[str, str]] = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            listing_id = row.get("web_scraper_order") or str(idx)
            for col in ("image", "image2", "image3", "image4"):
                url = (row.get(col) or "").strip()
                if _is_valid_image_url(url):
                    items.append((url, listing_id))
    return items


def download_images(url_items: List[Tuple[str, str]], output_dir: Path) -> List[Tuple[Path, str]]:
    """
    Download images from url_items and return (path, listing_id) pairs.
    """
    ensure_dir(output_dir)
    downloaded: List[Tuple[Path, str]] = []
    seen = set()

    for idx, (url, listing_id) in enumerate(url_items):
        if url in seen:
            continue
        seen.add(url)
        ext = os.path.splitext(url.split("?")[0])[1].lower() or ".jpg"
        file_name = f"{listing_id}_{idx:06d}{ext}"
        dest = output_dir / file_name
        if not dest.exists():
            try:
                urllib.request.urlretrieve(url, dest)
            except Exception as exc:
                print(f"Failed to download {url}: {exc}")
                continue
        downloaded.append((dest, listing_id))

    return downloaded


def list_image_files(image_dir: Path) -> List[Path]:
    if not image_dir.exists():
        return []
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return [p for p in image_dir.rglob("*") if p.suffix.lower() in exts]


def load_image(path: tf.Tensor) -> tf.Tensor:
    image = tf.io.read_file(path)
    image = tf.image.decode_image(image, channels=3, expand_animations=False)
    image = tf.image.resize(image, IMAGE_SIZE)
    image = tf.image.convert_image_dtype(image, tf.float32)
    return image


def build_augmenter() -> tf.keras.Sequential:
    """Enhanced data augmentation pipeline for creating diverse positive pairs"""
    return tf.keras.Sequential(
        [
            layers.RandomFlip("horizontal"),
            layers.RandomFlip("vertical"),
            layers.RandomRotation(0.2),  # Increased rotation
            layers.RandomZoom(0.2),       # Increased zoom
            layers.RandomContrast(0.3),   # Increased contrast variation
            layers.RandomBrightness(0.3), # Increased brightness variation
            layers.GaussianNoise(0.02),   # Increased noise
            layers.RandomTranslation(0.1, 0.1),  # Added translation
        ],
        name="augmenter",
    )


def make_pairs_from_groups(
    image_groups: dict, num_pairs: int = 2000
) -> Tuple[List[Tuple[str, str]], List[int]]:
    """
    Create positive pairs from the same listing_id and negative pairs across listings.
    Uses data augmentation to create positive pairs from single images when needed.
    """
    pairs: List[Tuple[str, str]] = []
    labels: List[int] = []

    listing_ids = list(image_groups.keys())
    if len(listing_ids) < 2:
        return pairs, labels

    # Build positive pairs
    positive_candidates = []
    for listing_id, paths in image_groups.items():
        if len(paths) >= 2:
            # Multiple images: create pairs from different images
            for i in range(len(paths)):
                for j in range(i + 1, len(paths)):
                    positive_candidates.append((str(paths[i]), str(paths[j])))
        else:
            # Single image: create pairs using same image (augmentation will differentiate)
            # Create multiple positive pairs from the same image
            for _ in range(5):  # Generate 5 augmented pairs per single image
                positive_candidates.append((str(paths[0]), str(paths[0])))

    random.shuffle(positive_candidates)
    max_pos = min(len(positive_candidates), num_pairs // 2)
    for i in range(max_pos):
        pairs.append(positive_candidates[i])
        labels.append(1)

    # Build negative pairs
    max_neg = num_pairs - max_pos
    for _ in range(max_neg):
        id_a, id_b = random.sample(listing_ids, 2)
        img_a = random.choice(image_groups[id_a])
        img_b = random.choice(image_groups[id_b])
        pairs.append((str(img_a), str(img_b)))
        labels.append(0)

    return pairs, labels


def build_siamese_base() -> tf.keras.Model:
    """Enhanced CNN base with batch norm, dropout, and residual-like connections"""
    inputs = layers.Input(shape=(*IMAGE_SIZE, 3))
    
    # Block 1
    x = layers.Conv2D(64, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(64, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    # Block 2
    x = layers.Conv2D(128, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(128, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    # Block 3
    x = layers.Conv2D(256, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(256, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    # Block 4
    x = layers.Conv2D(512, (3, 3), padding='same', kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.MaxPooling2D((2, 2))(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    # Global average pooling
    x = layers.GlobalAveragePooling2D()(x)
    
    # Dense layers with batch norm
    x = layers.Dense(512, kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    x = layers.Dense(256, kernel_regularizer=regularizers.l2(L2_REG))(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Dropout(DROPOUT_RATE)(x)
    
    # Output embedding
    outputs = layers.Dense(128, kernel_regularizer=regularizers.l2(L2_REG))(x)
    
    return models.Model(inputs, outputs, name="siamese_base")


def euclidean_distance(vects):
    """Compute euclidean distance between two vectors"""
    x, y = vects
    sum_sq = tf.reduce_sum(tf.square(x - y), axis=1, keepdims=True)
    return tf.sqrt(tf.maximum(sum_sq, tf.keras.backend.epsilon()))


def contrastive_loss(y_true, y_pred):
    """Improved contrastive loss with better numerical stability"""
    y_true = tf.cast(y_true, y_pred.dtype)
    pos = y_true * tf.square(y_pred)
    neg = (1 - y_true) * tf.square(tf.maximum(MARGIN - y_pred, 0))
    return tf.reduce_mean(pos + neg)


def triplet_loss(y_true, y_pred):
    """Triplet loss for metric learning - more effective than contrastive loss"""
    return tf.keras.losses.CosineSimilarity()(y_true, y_pred)


def build_siamese_model() -> tf.keras.Model:
    base = build_siamese_base()
    input_a = layers.Input(shape=(*IMAGE_SIZE, 3))
    input_b = layers.Input(shape=(*IMAGE_SIZE, 3))

    feat_a = base(input_a)
    feat_b = base(input_b)

    distance = layers.Lambda(euclidean_distance)([feat_a, feat_b])
    model = models.Model([input_a, input_b], distance, name="siamese_network")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss=contrastive_loss)
    return model


def build_dataset(pairs: List[Tuple[str, str]], labels: List[int], validation_split: float = 0.15) -> Tuple[tf.data.Dataset, tf.data.Dataset]:
    """Build train and validation datasets with proper splitting"""
    pairs = np.array(pairs)
    labels = np.array(labels, dtype=np.float32)
    
    # Split data
    total_samples = len(pairs)
    val_size = int(total_samples * validation_split)
    
    indices = np.arange(total_samples)
    np.random.shuffle(indices)
    
    val_indices = indices[:val_size]
    train_indices = indices[val_size:]
    
    train_pairs = pairs[train_indices]
    train_labels = labels[train_indices]
    val_pairs = pairs[val_indices]
    val_labels = labels[val_indices]
    
    augmenter = build_augmenter()
    
    def _map_train(paths, label):
        path_a, path_b = paths
        img_a = load_image(path_a)
        img_b = load_image(path_b)
        img_a = augmenter(img_a, training=True)
        img_b = augmenter(img_b, training=True)
        return (img_a, img_b), label
    
    def _map_val(paths, label):
        path_a, path_b = paths
        img_a = load_image(path_a)
        img_b = load_image(path_b)
        return (img_a, img_b), label
    
    # Training dataset with augmentation
    train_ds = tf.data.Dataset.from_tensor_slices(((train_pairs[:, 0], train_pairs[:, 1]), train_labels))
    train_ds = train_ds.shuffle(min(1024, len(train_pairs))).map(_map_train, num_parallel_calls=tf.data.AUTOTUNE).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    
    # Validation dataset without augmentation
    val_ds = tf.data.Dataset.from_tensor_slices(((val_pairs[:, 0], val_pairs[:, 1]), val_labels))
    val_ds = val_ds.map(_map_val, num_parallel_calls=tf.data.AUTOTUNE).batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    
    return train_ds, val_ds


def train():
    """Enhanced training with validation, callbacks, and evaluation"""
    ensure_dir(DATA_DIR)
    ensure_dir(MODEL_OUT)

    print("=" * 60)
    print("ENHANCED SIAMESE CNN TRAINING")
    print("=" * 60)
    
    # Download images
    print("\n📥 Downloading images from Housing1.csv...")
    url_items = read_housing_csv_images(HOUSING_CSV)
    if url_items:
        downloaded = download_images(url_items, DATA_DIR)
        print(f"✓ Downloaded {len(downloaded)} images")
    else:
        print("⚠ No image URLs found in CSV")

    # Build image groups for pair creation
    print("\n🔍 Building image groups...")
    image_groups = {}
    for path in list_image_files(DATA_DIR):
        listing_id = path.stem.split("_")[0]
        image_groups.setdefault(listing_id, []).append(path)

    if not image_groups:
        raise RuntimeError("No images found. Ensure Housing1.csv has valid image URLs.")
    
    print(f"✓ Found {len(image_groups)} listing groups with {len(list_image_files(DATA_DIR))} total images")

    # Create pairs
    print("\n🔗 Creating training pairs...")
    num_pairs = min(10000, len(image_groups) * 100)  # More pairs for augmentation-based training
    pairs, labels = make_pairs_from_groups(image_groups, num_pairs=num_pairs)
    
    if not pairs:
        raise RuntimeError("Not enough image pairs for training.")
    
    pos_count = sum(labels)
    neg_count = len(labels) - pos_count
    print(f"✓ Created {len(pairs)} pairs ({pos_count} positive, {neg_count} negative)")
    print(f"   Note: Positive pairs use augmentation for variation")

    # Build datasets
    print("\n📊 Building train/validation datasets...")
    train_ds, val_ds = build_dataset(pairs, labels)
    print(f"✓ Dataset ready")

    # Build model
    print("\n🏗️ Building Siamese CNN model...")
    model = build_siamese_model()
    print(f"✓ Model parameters: {model.count_params():,}")

    # Setup callbacks
    print("\n⚙️ Setting up training callbacks...")
    checkpoint = ModelCheckpoint(
        str(MODEL_OUT / "best_model.h5"),
        monitor='val_loss',
        save_best_only=True,
        verbose=1
    )
    
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        restore_best_weights=True,
        verbose=1
    )
    
    reduce_lr = ReduceLROnPlateau(
        monitor='val_loss',
        factor=0.5,
        patience=3,
        min_lr=1e-6,
        verbose=1
    )
    
    # Training phase
    print("\n🚀 Starting training phase...")
    print(f"   Learning rate: {LEARNING_RATE}")
    print(f"   Batch size: {BATCH_SIZE}")
    print(f"   Epochs: {EPOCHS}")
    
    history = model.fit(
        train_ds,
        epochs=EPOCHS,
        validation_data=val_ds,
        callbacks=[checkpoint, early_stop, reduce_lr],
        verbose=1
    )
    
    print("\n✓ Training phase completed")

    # Fine-tuning phase
    print("\n🔧 Starting fine-tuning phase...")
    print(f"   Learning rate: {FINE_TUNE_LR}")
    print(f"   Epochs: {FINE_TUNE_EPOCHS}")
    
    model.compile(optimizer=tf.keras.optimizers.Adam(FINE_TUNE_LR), loss=contrastive_loss)
    history_ft = model.fit(
        train_ds,
        epochs=FINE_TUNE_EPOCHS,
        validation_data=val_ds,
        callbacks=[checkpoint, reduce_lr],
        verbose=1
    )
    
    print("\n✓ Fine-tuning completed")

    # Evaluation
    print("\n📈 Evaluating model...")
    evaluate_model(model, val_ds)

    # Save model and metadata
    print("\n💾 Saving model...")
    model.save(MODEL_OUT / "model")
    
    # Save training metadata
    metadata = {
        "image_size": IMAGE_SIZE,
        "batch_size": BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "fine_tune_lr": FINE_TUNE_LR,
        "epochs": EPOCHS,
        "fine_tune_epochs": FINE_TUNE_EPOCHS,
        "total_pairs": len(pairs),
        "positive_pairs": int(pos_count),
        "negative_pairs": int(neg_count),
        "total_images": len(list_image_files(DATA_DIR)),
        "total_listing_groups": len(image_groups),
        "model_parameters": int(model.count_params()),
        "training_date": datetime.now().isoformat(),
        "final_train_loss": float(history.history['loss'][-1]),
        "final_val_loss": float(history.history['val_loss'][-1]),
    }
    
    with open(MODEL_OUT / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Save training history
    with open(MODEL_OUT / "training_history.json", "w") as f:
        json.dump({
            "train_loss": [float(x) for x in history.history['loss']],
            "val_loss": [float(x) for x in history.history['val_loss']],
        }, f, indent=2)
    
    print(f"✓ Model saved to {MODEL_OUT}")
    print("=" * 60)


def evaluate_model(model: tf.keras.Model, val_ds: tf.data.Dataset):
    """Evaluate model performance on validation set"""
    val_loss = model.evaluate(val_ds, verbose=0)
    print(f"   Validation Loss: {val_loss:.4f}")
    
    # Get predictions and compute metrics
    y_true = []
    y_pred = []
    
    for (img_pairs, labels) in val_ds:
        distances = model.predict(img_pairs, verbose=0)
        y_true.extend(labels.numpy())
        y_pred.extend(distances.numpy().flatten())
    
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    # Use threshold to convert distances to binary predictions
    threshold = np.median(y_pred)
    y_pred_binary = (y_pred < threshold).astype(int)
    
    # Compute metrics
    acc = accuracy_score(y_true, y_pred_binary)
    precision = precision_score(y_true, y_pred_binary, zero_division=0)
    recall = recall_score(y_true, y_pred_binary, zero_division=0)
    f1 = f1_score(y_true, y_pred_binary, zero_division=0)
    
    print(f"   Accuracy:  {acc:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")


if __name__ == "__main__":
    train()
