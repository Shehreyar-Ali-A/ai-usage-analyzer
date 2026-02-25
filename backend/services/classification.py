from typing import Dict, List, Tuple


CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Direct Generation": [
        "write the entire essay",
        "write my essay",
        "generate full solution",
        "write the whole assignment",
        "complete this problem set",
        "write this for me",
    ],
    "Rewriting": [
        "rewrite",
        "rephrase",
        "improve this",
        "make this sound better",
        "polish this",
        "edit this",
    ],
    "Tutoring": [
        "explain",
        "teach",
        "help me understand",
        "clarify",
        "what is",
        "how does",
    ],
    "Ideation": [
        "brainstorm",
        "outline",
        "ideas for",
        "structure this",
        "plan an essay",
    ],
}


def classify_prompts(user_prompts: List[str]) -> Tuple[List[str], float]:
    """
    Classify prompts into usage categories and compute a prompt severity score (0–1).
    Severity is higher when direct-generation-style prompts are present frequently.
    """
    if not user_prompts:
        return [], 0.0

    prompt_categories: Dict[str, int] = {name: 0 for name in CATEGORY_KEYWORDS.keys()}

    for prompt in user_prompts:
        lower = prompt.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in lower for keyword in keywords):
                prompt_categories[category] += 1

    usage_types = [cat for cat, count in prompt_categories.items() if count > 0]

    total_matched = sum(prompt_categories.values())
    if total_matched == 0:
        return usage_types, 0.0

    # Heuristic severity: weight Direct Generation highest, then Rewriting, then others.
    direct = prompt_categories["Direct Generation"]
    rewriting = prompt_categories["Rewriting"]
    tutoring = prompt_categories["Tutoring"]
    ideation = prompt_categories["Ideation"]

    weighted = 1.0 * direct + 0.7 * rewriting + 0.4 * tutoring + 0.3 * ideation
    max_possible = 1.0 * total_matched  # worst case all direct-generation
    severity = weighted / max_possible if max_possible > 0 else 0.0

    # Clamp to [0, 1]
    severity = max(0.0, min(1.0, severity))
    return usage_types, severity

