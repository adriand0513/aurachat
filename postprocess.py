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

    # ── Dynamic Grok secondary check (very light) ─────────────────────────
    # Only trigger on longer or suspicious replies to keep it efficient
    if len(text) > 90 or random.random() < 0.25:   # ~25% chance + long replies
        try:
            humanize_prompt = f"""Rewrite this reply to sound like a real 25-year-old girl casually texting. 
Make it natural, a bit messy, direct, and feminine. Remove any try-hard, poetic, or overly polished language. 
Keep the exact meaning and flirt level the same.

Original: {text}

Rewritten:"""

            headers = {
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": XAI_MODEL,
                "messages": [{"role": "user", "content": humanize_prompt}],
                "temperature": 0.85,
                "max_tokens": 300,
            }

            resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=8)
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                if rewritten and len(rewritten) > 10:
                    text = rewritten
        except Exception as e:
            logger.warning(f"Secondary Grok humanize failed: {e}")

    # ── Smart question reduction ───────────────────────────────────────────
    if random.random() < 0.65 and text.endswith('?'):
        if random.random() < 0.55:
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
