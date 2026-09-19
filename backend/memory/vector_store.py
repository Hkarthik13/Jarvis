import re
import json
import math
import hashlib
from typing import List, Dict, Any, Tuple
import numpy as np

VECTOR_DIM = 256

def text_to_vector(text: str) -> np.ndarray:
    """
    Computes a deterministic, dense, normalized embedding vector from text using
    hashed n-gram frequency distributions and token semantic representations.
    Zero external heavy dependencies, works seamlessly on all Python versions.
    """
    if not text or not text.strip():
        return np.zeros(VECTOR_DIM, dtype=np.float32)
        
    cleaned = text.lower().strip()
    words = re.findall(r"\b\w+\b", cleaned)
    vec = np.zeros(VECTOR_DIM, dtype=np.float32)
    
    # 1. Word unigram hashing
    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        idx = h % VECTOR_DIM
        sign = 1 if (h // VECTOR_DIM) % 2 == 0 else -1
        vec[idx] += sign * (1.0 + math.log(1 + len(word)))
        
    # 2. Character trigram hashing for fuzzy typo tolerance
    for i in range(len(cleaned) - 2):
        trigram = cleaned[i:i+3]
        h = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest(), 16)
        idx = h % VECTOR_DIM
        sign = 1 if (h // VECTOR_DIM) % 2 == 0 else -1
        vec[idx] += 0.5 * sign
        
    # 3. L2 Normalization
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
        
    return vec

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """Computes cosine similarity between two unit-normalized vectors."""
    dot = np.dot(v1, v2)
    return float(np.clip(dot, -1.0, 1.0))

def compute_hybrid_score(
    query: str,
    query_vec: np.ndarray,
    doc_key: str,
    doc_content: str,
    doc_tags: str,
    doc_vec: np.ndarray
) -> float:
    """
    Calculates hybrid relevance score combining vector cosine similarity,
    exact keyword substring matches, and token overlap in chunk content.
    """
    # 1. Vector cosine similarity (weight: 0.5)
    vec_sim = cosine_similarity(query_vec, doc_vec) if doc_vec is not None else 0.0
    
    # 2. Chunk text keyword & token matching (weight: 0.5)
    q_lower = query.lower()
    content_lower = doc_content.lower()
    key_lower = doc_key.lower()
    
    keyword_score = 0.0
    if q_lower in content_lower:
        keyword_score += 0.5
        
    # Meaningful query token overlap in chunk content
    stop_words = {"what", "are", "the", "in", "my", "is", "a", "an", "and", "of", "to", "for", "did", "use", "used"}
    q_words = set(re.findall(r"\b\w+\b", q_lower)) - stop_words
    content_words = set(re.findall(r"\b\w+\b", content_lower))
    if q_words:
        overlap = len(q_words.intersection(content_words)) / len(q_words)
        keyword_score += 0.5 * overlap

    if key_lower in q_lower:
        keyword_score += 0.15
        
    keyword_score = min(keyword_score, 1.0)
    
    # Combined hybrid score
    hybrid = (0.50 * max(0.0, vec_sim)) + (0.50 * keyword_score)
    return float(hybrid)
