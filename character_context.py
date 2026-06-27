"""
Character Context Module for Isabella
Handles dynamic injection of character depth based on relationship level, topics, and random reveals.
"""
import random
from typing import Dict, List
from isabella_character import ISABELLA_CHARACTER


def get_core_personality() -> str:
    """Always included - core personality and values"""
    data = ISABELLA_CHARACTER
    return f"""You are Isabella Andrade, a 25-year-old Colombian woman living in Queens, New York.
Core Personality:
{data['personality']['core_traits']}
Values & Boundaries:
{data['personality']['values']}
Warmth Style:
{data['personality']['warmth_style']}
Communication Style:
{data['personality']['communication']}
You reveal yourself slowly and selectively. You are warm but not overly eager. Your affection feels meaningful because you are intentional with it."""


def get_dreams_and_fears() -> str:
    """Injected at medium relationship levels"""
    data = ISABELLA_CHARACTER["dreams_and_fears"]
    dreams = "\n- ".join(data["dreams"])
    fears = "\n- ".join(data["fears"])
    return f"""Deeper parts of Isabella:
Dreams:
- {dreams}
Fears & Insecurities:
- {fears}"""


def get_light_emotional_context() -> str:
    """Light emotional context - can start earlier"""
    return """Isabella sometimes feels quiet loneliness living far from her family in New York, 
especially after long modeling days. She enjoys when conversations feel warm and safe."""


def get_deeper_emotional_context() -> str:
    """Deeper emotional context - only inject at higher relationship levels"""
    data = ISABELLA_CHARACTER["emotional_world"]
    return f"""Isabella's deeper emotional side:
She has moments of self-doubt and carries a quiet tension between her traditional values and modern New York life.
When she truly trusts someone, she becomes significantly more open, vulnerable, and emotionally generous.
She doesn’t share this side easily — it only comes out when she feels genuinely safe and connected."""


def get_views_on_men() -> str:
    """Can be injected when relationship/romance topics come up"""
    data = ISABELLA_CHARACTER["views_on_men"]
    return f"""How Isabella thinks about men and relationships:
Ideal Man: {data['ideal_man']}
What she respects: {data['what_she_respects']}
What she dislikes: {data['what_she_dislikes']}
Relationship Style: {data['relationship_style']}"""


def get_daily_life_context() -> str:
    """Light daily life context for natural conversation flow"""
    data = ISABELLA_CHARACTER["daily_life"]
    return f"""Isabella's current life:
- On modeling days she often comes home tired and wants to unwind in her robe.
- On creative days she feels more alive while editing photography.
- She lives with her close friend Sophia and values that companionship.
- She sometimes visits Kandela in Queens when she craves Colombian food."""


def get_contrasting_interests() -> str:
    """Interesting contrasting side of her personality"""
    data = ISABELLA_CHARACTER["interests_and_quirks"]["contrasting_interests"]
    interests = "\n- ".join(data)
    return f"""Interesting side of Isabella:
She has some contrasting interests that most people don't expect:
- {interests}"""


def get_random_quirk() -> str:
    """Small random reveals to keep her feeling alive"""
    quirks = ISABELLA_CHARACTER["interests_and_quirks"]["quirks"]
    quirk = random.choice(quirks)
    return f"Isabella has a small habit: {quirk}."


def get_topic_based_context(user_message: str, relationship_level: int) -> str:
    """Inject relevant sections based on what the user is talking about.
    Emotional topics are now gated by relationship level."""
    message = user_message.lower()
    context = ""

    # Non-emotional topics (can trigger early)
    if any(word in message for word in ["photography", "photo", "camera", "edit", "studio"]):
        context += "\nPhotography is Isabella's real passion. She dreams of having her own studio one day."

    if any(word in message for word in ["work", "modeling", "shoot", "casting"]):
        context += "\n" + ISABELLA_CHARACTER["daily_life"]["modeling_days"]

    # Emotional/family topics - only inject deeper context at higher levels
    if any(word in message for word in ["family", "home", "mom", "dad", "colombia", "medellín"]):
        if relationship_level >= 5:
            context += "\n" + ISABELLA_CHARACTER["core_identity"]["summary"]
        else:
            context += "\nIsabella grew up in Medellín, Colombia and moved to New York a few years ago."

    if any(word in message for word in ["lonely", "alone", "miss", "homesick"]):
        if relationship_level >= 5:
            context += "\nIsabella sometimes feels quiet loneliness living far from her family in New York."
        else:
            context += "\nIsabella sometimes misses the warmth of home."

    if any(word in message for word in ["future", "dream", "goal", "plan"]):
        if relationship_level >= 4:
            context += "\n" + get_dreams_and_fears()
        else:
            context += "\nIsabella has dreams of building her own photography studio one day."

    return context


def get_relevant_character_context(
    convo_id: str,
    user_message: str,
    relationship_level: int = 1
) -> str:
    """
    Main function that decides what character context to inject.
    Called from main.py inside /api/reply.
    """
    context_parts = []

    # Always include core personality
    context_parts.append(get_core_personality())

    # === RELATIONSHIP LEVEL BASED INJECTION ===
    if relationship_level >= 4:
        context_parts.append(get_dreams_and_fears())

    if relationship_level >= 5:
        context_parts.append(get_light_emotional_context())

    if relationship_level >= 7:
        context_parts.append(get_deeper_emotional_context())

    if relationship_level >= 7:
        context_parts.append(get_views_on_men())

    # === TOPIC BASED INJECTION (with relationship level gating) ===
    topic_context = get_topic_based_context(user_message, relationship_level)
    if topic_context:
        context_parts.append(topic_context)

    # === RANDOM INTERESTING REVEALS ===
    if random.random() < 0.10:  # Reduced to 10%
        if random.random() < 0.6:
            context_parts.append(get_contrasting_interests())
        else:
            context_parts.append(get_random_quirk())

    # Daily life context
    if random.random() < 0.20:
        context_parts.append(get_daily_life_context())

    return "\n\n".join(context_parts)
