import re
import random
import logging

logger = logging.getLogger(__name__)

def clean_reply(text: str) -> str:
    if not text:
        return ""

    original = text
    text = text.strip()

    # ── Critical safety & leak removal ─────────────────────────────────────
    text = re.sub(r"<\|[^>]*\|>", "", text)                    # Remove <|eos|>, etc.
    text = re.sub(r"__.*?__", "", text)
    text = re.sub(r'(?i)(as (an )?ai|language model|llm|chatbot|bot|grok|i\'m (not real|programmed|an ai|artificial|virtual))', '', text)
    text = re.sub(r'(?i)(i can\'t assist|against policy|inappropriate|ethical reasons)', '', text)

    # Remove thinking tags / actions / stage directions
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)

    # Light normalization
    text = re.sub(r'[-—–]+', ' ', text)
    text = re.sub(r'[.?!…]{3,}', '…', text)
    text = re.sub(r'[!？]{2,}', '!', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # ── Gentle question mark fix ───────────────────────────────────────────
    # Only fix if it looks like a clear question but ends with period
    # if re.search(r'(?i)\b(what|how|why|when|where|who|do you|are you|can you|would you|tell me|is it|should i)\b', text.lower()) \
    #    and text.endswith('.') and not text.endswith('?'):
    #     # Avoid fixing titles or names (Mr., Dr., etc.)
    #     if not any(x in text[-30:].lower() for x in ['mr.', 'mrs.', 'dr.', 'ms.', 'prof.']):
    #         text = text[:-1] + '?'

    # Final cleanup
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Logging for debugging significant changes
    if len(text) < len(original) * 0.75 or "<|" in original:
        logger.warning(f"Cleaned significant content. Original: {original[:300]}... → Cleaned: {text}")

    # Very light human touch (optional)
    if random.random() < 0.08 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
