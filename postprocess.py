import re
import random
import logging

logger = logging.getLogger(__name__)

def clean_reply(text: str) -> str:
    if not text:
        return ""

    original_text = text
    text = text.strip()

    # ── Remove ALL special model tokens ─────────────────────────────────────
    text = re.sub(r"<\|[^>]*\|>", "", text)           # catches <|eos|>, <|endoftext|>, etc.
    text = re.sub(r"__.*?__", "", text)               # double underscore tokens

    # ── Broad AI leak / meta / refusal removal ─────────────────────────────
    text = re.sub(r'(?i)(as (an )?ai|language model|llm|chatbot|bot|grok|i\'m (not real|programmed|an ai|artificial))', '', text)
    text = re.sub(r'(?i)(i can\'t assist|against policy|inappropriate|ethical reasons|sorry i can\'t)', '', text)

    # ── Remove thinking tags, actions, stage directions ─────────────────────
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)

    # ── Replace dashes with ellipsis (natural texting) ──────────────────────
    text = re.sub(r'[-—–]+', '…', text)

    # Normalize punctuation
    text = re.sub(r'[.?!…]{3,}', '…', text)
    text = re.sub(r'[!？]{2,}', '!', text)

    # ── Remove banned cringe words ──────────────────────────────────────────
    banned = r'\b(boo|babe|cutie|wassup|wyd|sup|hiii|miss ?me|lma?o+|omg+|no ?way|lowkey|highkey|vibes?|energy)\b'
    text = re.sub(banned, '', text, flags=re.IGNORECASE)

    # ── Limit emojis to maximum 1 ───────────────────────────────────────────
    emoji_pattern = r'[\U0001F300-\U0001F9FF]'
    emojis = re.findall(emoji_pattern, text)
    if len(emojis) > 1:
        text = re.sub(emoji_pattern, lambda m: '' if random.random() < 0.7 else m.group(0), text, count=999)

    # ── Smart question mark fix ─────────────────────────────────────────────
    # Only change trailing ? to . if it doesn't look like a real question
    if text.endswith('?') and not any(word in text.lower() for word in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'do you', 'are you', 'can you']):
        text = text[:-1] + '.'

    # ── Final cleanup ───────────────────────────────────────────────────────
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Log if we removed something significant
    if len(text) < len(original_text) * 0.7:
        logger.warning(f"Significant cleaning occurred. Original: {original_text[:200]}... Cleaned: {text}")

    # Light random human touch
    if random.random() < 0.10 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
