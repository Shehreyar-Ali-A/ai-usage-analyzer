from typing import List, Tuple


def compute_direct_reuse_similarity(similarity_scores: List[float]) -> float:
    if not similarity_scores:
        return 0.0
    # Use max similarity as a proxy for direct reuse
    return max(similarity_scores)


def compute_transformation_degree(semantic_scores: List[float], lexical_scores: List[float]) -> float:
    """
    Approximate transformation degree: high when semantic similarity is high but lexical is lower.
    For v0, use a simple heuristic.
    """
    if not semantic_scores or not lexical_scores:
        return 0.0

    avg_sem = sum(semantic_scores) / len(semantic_scores)
    avg_lex = sum(lexical_scores) / len(lexical_scores)
    # If semantic > lexical, assume more transformation; scale into [0, 1]
    diff = max(0.0, avg_sem - avg_lex)
    return min(1.0, diff)


def compute_iteration_depth(num_messages: int) -> float:
    """
    Heuristic iteration depth score based on conversation length.
    """
    if num_messages <= 0:
        return 0.0
    # Cap influence after ~40 messages
    return min(1.0, num_messages / 40.0)


def compute_reliance_score(
    direct_reuse_similarity: float,
    prompt_severity: float,
    transformation_degree: float,
    iteration_depth: float,
) -> Tuple[int, str]:
    """
    Combine sub-scores into final 0–100 reliance score and label.
    Weights:
      - direct_reuse_similarity: 40%
      - prompt_severity: 30%
      - transformation_degree: 20%
      - iteration_depth: 10%
    """
    direct_reuse_similarity = max(0.0, min(1.0, direct_reuse_similarity))
    prompt_severity = max(0.0, min(1.0, prompt_severity))
    transformation_degree = max(0.0, min(1.0, transformation_degree))
    iteration_depth = max(0.0, min(1.0, iteration_depth))

    score_0_1 = (
        0.4 * direct_reuse_similarity
        + 0.3 * prompt_severity
        + 0.2 * transformation_degree
        + 0.1 * iteration_depth
    )
    score_0_100 = int(round(score_0_1 * 100))

    if score_0_100 <= 30:
        label = "Low"
    elif score_0_100 <= 60:
        label = "Moderate"
    else:
        label = "High"

    return score_0_100, label

