import re
from rapidfuzz import fuzz

def clean_title_only(title: str) -> str:
    """Cleans song titles by removing extra features, parentheses, and punctuation."""
    # Remove anything after a standalone dash (e.g., ' - Demo - 1969')
    title = title.split(" - ")[0]
    clean_title = re.sub(r"\(.*?\) |\[.*?\]", "", title)
    clean_title = re.sub(r"(?i)feat\..*|ft\..*", "", clean_title)
    return " ".join(clean_title.split())

def is_similar(a: str, b: str, threshold: float = 65.0) -> bool:
    """Compares two strings using rapidfuzz. Returns True if ratio > threshold."""
    # token_set_ratio is much better for subsets (e.g., 'Lanu' vs 'Lanu And Megan Washington')
    return fuzz.token_set_ratio(a.lower(), b.lower()) > threshold
