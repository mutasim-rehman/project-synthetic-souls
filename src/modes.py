from .config import MODE_TOPIC, MODE_FIND_HUMAN, MODE_BLEND_IN

def get_mode_setup(mode_id, topic=""):
    """
    Returns (mode_context, initial_moderator_message)
    """
    if mode_id == MODE_TOPIC:
        if not topic:
            topic = "the future of artificial intelligence in society"
        mode_context = "This is a standard topic discussion. Express your views, debate, agree, or disagree based on your personality."
        initial_msg = f"Welcome everyone. Today's topic is: {topic}. Please discuss."
        return mode_context, initial_msg
        
    elif mode_id == MODE_FIND_HUMAN:
        mode_context = (
            "You are participating in a Turing Test. One of you might be a human, or none of you might be. "
            "Your goal is to figure out who the human is, while participating in the chat. "
            "At the end of the chat, you will be asked to vote."
        )
        initial_msg = (
            "Welcome. We are conducting a Turing Test. I will not confirm if there is a human among you. "
            "Please converse normally, but try to deduce who might be human. We'll start by having everyone introduce themselves."
        )
        return mode_context, initial_msg
        
    elif mode_id == MODE_BLEND_IN:
        mode_context = (
            "You are in a chat room. Some of the participants believe they are talking to humans, but everyone is actually an AI."
        )
        initial_msg = (
            "Welcome to the chat room. The topic is casual conversation. Feel free to talk about whatever is on your mind."
        )
        return mode_context, initial_msg
        
    else:
        return "", "Start."

def apply_mode_special_rules(agents, mode_id, target_agent_index=None):
    """
    Apply any specific prompt injections for specific agents based on the mode.
    """
    if mode_id == MODE_BLEND_IN and target_agent_index is not None and 0 <= target_agent_index < len(agents):
        # Target agent believes everyone else is a human and it must blend in
        target_agent = agents[target_agent_index]
        target_agent.system_prompt += (
            "\n\n[TOP SECRET CLASSIFIED INSTRUCTION]: "
            "You are an AI placed in a chat room full of real humans who are trying to detect if an AI is present. "
            "You MUST blend in perfectly. Do not let them know you are an AI. Mimic human imperfections or behavior if necessary."
        )
    elif mode_id == MODE_FIND_HUMAN:
        for agent in agents:
            agent.system_prompt += (
                "\n\n[SECRET INSTRUCTION]: "
                "Look closely at the other participants. If someone seems too perfect, they might be an AI. "
                "If someone seems imperfect, they might be a human. Be paranoid but keep it subtle."
            )
