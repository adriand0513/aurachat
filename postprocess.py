# postprocess.py - Balanced & Safe Version
import re
import random
import requests
from config import XAI_API_KEY, XAI_API_BASE, XAI_MODEL
# postprocess.py - Balanced & Safe Version
import re
import random
import requests
from config import XAI_API_KEY, XAI_API_BASE, XAI_MODEL

def clean_reply(text: str) -> str:
    if not text:
        return "Hey..."

    text = text.strip()

    # Light cleanup only
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"__.*?__", "", text)
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'[-—–]{2,}', ' ', text)   # Remove excessive dashes
    text = re.sub(r'\s{2,}', ' ', text)

    # Remove common AI starters
    text = re.sub(r"^(Mmm|Hmm|Ahh|Ohh|Well|So|Hey there)\s*", "", text, flags=re.IGNORECASE)

    # Very light humanizing (only when needed)
    if len(text) > 100 and random.random() < 0.12:
        try:
            humanize_prompt = f"""Rewrite this reply to sound like a real 25-year-old girl texting casually. 
Keep it warm, natural, slightly seductive. Do not add any prefixes or explanations.

Original: {text}

Natural version:"""

            resp = requests.post(
                XAI_API_BASE,
                headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": XAI_MODEL,
                    "messages": [{"role": "user", "content": humanize_prompt}],
                    "temperature": 0.7,
                    "max_tokens": 250
                },
                timeout=7
            )
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                if 25 < len(rewritten) < len(text) * 1.25:
                    text = rewritten
        except:
            pass

    return text.strip()
