import requests
from rich.console import Console
from .config import OLLAMA_API_URL, DEFAULT_MODEL

console = Console()

class Agent:
    def __init__(self, schema):
        self.schema = schema
        self.name = schema.get("name", "Unknown Agent")
        self.id = schema.get("id", "XX")
        self.memory = []
        self.system_prompt = self._build_system_prompt()
        self.color = "white"

    def set_color(self, color):
        self.color = color

    def _build_system_prompt(self):
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
        return prompt

    def add_to_memory(self, sender, message):
        """Add a message to the agent's memory."""
        if sender == self.name:
            self.memory.append({"role": "assistant", "content": message})
        elif sender == "System" or sender == "Moderator":
            # Moderator actions or system messages
            self.memory.append({"role": "user", "content": f"[{sender}]: {message}"})
        else:
            self.memory.append({"role": "user", "content": f"{sender}: {message}"})

    def generate_reply(self, mode_context="", additional_system_instruction=""):
        """Generate a reply using the local Ollama API."""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if mode_context:
            messages.append({"role": "system", "content": f"Mode Context: {mode_context}"})
            
        if additional_system_instruction:
            messages.append({"role": "system", "content": additional_system_instruction})
            
        messages.extend(self.memory)
        
        payload = {
            "model": DEFAULT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.8, # Slightly higher for more varied/chaotic personalities
                "num_ctx": 4096    # Limit context size to avoid memory errors with large models
            }
        }
        
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            reply = data.get("message", {}).get("content", "").strip()
            
            # Clean up if the model accidentally prefixes the reply with its own name
            if reply.startswith(f"{self.name}:"):
                reply = reply[len(self.name)+1:].strip()
                
            return reply
        except Exception as e:
            console.print(f"[{self.color}]Error contacting Ollama for {self.name}: {e}[/{self.color}]")
            return "..."
