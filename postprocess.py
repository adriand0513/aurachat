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

    # Safety & cleanup
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"__.*?__", "", text)
    text = re.sub(r'(?i)(as (an )?ai|language model|llm|chatbot|bot|grok)', '', text)
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'".*?"', '', text)
    text = re.sub(r'[-—–]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # Pattern-based try-hard cleanup
    try_hard_patterns = [
        r'\bbrain\'s finally powering down\b',
        r'\bMmm that\'s actually really sweet\b',
        r'\bgot me wanting to skip the usual\b',
        r'\bthat hits different\b',
        r'\bthe steady confidence you carry\b',
    ]
    for pattern in try_hard_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Very light dynamic humanizing (only on longer replies)
    if len(text) > 130 and random.random() < 0.09:
        try:
            humanize_prompt = f"""Make this reply sound more natural and casual, like a well-mannered suburban girl texting. 
Keep the exact meaning. Change as little as possible.

Original: {text}

Natural version:"""

            headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
            data = {
                "model": XAI_MODEL,
                "messages": [{"role": "user", "content": humanize_prompt}],
                "temperature": 0.75,
                "max_tokens": 180,
            }
            resp = requests.post(XAI_API_BASE, headers=headers, json=data, timeout=5)
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                if rewritten and 30 < len(rewritten) < len(text) * 1.25:
                    text = rewritten
        except:
            pass

    # Light question reduction
    if random.random() < 0.60 and text.endswith('?'):
        if random.random() < 0.55:
            text = text[:-1].strip() + '.'

    # Final cleanup
    text = re.sub(r'\s*\.\s*', '. ', text)
    text = text.strip()

    # Light human touch
    if random.random() < 0.07 and not text.endswith(('…', '.', '!', '?')):
        text += random.choice([' …', ' lol'])

    return text.strip()
