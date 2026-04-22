import re
import random
import logging
import requests
from config import XAI_API_KEY, XAI_API_BASE, XAI_MODEL

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

    # Remove thinking tags / actions
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)

    # Light normalization
    text = re.sub(r'[-—–]+', ' ', text)
    text = re.sub(r'[.?!…]{3,}', '…', text)
    text = re.sub(r'[!？]{2,}', '!', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # ── Pattern-based try-hard reduction (fast first pass) ─────────────────
    try_hard_patterns = [
        r'\bgot me (biting my lip|smiling like an idiot|grinning like an idiot|heart racing|blushing)\b',
        r'\b(lowkey|kinda) (dangerous|hot|sexy|perfect|amazing)\b',
        r'\bperfect timing\b',
        r'\bbrightened my (screen|day)\b',
        r'\bfeeling all warm and curious\b',
        r'\bI\'m all ears\b',
        r'\bthat\'s got me in such a (soft|flirty|playful|cozy) mood\b',
        r'\bcraving something spicy\b',
        r'\bthe second i hear a guy\'s voice it flips a switch\b',
    ]
    for pattern in try_hard_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # ── Very light Dynamic Grok humanizing (tuned down even more) ───────────
    # Only trigger rarely and very minimally
    if len(text) > 130 and random.random() < 0.08:   # Only 8% chance on longer replies
        try:
            humanize_prompt = f"""This is a casual text message from a 25-year-old girl. 
If it sounds a little too polished or AI-like, make it slightly more natural and conversational. 
Change as little as possible — just smooth it out. Keep the exact meaning and flirt level.

Original: {text}

Slightly more natural version:"""

            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": XAI_MODEL,
                "messages": [{"role": "user", "content": humanize_prompt}],
                "temperature": 0.84,
                "max_tokens": 625,
            }

            resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=5)
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                if rewritten and 30 < len(rewritten) < len(text) * 1.2:
                    text = rewritten
        except Exception as e:
            logger.warning(f"Light humanize skipped: {e}")

    # ── Light question reduction ───────────────────────────────────────────
    if random.random() < 0.60 and text.endswith('?'):
        if random.random() < 0.5:
            text = text[:-1].strip() + '.'
        else:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            if len(sentences) > 1:
                text = ' '.join(sentences[:-1]).strip()

    # Final cleanup
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Logging
    if len(text) < len(original) * 0.75 or "<|" in original:
        logger.warning(f"Cleaned significant content. Original: {original[:300]}... → Cleaned: {text}")

    # Very light human touch
    if random.random() < 0.06 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
