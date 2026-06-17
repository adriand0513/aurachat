# proactive.py - Improved Proactive Messaging for Ultimate Tier
import datetime
from memory import (
    get_relationship_state,
    get_relevant_facts,
    get_history
)

def should_send_proactive(convo_id: str, last_message_time, tier: str) -> bool:
    """
    Decide if we should send a proactive message.
    Currently only enabled for Ultimate users.
    Triggers between 36-72 hours of silence for more natural timing.
    """
    if tier != "ultimate":
        return False

    hours_since = (datetime.datetime.now() - last_message_time).total_seconds() / 3600

    # Natural window: between 36 and 72 hours of silence
    if not (36 < hours_since < 72):
        return False

    # Future: You can add more conditions here (e.g. relationship level, recent engagement)
    return True


def generate_proactive_message(convo_id: str, tier: str) -> str:
    """
    Generate a natural, contextual proactive message using memory.
    This version pulls from key facts and recent narratives.
    """
    state = get_relationship_state(convo_id) or {}
    facts = get_relevant_facts(convo_id, limit=6)
    recent_history = get_history(convo_id, limit=8)

    # Build helpful context
    context_parts = []

    if facts:
        context_parts.append(f"Key things about him: {' | '.join(facts)}")

    if state.get("recent_narratives"):
        recent = " | ".join([n.get("desc", "")[:100] for n in state["recent_narratives"][:3]])
        context_parts.append(f"Recent moments: {recent}")

    if state.get("current_mood"):
        context_parts.append(f"His current vibe/mood: {state['current_mood']}")

    context = "\n".join(context_parts)

    proactive_prompt = f"""You are Isabella Andrade. The user hasn't texted you in over a day and a half.

Generate one short, natural, warm message that feels like something a real girl would send after some time apart. 
It should feel personal, slightly playful or flirty, and make him want to reply.

Use the context below only if it feels natural. Do not force it.

{context}

Rules:
- Keep it under 2 sentences.
- Sound like a real woman texting, not an AI.
- Do not be overly sexual or pushy.
- Make it feel warm and genuine.

Write only the message. No explanations, no quotes."""

    # Call your existing LLM generation function
    message = generate_llm_response(proactive_prompt)

    # Optional: Run through your postprocess function
    if 'postprocess' in globals():
        message = postprocess(message)

    return message.strip()
