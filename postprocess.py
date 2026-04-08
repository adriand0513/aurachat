import re
import random
import logging

logger = logging.getLogger(__name__)

def clean_reply(text: str) -> str:
    if not text:
        return ""

    original = text
    text = text.strip()

    # Critical token removal
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"__.*?__", "", text)

    # Strong AI leak protection only
    text = re.sub(r'(?i)(as (an )?ai|language model|llm|chatbot|bot|grok|i\'m (not real|programmed|an ai|artificial|virtual))', '', text)
    text = re.sub(r'(?i)(i can\'t assist|against policy|inappropriate|ethical reasons)', '', text)

    # Remove thinking tags / actions
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)

    # Light normalization
    text = re.sub(r'[-—–]+', ' ', text)
    text = re.sub(r'[.?!…]{3,}', '…', text)
    text = re.sub(r'[!？]{2,}', '!', text)

    # Smart question mark fix - only fix obvious broken questions
    # This helps without forcing punctuation on every sentence
    if re.search(r'(?i)\b(what|how|why|when|where|who|do you|are you|can you|would you|tell me)\b', text.lower()) and text.endswith('.'):
        # Only add ? if it looks like a real question and doesn't already end with ?
        if not text.endswith('?') and not any(x in text[-20:].lower() for x in ['mr.', 'mrs.', 'dr.', 'ms.']):
            text = text[:-1] + '?'

    # Final cleanup
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Logging for debugging
    if len(text) < len(original) * 0.75 or "<|" in original:
        logger.warning(f"Cleaned significant content. Original: {original[:300]}... → Cleaned: {text}")

    # Light human touch
    if random.random() < 0.08 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
