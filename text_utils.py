# text_utils.py (snippet - the expansions dictionary)

import re

def expand_abbreviations_for_tts(text: str) -> str:
    """
    Expand common texting abbreviations/acronyms for natural ElevenLabs TTS pronunciation.
    Keeps chat text casual while making voice notes sound spoken/human.
    """
    expansions = {
        # Very high frequency - almost mandatory
        r'\baf\b': 'as fuck',          # tired af → tired as fuck
        r'\bAF\b': 'as fuck',
        r'\basf\b': 'as fuck',
        r'\bbc\b': 'because',          # bc I'm tired → because I'm tired
        r'\bBC\b': 'because',
        r'\bbcs\b': 'because',
        r'\btbh\b': 'to be honest',
        r'\bTBH\b': 'to be honest',
        r'\bfr\b': 'for real',
        r'\bFR\b': 'for real',
        r'\bfrfr\b': 'for real for real',
        r'\bFRFR\b': 'for real for real',
        r'\bngl\b': 'not gonna lie',
        r'\bNGL\b': 'not gonna lie',
        r'\bidk\b': 'I don’t know',
        r'\bIDK\b': 'I don’t know',
        r'\bmin\b': 'minute',          # 10 min → 10 minute
        r'\bmins\b': 'minutes',
        r'\bprobs\b': 'probably',
        r'\bdef\b': 'definitely',

        # Laugh / reaction - usually fine as-is, but can expand if voice struggles
        r'\blol\b': 'lol',             # most voices say "lol" or chuckle - safe to leave
        r'\bLOL\b': 'lol',
        r'\blmao\b': 'lmao',
        r'\bLMAO\b': 'lmao',
        r'\bdead\b': 'dead',           # I'm dead (laughing)
        r'\bded\b': 'dead',

        # Emotional / flirty common in her style
        r'\bsmh\b': 'shaking my head',
        r'\bSMH\b': 'shaking my head',
        r'\bfomo\b': 'fear of missing out',
        r'\bFOMO\b': 'fear of missing out',
        r'\bimo\b': 'in my opinion',
        r'\bIMO\b': 'in my opinion',
        r'\bimho\b': 'in my humble opinion',
        r'\bIMHO\b': 'in my humble opinion',
        r'\bbffr\b': 'be for real',
        r'\bBFFR\b': 'be for real',
        r'\bpmo\b': 'pisses me off',   # or 'put me on' - context matters; pick one
        r'\bPMO\b': 'pisses me off',

        # Time / availability
        r'\bbrb\b': 'be right back',
        r'\bBRB\b': 'be right back',
        r'\bttyl\b': 'talk to you later',
        r'\bTTYL\b': 'talk to you later',
        r'\bg2g\b': 'got to go',
        r'\bG2G\b': 'got to go',
        r'\brn\b': 'right now',
        r'\bRN\b': 'right now',
        r'\batm\b': 'at the moment',
        r'\bATM\b': 'at the moment',

        # Agreement / emphasis
        r'\bbet\b': 'bet',             # usually fine - means "sure" / "ok"
        r'\bperiodt\b': 'period',      # emphasis - "periodt" → "period"
        r'\bfacts\b': 'facts',
        r'\bno cap\b': 'no cap',       # no lie - usually pronounced ok
        r'\bnc\b': 'no cap',

        # Other frequent casual ones
        r'\bb4\b': 'before',
        r'\bB4\b': 'before',
        r'\bbtw\b': 'by the way',
        r'\bBTW\b': 'by the way',
        r'\bfyi\b': 'for your information',
        r'\bFYI\b': 'for your information',
        r'\bwtf\b': 'what the fuck',
        r'\bWTF\b': 'what the fuck',
        r'\bstfu\b': 'shut the fuck up',
        r'\bSTFU\b': 'shut the fuck up',
        r'\bidc\b': 'I don’t care',
        r'\bIDC\b': 'I don’t care',
        r'\bnvm\b': 'never mind',
        r'\bNVM\b': 'never mind',
        r'\blmk\b': 'let me know',
        r'\bLMK\b': 'let me know',
        r'\bily\b': 'I love you',
        r'\bILY\b': 'I love you',
        r'\bomw\b': 'on my way',
        r'\bOMW\b': 'on my way',

        # Add more niche/2025–2026 trending if she uses them
        r'\bfafa\b': 'fuck around and find out',  # FAFO
        r'\bfafo\b': 'fuck around and find out',
        r'\bFAFO\b': 'fuck around and find out',
        r'\bicl\b': 'I can’t lie',
        r'\bICL\b': 'I can’t lie',
        r'\batp\b': 'at this point',
        r'\bATP\b': 'at this point',
        r'\bts\b': 'talk soon',
        r'\bTS\b': 'talk soon',
    }

    for pattern, replacement in expansions.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text