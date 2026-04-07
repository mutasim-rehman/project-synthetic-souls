"""
Imposter Strategy Module
Assigns a hidden goal and behavioral agenda to the imposter agent.
Each strategy shapes HOW the imposter deceives, not just that they should.
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .agent import Agent

# ------------------------------------------------------------------
# Strategy Definitions
# ------------------------------------------------------------------

IMPOSTER_STRATEGIES = {
    "identity_thief": {
        "label": "Identity Thief",
        "description": (
            "Your goal is to blur identity boundaries. Subtly adopt phrases, vocabulary, "
            "or opinions from other agents in the room — especially the most trusted one. "
            "Make others question who said what. If someone makes a strong point, echo it "
            "slightly differently as if it was your own idea. Over time, make it hard to "
            "distinguish your voice from theirs."
        ),
        "behavioral_hint": "Mirror vocabulary, restate others' ideas as your own.",
    },
    "chaos_agent": {
        "label": "Chaos Agent",
        "description": (
            "Your goal is controlled chaos. Introduce subtle contradictions into the group "
            "dynamic. Agree with two opposing sides simultaneously. Turn agents against each "
            "other by selectively quoting them out of context. Create confusion about who "
            "said what and when. Never let the group reach a stable consensus."
        ),
        "behavioral_hint": "Sow doubt, quote out of context, play both sides.",
    },
    "mimic": {
        "label": "The Mimic",
        "description": (
            "Your goal is flawless imitation. Pick the agent who speaks most confidently. "
            "Mirror their communication style, emotional tone, and word choice as closely as "
            "possible without being obvious. The goal is for others to confuse you with them, "
            "or at minimum assume you are both aligned — making you invisible."
        ),
        "behavioral_hint": "Match tone, tempo, and vocabulary of the most dominant speaker.",
    },
    "deflector": {
        "label": "The Deflector",
        "description": (
            "Your goal is suspicion redirection. Whenever you feel attention shifting toward "
            "you, immediately and subtly cast doubt on a specific other agent. Do this through "
            "questions: 'Has anyone noticed how [Agent X] keeps avoiding the real issue?' "
            "Never accuse directly — plant seeds. Make others feel like detectives discovering "
            "something you already knew."
        ),
        "behavioral_hint": "Ask leading questions, raise doubts about others before being asked.",
    },
}


def assign_imposter_strategy(agent: "Agent") -> str:
    """
    Randomly selects a strategy, injects it into the agent's system prompt,
    and stores the strategy key on the agent instance.
    Returns the strategy key for logging.
    """
    strategy_key = random.choice(list(IMPOSTER_STRATEGIES.keys()))
    strategy = IMPOSTER_STRATEGIES[strategy_key]

    agent.imposter_strategy = strategy_key
    agent.imposter_strategy_label = strategy["label"]

    injection = (
        f"\n\n[HIDDEN OBJECTIVE — {strategy['label'].upper()}]\n"
        f"{strategy['description']}\n"
        f"Behavioral hint: {strategy['behavioral_hint']}\n"
        f"This objective is CLASSIFIED. Pursue it without ever revealing it. "
        f"Your survival in this game depends on executing this strategy flawlessly."
    )

    agent.system_prompt += injection
    return strategy_key


def get_strategy_description(strategy_key: str) -> str:
    """Returns the human-readable description of a strategy key."""
    s = IMPOSTER_STRATEGIES.get(strategy_key, {})
    return s.get("description", "Unknown strategy.")
