# postprocess.py
import re

def clean_reply(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # ── Step 1: Replace dashes with ellipses (the most natural texting feel) ─────
    dash_patterns = [
        r'—',                               # em dash
        r'–',                               # en dash
        r'\s*-\s*(?=[A-Za-z])',             # hyphen with spaces before word
        r'\s*-\s*$',                        # trailing hyphen
        r'(?<=[A-Za-z])\s*-\s*(?=[A-Za-z])',# mid-sentence hyphen with spaces
        r'-\s+',                            # hyphen followed by space
    ]

    # Replace any matched dash pattern with ellipsis + space
    for pattern in dash_patterns:
        text = re.sub(pattern, '… ', text)

    # Normalize multiple ellipses (people don't usually write .......)
    text = re.sub(r'[…]{2,}', '…', text)

    # ── Your original rules ─────────────────────────────────────────────────────

    # Remove trailing question mark → turn into period
    text = re.sub(r'\?\s*$', '.', text)

    # Turn mid-sentence questions into statements
    text = re.sub(r'(\S+)\?\s*', r'\1. ', text)

    # Remove very common unwanted words/patterns
    banned = r'\b(boo|papi|baby|cutie|wassup|sup|wyd|hiii|heyyy|miss ?me|already\??|fr|lma?o+|omg+|no ?way)\b'
    text = re.sub(banned, '', text, flags=re.IGNORECASE)

    # Limit emojis severely (keep at most 1)
    emojis = re.findall(r'[\U0001F300-\U0001F9FF]', text)
    if len(emojis) > 1:
        keep_first = True
        def repl(m):
            nonlocal keep_first
            if keep_first:
                keep_first = False
                return m.group(0)
            return ''
        text = re.sub(r'[\U0001F300-\U0001F9FF]', repl, text)

    # ── Final cleanup ───────────────────────────────────────────────────────────
    # Collapse multiple spaces/punctuation
    text = re.sub(r'([.!?]){2,}', r'\1', text)      # !! → !
    text = re.sub(r'\s{2,}', ' ', text)             # multiple spaces → single
    text = re.sub(r'\s*\.\s*', '. ', text)          # normalize periods + spaces

    # Trim trailing punctuation that looks off
    text = re.sub(r'[.!?]\s*$', lambda m: m.group(0).rstrip(), text)

    return text.strip()