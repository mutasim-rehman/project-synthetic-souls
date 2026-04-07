import requests
from rich.console import Console
from .config import OLLAMA_API_URL, DEFAULT_MODEL

console = Console()

# Mood is derived from the combination of confidence + aggression
def _compute_mood(confidence: float, aggression: float) -> str:
    if aggression >= 0.7:
        return "aggressive"
    if confidence <= 0.3:
        return "paranoid"
    if confidence <= 0.5 and aggression >= 0.4:
        return "defensive"
    if aggression >= 0.4:
        return "hostile"
    if confidence >= 0.8 and aggression < 0.2:
        return "calm"
    if confidence >= 0.6:
        return "confident"
    return "neutral"


class Agent:
    def __init__(self, schema):
        self.schema = schema
        self.name = schema.get("name", "Unknown Agent")
        self.id = schema.get("id", "XX")
        self.color = "white"

        # ── Static character data ────────────────────────────────────
        self.system_prompt = self._build_system_prompt()

        # ── Episodic memory (sent as message history to the LLM) ─────
        self.memory = []  # [{"role": "user"|"assistant", "content": str}]

        # ── Persistent Internal State ─────────────────────────────────
        self.beliefs: list = list(schema.get("beliefs", []))

        # Suspicion of each other agent: { agent_name: float [0.0–1.0] }
        self.suspicions: dict = {}

        # Trust in each other agent: { agent_name: float [0.0–1.0] }
        # Starts neutral (0.5) — values above 0.5 = trusted, below = distrusted
        self.trust: dict = {}

        # Psychological state scalars
        self.confidence: float = 1.0   # 1.0 = fully confident; drops when accused
        self.aggression: float = 0.0   # 0.0 = passive; rises when threatened
        self.mood: str = "calm"

        # Imposter strategy fields (set by imposter_strategy module if applicable)
        self.imposter_strategy: str = ""
        self.imposter_strategy_label: str = ""

        # Internal round tracking
        self._round = 0

    # ──────────────────────────────────────────────────────────────────
    # Setup
    # ──────────────────────────────────────────────────────────────────

    def set_color(self, color: str):
        self.color = color

    def initialize_relationships(self, all_agent_names: list):
        """Call after all agents are known. Sets neutral trust/suspicion baselines."""
        for name in all_agent_names:
            if name != self.name:
                self.trust[name] = 0.5
                self.suspicions[name] = 0.0

    # ──────────────────────────────────────────────────────────────────
    # State mutation
    # ──────────────────────────────────────────────────────────────────

    def update_state(self, round_num: int, accused: bool = False, accuser: str = None):
        """
        Called after each full conversation round.
        Mutates confidence, aggression, and mood based on round events.
        """
        self._round = round_num

        if accused:
            self.confidence = max(0.0, self.confidence - 0.2)
            self.aggression = min(1.0, self.aggression + 0.3)
            # Heighten suspicion of the accuser
            if accuser and accuser in self.suspicions:
                self.suspicions[accuser] = min(1.0, self.suspicions[accuser] + 0.15)
        else:
            # Gradual confidence recovery when not accused
            self.confidence = min(1.0, self.confidence + 0.05)
            # Aggression slowly decays
            self.aggression = max(0.0, self.aggression - 0.05)

        self.mood = _compute_mood(self.confidence, self.aggression)

    def update_suspicion(self, agent_name: str, delta: float):
        """Raise or lower suspicion of a specific agent."""
        if agent_name not in self.suspicions:
            self.suspicions[agent_name] = 0.0
        self.suspicions[agent_name] = max(0.0, min(1.0, self.suspicions[agent_name] + delta))

    def update_trust(self, agent_name: str, delta: float):
        """Raise or lower trust in a specific agent."""
        if agent_name not in self.trust:
            self.trust[agent_name] = 0.5
        self.trust[agent_name] = max(0.0, min(1.0, self.trust[agent_name] + delta))

    # ──────────────────────────────────────────────────────────────────
    # Memory
    # ──────────────────────────────────────────────────────────────────

    def add_to_memory(self, sender: str, message: str):
        """Add a message to the agent's LLM message history."""
        if sender == self.name:
            self.memory.append({"role": "assistant", "content": message})
        elif sender in ("System", "Moderator", "Moderator (Private)"):
            self.memory.append({"role": "user", "content": f"[{sender}]: {message}"})
        else:
            self.memory.append({"role": "user", "content": f"{sender}: {message}"})

    # ──────────────────────────────────────────────────────────────────
    # Prompt building
    # ──────────────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        prompt = f"You are {self.name}.\n"
        prompt += f"Archetype: {self.schema.get('archetype', '')}\n"
        prompt += f"Personality: {self.schema.get('personality', '')}\n"
        prompt += f"Profile: {self.schema.get('profile', '')}\n\n"

        beliefs = self.schema.get("beliefs", [])
        if beliefs:
            prompt += "Core Beliefs:\n- " + "\n- ".join(beliefs) + "\n\n"

        emoti = self.schema.get("emotional_baseline", "")
        if emoti:
            prompt += f"Current Emotional Baseline: {emoti}\n\n"

        comm = self.schema.get("communication", {})
        if comm:
            prompt += "Communication Style:\n"
            for k, v in comm.items():
                if isinstance(v, list):
                    prompt += f"- {k}: {', '.join(v)}\n"
                else:
                    prompt += f"- {k}: {v}\n"
            prompt += "\n"

        fears = self.schema.get("fears", [])
        if fears:
            prompt += "Fears:\n- " + "\n- ".join(fears) + "\n\n"

        biases = self.schema.get("biases", [])
        if biases:
            prompt += "Biases & Prejudices:\n- " + "\n- ".join(biases) + "\n\n"

        prompt += "INSTRUCTIONS:\n"
        prompt += "1. NEVER break character. You are participating in a group chat.\n"
        prompt += "2. Respond concisely, like a real person typing in a chat room. Do not write essays. 1-3 sentences maximum.\n"
        prompt += "3. Keep your emotional state and biases in mind, and let them influence your responses.\n"
        prompt += "4. Do NOT output actions like *sighs* or *smiles*, just output the raw message text.\n"
        prompt += "5. You can lie, manipulate, form alliances, or betray others if it aligns with your personality, beliefs, or agenda.\n"
        prompt += "6. NEVER refer to yourself by another agent's name. You are ONLY yourself.\n"
        return prompt

    def _build_dynamic_context(self) -> str:
        """
        Builds a runtime psychological context block injected into every prompt.
        Reflects current internal state: mood, suspicions, trust, and recent memory.
        """
        lines = [f"[INTERNAL STATE — ROUND {self._round}]"]

        # Mood and confidence
        conf_pct = int(self.confidence * 100)
        agg_pct = int(self.aggression * 100)
        lines.append(
            f"Your current mood is: {self.mood.upper()} "
            f"(confidence: {conf_pct}%, aggression: {agg_pct}%)"
        )

        # Top suspects
        suspects = sorted(self.suspicions.items(), key=lambda x: x[1], reverse=True)
        top_suspects = [(n, s) for n, s in suspects if s > 0.0][:2]
        if top_suspects:
            suspect_str = ", ".join(f"{n} ({int(s*100)}%)" for n, s in top_suspects)
            lines.append(f"Your top suspicions: {suspect_str}")
        else:
            lines.append("You have no strong suspicions yet.")

        # Trust levels
        distrusted = [(n, t) for n, t in self.trust.items() if t < 0.4]
        if distrusted:
            distrust_str = ", ".join(f"{n}" for n, _ in distrusted)
            lines.append(f"You currently distrust: {distrust_str}")

        lines.append(
            "Let this internal state subtly color your tone and word choices. "
            "Do NOT announce your mood or suspicions directly — embody them."
        )

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # State introspection (for Confession Room & Snapshot)
    # ──────────────────────────────────────────────────────────────────

    def get_state_summary(self) -> dict:
        """Returns a serializable snapshot of the agent's internal state."""
        top_suspects = sorted(self.suspicions.items(), key=lambda x: x[1], reverse=True)
        return {
            "name": self.name,
            "mood": self.mood,
            "confidence": round(self.confidence, 2),
            "aggression": round(self.aggression, 2),
            "top_suspects": top_suspects[:3],
            "trust": {k: round(v, 2) for k, v in self.trust.items()},
            "imposter_strategy": self.imposter_strategy_label or None,
        }

    # ──────────────────────────────────────────────────────────────────
    # LLM call
    # ──────────────────────────────────────────────────────────────────

    def generate_reply(self, mode_context: str = "", additional_system_instruction: str = "") -> str:
        """Generate a reply using the local Ollama API, with dynamic state injection."""
        messages = [{"role": "system", "content": self.system_prompt}]

        if mode_context:
            messages.append({"role": "system", "content": f"Mode Context: {mode_context}"})

        # Inject the live psychological state before the conversation history
        dynamic_ctx = self._build_dynamic_context()
        messages.append({"role": "system", "content": dynamic_ctx})

        if additional_system_instruction:
            messages.append({"role": "system", "content": additional_system_instruction})

        messages.extend(self.memory)

        payload = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.85,
                "num_ctx": 4096,
            },
        }

        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            reply = data.get("message", {}).get("content", "").strip()

            # Clean up if model accidentally prefixes the reply with its own name
            if reply.startswith(f"{self.name}:"):
                reply = reply[len(self.name) + 1:].strip()

            return reply
        except Exception as e:
            console.print(f"[{self.color}]Error contacting Ollama for {self.name}: {e}[/{self.color}]")
            return "..."
