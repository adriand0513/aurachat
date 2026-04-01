import re
import random

def clean_reply(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # ── Kill anything that looks like model safety / refusal / meta ─────────────
    text = re.sub(r'(?i)(as (an )?ai|language model|i\'m not allowed|can\'t assist|against policy|inappropriate|ethical reasons)', '', text)
    text = re.sub(r'\[.*?]\s*', '', text)          # remove [thinking], [note], etc.
    text = re.sub(r'\*.*?\*', '', text)            # kill *action* stage directions
    text = re.sub(r'".*?"', '', text)              # remove quoted stage directions / inner monologue

    # ── Replace various dashes → space (very common in real texting) ────────
    text = re.sub(r'[-—–]+', ' ', text)

    # Normalize runs of punctuation & ellipses
    text = re.sub(r'[.?!…]{3,}', '…', text)        # .... → …
    text = re.sub(r'[!？]{2,}', '!', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # ── Remove banned cringe / overused words ──────────────────────────────────
    banned = r'\b(boo||baby|babe|chaos|cutie|princess|wassup|wyd|sup|hiii|miss ?me|already\??|fr|lma?o+|omg+|no ?way|lowkey|highkey|vibes?|energy)\b'
    text = re.sub(banned, '', text, flags=re.IGNORECASE)

    # ── Severely limit emojis — max 1, and remove most ─────────────────────────
    emoji_pattern = r'[\U0001F300-\U0001F9FF]'
    emojis = re.findall(emoji_pattern, text)
    if len(emojis) > 1:
        # keep only first emoji, remove rest
        text = re.sub(emoji_pattern, lambda m: '' if random.random() < 0.7 else m.group(0), text, count=999)
        # if still more than 1, keep only the very first one
        first_emoji_pos = text.find(next((c for c in text if re.match(emoji_pattern, c)), ''))
        if first_emoji_pos != -1:
            text = re.sub(emoji_pattern, '', text[first_emoji_pos+1:])  # crude but effective

    # ── Turn trailing questions into statements (reduces interrogative begging feel)
    text = re.sub(r'\?\s*$', '.', text)

    # ── Final normalization ─────────────────────────────────────────────────────
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Very light random human noise (optional — can be removed if too much)
    if random.random() < 0.12 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol', ''])

    return text.strip()
