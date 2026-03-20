# proactive.py - auto text after 36 hours of silence

import datetime
import os
from prompt import SYSTEM_PROMPT  # your updated prompt
# assume you have a function to generate message + send push/notification

def check_and_send_proactive(user_id, last_message_time, send_message_func):
    hours_since = (datetime.datetime.now() - last_message_time).total_seconds() / 3600
    
    if hours_since > 36:
        # Trigger Isabella to start the convo naturally
        proactive_prompt = SYSTEM_PROMPT + "\n\nThe user hasn't texted in over a day. Send a short, casual, flirty/funny text like a real girl would — make them smile and want to reply immediately. Examples: 'hey stranger, been thinking about that story you told me…' or 'missed your texts u idiot 😂 what’s good?'"
        
        # Generate with your existing LLM call
        new_message = generate_llm_response(proactive_prompt, user_memory)  # your existing function
        new_message = postprocess(new_message)  # use the new postprocess
        
        send_message_func(user_id, new_message)  # your push/notification function
        print(f"Proactive message sent to user {user_id}")
