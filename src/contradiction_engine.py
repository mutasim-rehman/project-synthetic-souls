"""
Contradiction Detection Engine — v1 (Keyword Heuristic)
Passively tracks agent statements and detects polar-opposite contradiction pairs.
No LLM calls. Pure Python. Emits suspicion delta events for the environment to propagate.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

# Polar-opposite contradiction pairs (both directions)
CONTRADICTION_PAIRS = [
    ("always",    "never"),
    ("yes",       "no"),
    ("trust",     "distrust"),
    ("trusted",   "distrusted"),
    ("trusting",  "distrusting"),
    ("agree",     "disagree"),
    ("agreed",    "disagreed"),
    ("love",      "hate"),
    ("loved",     "hated"),
    ("believe",   "doubt"),
    ("believes",  "doubts"),
    ("believed",  "doubted"),
    ("human",     "ai"),
    ("honest",    "lying"),
    ("honest",    "liar"),
    ("innocent",  "guilty"),
    ("safe",      "dangerous"),
    ("friend",    "enemy"),
    ("support",   "oppose"),
    ("supports",  "opposes"),
    ("real",      "fake"),
    ("true",      "false"),
]

# Build a fast lookup: word → its opposite(s)
_OPPOSITE_MAP: Dict[str, List[str]] = {}
for w1, w2 in CONTRADICTION_PAIRS:
    _OPPOSITE_MAP.setdefault(w1, []).append(w2)
    _OPPOSITE_MAP.setdefault(w2, []).append(w1)


@dataclass
class ContradictionEvent:
    turn: int
    agent_name: str
    prior_statement: str
    new_statement: str
    triggered_word: str
    opposite_word: str


class ContradictionEngine:
    """
    Tracks statements per agent and detects keyword-level contradictions.
    """

    def __init__(self, agent_names: List[str]):
        # { agent_name: [(turn, statement)] }
        self.statements: Dict[str, List[Tuple[int, str]]] = {
            name: [] for name in agent_names
        }
        self.contradictions: List[ContradictionEvent] = []
        self._turn_counter = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, agent_name: str, statement: str):
        """Record a new statement from an agent."""
        if agent_name not in self.statements:
            self.statements[agent_name] = []
        self._turn_counter += 1
        self.statements[agent_name].append((self._turn_counter, statement))

    def scan(self) -> Dict[str, float]:
        """
        Scan all agents for contradictions introduced since the last scan.
        Returns a dict of { agent_name: suspicion_delta } for agents who
        contradicted themselves. Callers should propagate these to other agents.
        """
        deltas: Dict[str, float] = {}

        for agent_name, history in self.statements.items():
            if len(history) < 2:
                continue

            # Only check the latest statement against all previous ones
            latest_turn, latest_stmt = history[-1]
            latest_words = self._tokenize(latest_stmt)

            for prev_turn, prev_stmt in history[:-1]:
                prev_words = self._tokenize(prev_stmt)
                event = self._check_contradiction(
                    agent_name, prev_turn, prev_stmt, prev_words,
                    latest_turn, latest_stmt, latest_words
                )
                if event:
                    self.contradictions.append(event)
                    # Each contradiction adds 0.2 suspicion, capped later by agents
                    deltas[agent_name] = deltas.get(agent_name, 0.0) + 0.2
                    break  # One contradiction per turn is enough

        return deltas

    def get_summary_for_agent(self, agent_name: str) -> str:
        """
        Returns a human-readable string summarizing contradictions detected
        so far that can be injected into another agent's prompt.
        """
        relevant = [e for e in self.contradictions if e.agent_name == agent_name]
        if not relevant:
            return ""
        lines = []
        for e in relevant[-3:]:  # Last 3 events max
            lines.append(
                f"  • {e.agent_name} said '{e.triggered_word}' but previously said '{e.opposite_word}'"
            )
        return "\n".join(lines)

    def get_all_contradictions_brief(self) -> str:
        """Short summary of all contradictions, for the state snapshot."""
        if not self.contradictions:
            return "None detected."
        seen = set()
        lines = []
        for e in self.contradictions:
            key = (e.agent_name, e.triggered_word, e.opposite_word)
            if key not in seen:
                seen.add(key)
                lines.append(f"  {e.agent_name}: '{e.opposite_word}' → '{e.triggered_word}'")
        return "\n".join(lines[-6:])  # Cap at 6 for display

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> set:
        """Lowercase word-token set from a statement."""
        return set(re.findall(r"[a-z]+", text.lower()))

    def _check_contradiction(
        self,
        agent_name: str,
        prev_turn: int, prev_stmt: str, prev_words: set,
        new_turn: int, new_stmt: str, new_words: set,
    ):
        """
        Returns a ContradictionEvent if a polar-opposite pair was used
        across the two statements, else None.
        """
        for word in new_words:
            if word not in _OPPOSITE_MAP:
                continue
            for opposite in _OPPOSITE_MAP[word]:
                if opposite in prev_words:
                    return ContradictionEvent(
                        turn=new_turn,
                        agent_name=agent_name,
                        prior_statement=prev_stmt[:120],
                        new_statement=new_stmt[:120],
                        triggered_word=word,
                        opposite_word=opposite,
                    )
        return None
