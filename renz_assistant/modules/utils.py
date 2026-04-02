"""
Utility functions for Renz Assistant
Pure Python implementation - no numpy required
"""
import math


def cosine_similarity_manual(vec1, vec2):
    """Calculate cosine similarity between two vectors using pure Python."""
    if len(vec1) != len(vec2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def mean(values):
    """Calculate mean of a list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def std(values):
    """Calculate standard deviation of a list."""
    if not values:
        return 0.0
    m = mean(values)
    variance = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(variance)
