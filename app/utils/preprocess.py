# FILE: app/utils/preprocess.py
import re
import unicodedata

def clean_text(text: str) -> str:
    """
    Clean raw product text to improve embedding quality.
    (Renamed from normalize_text to match ingest.py)
    """
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Normalize unicode characters
    text = unicodedata.normalize("NFKD", text)

    # Remove non-alphanumeric characters except basic punctuation
    text = re.sub(r"[^a-z0-9\s.,-]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text

# Alias for backward compatibility if needed
normalize_text = clean_text