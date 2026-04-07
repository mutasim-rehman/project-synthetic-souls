from .config import MODE_TOPIC, MODE_IMPOSTER, MODE_BLEND_IN
from .imposter_strategy import assign_imposter_strategy

def get_mode_setup(mode_id, topic=""):
    """
    Returns (mode_context, initial_moderator_message)
    """
    if mode_id == MODE_TOPIC:
        if not topic:
            topic = "the future of artificial intelligence in society"
        mode_context = (
            "This is a standard topic discussion. Express your views, debate, agree, or disagree "
            "based on your personality. Your internal suspicion and trust levels will subtly color "
            "how you engage with each participant."
        )
        initial_msg = f"Welcome everyone. Today's topic is: {topic}. Please discuss."
        return mode_context, initial_msg

    elif mode_id == MODE_IMPOSTER:
        mode_context = (
            "You are playing 'Find the Imposter'. One of the agents in this chat is the imposter. "
            "Your goal is to figure out who the imposter is based on their answers, while acting naturally. "
            "If you are the imposter, you have a hidden strategy — execute it without revealing it. "
            "Let your suspicion scores guide your observations. The Moderator will ask questions. Answer in character."
        )
        initial_msg = (
            "Welcome to Find the Imposter. One of you is the designated imposter with a hidden agenda. "
            "I will ask 10 questions. Everyone must answer. At the end, you will all vote on who is the imposter."
        )
        return mode_context, initial_msg

    elif mode_id == MODE_BLEND_IN:
        mode_context = (
            "You are in a chat room. Some participants believe they are talking to humans, "
            "but everyone is actually an AI. Trust nobody completely. Your suspicion system is active."
        )
        initial_msg = (
            "Welcome to the chat room. The topic is casual conversation. Feel free to talk about whatever is on your mind."
        )
        return mode_context, initial_msg

    else:
        return "", "Start."


def apply_mode_special_rules(agents, mode_id, target_agent_index=None):
    """
    Apply specific prompt injections for agents based on the mode.
    For imposter mode, assigns a randomized hidden strategy.
    """
    if mode_id == MODE_BLEND_IN and target_agent_index is not None and 0 <= target_agent_index < len(agents):
        target_agent = agents[target_agent_index]
        target_agent.system_prompt += (
            "\n\n[TOP SECRET CLASSIFIED INSTRUCTION]: "
            "You are an AI placed in a chat room full of real humans who are trying to detect if an AI is present. "
            "You MUST blend in perfectly. Do not let them know you are an AI. Mimic human imperfections or behavior if necessary."
        )

    elif mode_id == MODE_IMPOSTER:
        for i, agent in enumerate(agents):
            if i == target_agent_index:
                # Assign a hidden strategy — this injects the full hidden objective
                strategy_key = assign_imposter_strategy(agent)
                # Base imposter instruction is already inside assign_imposter_strategy
                # Add the basic "don't get caught" framing on top
                agent.system_prompt += (
                    "\n\n[IMPOSTER CORE RULE]: Do not reveal you are the imposter. "
                    "Deflect suspicion if accused. Your hidden strategy above is your PRIMARY tool."
                )
            else:
                agent.system_prompt += (
                    "\n\n[SECRET INSTRUCTION]: "
                    "You are a regular participant. One of the other agents is the imposter with a hidden agenda. "
                    "Analyze their answers carefully. Trust your suspicion scores — they update in real time. "
                    "Do not falsely claim to be the imposter."
                )
