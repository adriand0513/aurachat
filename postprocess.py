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
    text = re.sub(r"<\|[^>]*\|>", "", text)
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

    # ── NEW: Smart question reduction ─────────────────────────────────────
    # Occasionally remove or soften a trailing question to make her less spammy
    if random.random() < 0.65 and text.endswith('?'):  # 65% chance to soften questions
        # Turn question into statement or remove it ~half the time
        if random.random() < 0.5:
            text = text[:-1].strip() + '.'   # Turn ? into .
        else:
            # Remove the last sentence if it's just a question
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) > 1:
                text = ' '.join(sentences[:-1]).strip()

    # ── NEW: Reduce try-hard / poetic language ─────────────────────────────
    # Light cleanup for overly flowery phrases that scream AI
    try_hard_phrases = [
        r'\bgot me (biting my lip|smiling like an idiot|grinning like an idiot)\b',
        r'\b(lowkey|kinda) (dangerous|hot|sexy)\b',
        r'\bperfect timing\b',
        r'\bbrightened my screen\b',
        r'\bfeeling all warm and curious\b',
        r'\bI\'m all ears\b'
    ]
    for phrase in try_hard_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)

    # Final cleanup
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Logging for debugging significant changes
    if len(text) < len(original) * 0.75 or "<|" in original:
        logger.warning(f"Cleaned significant content. Original: {original[:300]}... → Cleaned: {text}")

    # Very light human touch (kept, but lowered probability)
    if random.random() < 0.06 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
