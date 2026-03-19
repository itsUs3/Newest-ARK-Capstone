import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

try:
    import tensorflow as tf
    from tensorflow.keras.applications.efficientnet import EfficientNetB0, preprocess_input
    from tensorflow.keras.preprocessing import image
except Exception:
    tf = None
    EfficientNetB0 = None
    preprocess_input = None
    image = None

logger = logging.getLogger(__name__)


class ImageFeatureExtractor:
    """EfficientNetB0-based image embedding extractor for property condition signals."""

    def __init__(self, target_size: tuple[int, int] = (224, 224), batch_size: int = 16):
        self.target_size = target_size
        self.batch_size = max(1, int(batch_size))
        self.embedding_dim = 1280
        self.model = None

        if tf is None or EfficientNetB0 is None:
            logger.warning("TensorFlow/EfficientNet unavailable. Falling back to zero embeddings.")
            return

        try:
            # CPU-friendly configuration; no GPU dependency is required.
            self.model = EfficientNetB0(include_top=False, weights="imagenet", pooling="avg")
            logger.info("EfficientNetB0 image feature extractor initialized")
        except Exception as exc:
            logger.warning(f"Failed to initialize EfficientNetB0: {exc}")
            self.model = None

    def _normalize_embedding(self, embedding: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(embedding)
        if norm <= 1e-12:
            return embedding
        return embedding / norm

    def zero_embedding(self) -> np.ndarray:
        return np.zeros(self.embedding_dim, dtype=np.float32)

    def _load_image_tensor(self, image_path: str) -> Optional[np.ndarray]:
        if image is None or preprocess_input is None:
            return None

        try:
            img = image.load_img(image_path, target_size=self.target_size)
            arr = image.img_to_array(img)
            return arr
        except Exception as exc:
            logger.debug(f"Unable to load image {image_path}: {exc}")
            return None

    def extract_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract normalized 1280-d embedding from a single image path."""
        if self.model is None or preprocess_input is None or not image_path or not Path(image_path).exists():
            return self.zero_embedding()

        arr = self._load_image_tensor(image_path)
        if arr is None:
            return self.zero_embedding()

        try:
            batch = np.expand_dims(arr, axis=0)
            batch = preprocess_input(batch)
            embedding = self.model.predict(batch, verbose=0)[0].astype(np.float32)
            return self._normalize_embedding(embedding)
        except Exception as exc:
            logger.debug(f"Embedding extraction failed for {image_path}: {exc}")
            return self.zero_embedding()

    def extract_batch_embeddings(self, image_paths: List[Optional[str]]) -> np.ndarray:
        """
        Batch extract normalized embeddings.
        Uses memory-efficient chunked inference and fills missing images with zero vectors.
        """
        count = len(image_paths)
        output = np.zeros((count, self.embedding_dim), dtype=np.float32)

        if self.model is None or preprocess_input is None or count == 0:
            return output

        valid_indices: List[int] = []
        valid_tensors: List[np.ndarray] = []

        for idx, path in enumerate(image_paths):
            if not path:
                continue
            p = str(path)
            if not Path(p).exists():
                continue
            tensor = self._load_image_tensor(p)
            if tensor is None:
                continue
            valid_indices.append(idx)
            valid_tensors.append(tensor)

        if not valid_indices:
            return output

        for start in range(0, len(valid_indices), self.batch_size):
            end = start + self.batch_size
            batch_indices = valid_indices[start:end]
            batch_tensors = np.array(valid_tensors[start:end], dtype=np.float32)
            try:
                batch_tensors = preprocess_input(batch_tensors)
                batch_embeddings = self.model.predict(batch_tensors, verbose=0).astype(np.float32)
                for i, emb in enumerate(batch_embeddings):
                    output_idx = batch_indices[i]
                    output[output_idx] = self._normalize_embedding(emb)
            except Exception as exc:
                logger.debug(f"Batch embedding extraction failed for indices {batch_indices}: {exc}")

        return output
