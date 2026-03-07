"""
Tag normalisation utility — Phase V (T005/T018).
Enforces: lowercase, stripped whitespace, deduplication, max 20 tags, max 50 chars per tag.
"""
from typing import List, Optional


def normalise_tags(tags: Optional[List[str]]) -> List[str]:
    """
    Normalise a list of tag strings:
    - Strip whitespace
    - Lowercase
    - Drop empty strings
    - Truncate to 50 characters
    - Deduplicate (preserve order of first occurrence)
    - Limit to 20 tags
    """
    if not tags:
        return []
    seen = set()
    result = []
    for tag in tags:
        normalised = tag.strip().lower()[:50]
        if normalised and normalised not in seen:
            seen.add(normalised)
            result.append(normalised)
        if len(result) >= 20:
            break
    return result
