"""ONNX-based embedding generation with proper shape handling."""

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from typing import List, Union
import os
import logging
from .config import settings


logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generate embeddings using ONNX model with consistent shape handling."""

    def __init__(self):
        """Initialize with ONNX model."""
        model_path = settings.onnx_model_path

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"ONNX model not found at {model_path}. "
                f"Please run 'python scripts/download_model.py' first."
            )

        # Initialize ONNX session with optimization
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = (
            ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        )

        self.session = ort.InferenceSession(
            model_path, sess_options=sess_options, providers=["CPUExecutionProvider"]
        )

        # Initialize tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "sentence-transformers/all-MiniLM-L6-v2", clean_up_tokenization_spaces=True
        )

        # Model configuration
        self.max_length = 256
        self.embedding_dim = 384

        logger.info(f"Initialized embedding engine with model: {model_path}")

    def encode(
        self, texts: Union[str, List[str]], normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text string or list of texts
            normalize: Whether to L2-normalize the embeddings

        Returns:
            1D array (shape: [embedding_dim]) for single text
            2D array (shape: [n_texts, embedding_dim]) for multiple texts
        """
        # Track if input was single text
        single_text = isinstance(texts, str)
        if single_text:
            texts = [texts]

        if not texts:
            return np.array([])

        # Tokenize with proper error handling
        try:
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="np",
                return_attention_mask=True,
                return_token_type_ids=True,
            )
        except Exception as e:
            logger.error(f"Tokenization error: {e}")
            # Return zero embeddings on error
            if single_text:
                return np.zeros(self.embedding_dim, dtype=np.float32)
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

        # Prepare inputs
        input_ids = encoded["input_ids"].astype(np.int64)
        attention_mask = encoded["attention_mask"].astype(np.int64)

        # Handle token_type_ids (some models don't use them)
        if "token_type_ids" in encoded:
            token_type_ids = encoded["token_type_ids"].astype(np.int64)
        else:
            token_type_ids = np.zeros_like(input_ids, dtype=np.int64)

        # Run inference
        try:
            outputs = self.session.run(
                None,
                {
                    "input_ids": input_ids,
                    "attention_mask": attention_mask,
                    "token_type_ids": token_type_ids,
                },
            )
        except Exception as e:
            logger.error(f"ONNX inference error: {e}")
            # Return zero embeddings on error
            if single_text:
                return np.zeros(self.embedding_dim, dtype=np.float32)
            return np.zeros((len(texts), self.embedding_dim), dtype=np.float32)

        # Extract embeddings (last hidden state)
        last_hidden_state = outputs[0]

        # Mean pooling over tokens
        embeddings = self._mean_pooling(last_hidden_state, attention_mask)

        # Normalize if requested
        if normalize:
            embeddings = self._normalize_embeddings(embeddings)

        # Return appropriate shape
        if single_text:
            # Return 1D array for single text
            return embeddings[0]
        else:
            # Return 2D array for multiple texts
            return embeddings

    def encode_batch(
        self, texts: List[str], batch_size: int = 32, normalize: bool = True
    ) -> np.ndarray:
        """
        Encode texts in batches for efficiency.

        Args:
            texts: List of texts to encode
            batch_size: Number of texts to process at once
            normalize: Whether to L2-normalize the embeddings

        Returns:
            2D array of shape [n_texts, embedding_dim]
        """
        if not texts:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)

        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Always process as list to get 2D output
            embeddings = self.encode(batch, normalize=normalize)

            # Ensure 2D shape
            if embeddings.ndim == 1:
                embeddings = embeddings.reshape(1, -1)

            all_embeddings.append(embeddings)

        # Stack all batches
        result = (
            np.vstack(all_embeddings)
            if all_embeddings
            else np.zeros((0, self.embedding_dim), dtype=np.float32)
        )

        # Ensure float32 dtype
        return result.astype(np.float32)

    def _mean_pooling(
        self, last_hidden_state: np.ndarray, attention_mask: np.ndarray
    ) -> np.ndarray:
        """
        Apply mean pooling to token embeddings.

        Args:
            last_hidden_state: Token embeddings [batch_size, seq_len, hidden_dim]
            attention_mask: Attention mask [batch_size, seq_len]

        Returns:
            Pooled embeddings [batch_size, hidden_dim]
        """
        # Expand attention mask to match embedding dimensions
        input_mask_expanded = attention_mask[..., None].astype(np.float32)

        # Sum embeddings for non-padding tokens
        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)

        # Count non-padding tokens
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)

        # Average
        return sum_embeddings / sum_mask

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """
        L2-normalize embeddings.

        Args:
            embeddings: Embeddings to normalize

        Returns:
            Normalized embeddings
        """
        if embeddings.ndim == 1:
            # Single embedding
            norm = np.linalg.norm(embeddings)
            if norm > 0:
                return embeddings / norm
            return embeddings
        else:
            # Multiple embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            norms = np.clip(norms, a_min=1e-9, a_max=None)
            return embeddings / norms

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Cosine similarity score between -1 and 1
        """
        # Ensure 1D arrays
        if embedding1.ndim > 1:
            embedding1 = embedding1.squeeze()
        if embedding2.ndim > 1:
            embedding2 = embedding2.squeeze()

        # Normalize
        embedding1 = self._normalize_embeddings(embedding1)
        embedding2 = self._normalize_embeddings(embedding2)

        # Dot product
        return float(np.dot(embedding1, embedding2))

    def batch_similarity(
        self, query_embedding: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Calculate similarity between a query and multiple embeddings.

        Args:
            query_embedding: Query embedding (1D or 2D with shape [1, dim])
            embeddings: Multiple embeddings (2D array)

        Returns:
            Array of similarity scores
        """
        # Ensure query is 1D
        if query_embedding.ndim > 1:
            query_embedding = query_embedding.squeeze()

        # Normalize all
        query_embedding = self._normalize_embeddings(query_embedding)
        embeddings = self._normalize_embeddings(embeddings)

        # Calculate similarities
        return np.dot(embeddings, query_embedding)
