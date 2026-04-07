import re
import random
import logging

logger = logging.getLogger(__name__)

def clean_reply(text: str) -> str:
    if not text:
        return ""

    original = text
    text = text.strip()

    # ── Critical: Remove ALL special model tokens ─────────────────────────────
    text = re.sub(r"<\|[^>]*\|>", "", text)          # catches <|eos|>, etc.
    text = re.sub(r"__.*?__", "", text)

    # ── Strong but targeted AI leak / meta removal ───────────────────────────
    text = re.sub(r'(?i)(as (an )?ai|language model|llm|chatbot|bot|grok|i\'m (not real|programmed|an ai|artificial|virtual|digital assistant))', '', text)
    text = re.sub(r'(?i)(i can\'t assist|against policy|inappropriate|ethical reasons|sorry i can\'t)', '', text)

    # ── Remove thinking tags, actions, stage directions ─────────────────────
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)

    # ── Light punctuation normalization ─────────────────────────────────────
    text = re.sub(r'[-—–]+', ' ', text)
    text = re.sub(r'[.?!…]{3,}', '…', text)
    text = re.sub(r'[!？]{2,}', '!', text)

    # ── Removed heavy banned word list ───────────────────────────────────────
    # Only keep very light emoji control
    emoji_pattern = r'[\U0001F300-\U0001F9FF]'
    emojis = re.findall(emoji_pattern, text)
    if len(emojis) > 1:
        text = re.sub(emoji_pattern, lambda m: '' if random.random() < 0.7 else m.group(0), text, count=999)

    # ── Smart question mark preservation (only fix obvious broken cases) ─────
    # This helps prevent turning real questions into statements
    if re.search(r'(what|how|why|when|where|who|do you|are you|can you|would you)', text.lower()) and text.endswith('.'):
        if not text.endswith(('Mr.', 'Mrs.', 'Dr.', 'Ms.')):
            text = text[:-1] + '?'

    # ── Final cleanup ───────────────────────────────────────────────────────
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Log if we removed a lot of content (for debugging)
    if len(text) < len(original) * 0.75 or "<|" in original:
        logger.warning(f"Cleaned significant content. Original: {original[:300]}... → Cleaned: {text}")

    # Very light human touch (optional)
    if random.random() < 0.08 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
