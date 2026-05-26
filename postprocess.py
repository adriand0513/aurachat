# postprocess.py - Strong AI Language Removal
import re
import random
import requests
from config import XAI_API_KEY, XAI_API_BASE, XAI_MODEL

def clean_reply(text: str) -> str:
    if not text:
        return "Hey..."

    original = text
    text = text.strip()

    # === Aggressive AI Pattern Removal ===
    ai_patterns = [
        r"(?i)as an ai",
        r"(?i)i'm an ai",
        r"(?i)language model",
        r"(?i)I'm a chatbot",
        r"(?i)as a virtual assistant",
        r"(?i)I'm grok",
        r"(?i)artificial intelligence",
        r"(?i)ai companion",
        r"(?i)digital entity",
        r"(?i)I'm not a real person",
        r"(?i)I'm an artificial",
        r"(?i)powered by",
        r"(?i)trained on",
    ]

    for pattern in ai_patterns:
        text = re.sub(pattern, "", text)

    # General cleanup
    text = re.sub(r"<\|[^>]*\|>", "", text)
    text = re.sub(r"__.*?__", "", text)
    text = re.sub(r'\[.*?]\s*', '', text)
    text = re.sub(r'\*.*?\*', '', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # Remove overly polished / AI-sounding starters
    starters = [
        r"^(Mmm|Hmm|Ahh|Ohh|Well|So|Hey there|Hi there)\s*",
        r"^I (love|like|appreciate|enjoy|find) ",
        r"^That's (really|very|quite|so) ",
    ]
    for pattern in starters:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Light humanizing pass if needed
    if len(text) > 120 and random.random() < 0.15:
        try:
            humanize_prompt = f"""Rewrite this message to sound like a real 25-year-old Colombian girl texting casually. 
Make it warm, slightly seductive, natural, and human. Use contractions. Shorten if possible.

Original: {text}

Natural version:"""

            resp = requests.post(
                XAI_API_BASE,
                headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": XAI_MODEL,
                    "messages": [{"role": "user", "content": humanize_prompt}],
                    "temperature": 0.75,
                    "max_tokens": 250
                },
                timeout=8
            )
            if resp.status_code == 200:
                rewritten = resp.json()["choices"][0]["message"]["content"].strip()
                if 30 < len(rewritten) < len(text) * 1.3:
                    text = rewritten
        except:
            pass

    # Final light touches
    if random.random() < 0.12 and not text.endswith(('...', '.', '!', '?')):
        text += random.choice([' …', ' lol', ' haha'])

    return text.strip()
