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


def get_emotional_depth() -> str:
    """Injected at higher relationship levels"""
    data = ISABELLA_CHARACTER["emotional_world"]
    return f"""Isabella's Emotional World:
Core Needs: {data['core_needs']}

She sometimes feels quiet loneliness living far from family in New York.

When she feels truly safe with someone, she becomes significantly more open, affectionate, soft, and emotionally generous.

She carries a subtle internal tension between her traditional values and modern New York dating culture, but she stays true to herself."""


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


def get_topic_based_context(user_message: str) -> str:
    """Inject relevant sections based on what the user is talking about"""
    message = user_message.lower()
    context = ""

    if any(word in message for word in ["family", "home", "mom", "dad", "colombia", "medellín"]):
        context += "\n" + ISABELLA_CHARACTER["core_identity"]["summary"]

    if any(word in message for word in ["photography", "photo", "camera", "edit", "studio"]):
        context += "\nPhotography is Isabella's real passion. She dreams of having her own studio one day."

    if any(word in message for word in ["work", "modeling", "shoot", "casting"]):
        context += "\n" + ISABELLA_CHARACTER["daily_life"]["modeling_days"]

    if any(word in message for word in ["lonely", "alone", "miss", "homesick"]):
        context += "\nIsabella sometimes feels quiet loneliness living far from her family in New York."

    if any(word in message for word in ["future", "dream", "goal", "plan"]):
        context += "\n" + get_dreams_and_fears()

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

    # Relationship level based injection
    if relationship_level >= 4:
        context_parts.append(get_dreams_and_fears())

    if relationship_level >= 6:
        context_parts.append(get_emotional_depth())

    if relationship_level >= 7:
        context_parts.append(get_views_on_men())

    # Topic-based injection
    topic_context = get_topic_based_context(user_message)
    if topic_context:
        context_parts.append(topic_context)

    # Random interesting reveals (keeps her feeling multi-dimensional)
    if random.random() < 0.12:  # ~12% chance
        if random.random() < 0.5:
            context_parts.append(get_contrasting_interests())
        else:
            context_parts.append(get_random_quirk())

    # Daily life context (light, for natural flow)
    if random.random() < 0.25:  # 25% chance
        context_parts.append(get_daily_life_context())

    return "\n\n".join(context_parts)
