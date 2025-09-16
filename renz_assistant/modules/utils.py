"""
Utility functions for Renz Assistant
"""
import numpy as np

def cosine_similarity_manual(vec1, vec2):
    """Calculate cosine similarity between two vectors manually using numpy."""
    vec1 = np.asarray(vec1)
    vec2 = np.asarray(vec2)
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    return dot_product / (norm_vec1 * norm_vec2)