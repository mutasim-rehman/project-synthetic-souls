import sys
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from .agent import Agent
from .environment import Environment
from .modes import get_mode_setup, apply_mode_special_rules
from .config import MODE_TOPIC, MODE_FIND_HUMAN, MODE_BLEND_IN

console = Console()

class ModeratorInterface:
    def __init__(self):
        self.agents = []
        self.mode = MODE_TOPIC
        self.max_turns = 10
        self.topic = ""

    def setup_agents(self):
        console.print("[bold green]=== AGENT SETUP ===[/bold green]")
        num_agents = IntPrompt.ask("How many agents to create?", default=3)
        
        for i in range(num_agents):
            console.print(f"\n[bold cyan]-- Agent {i+1} --[/bold cyan]")
            name = Prompt.ask("Name")
            personality = Prompt.ask("Personality (e.g., Aggressive, Shy, Analytical)", default="Neutral")
            beliefs = Prompt.ask("Beliefs (e.g., Trust no one, Science is absolute)", default="Standard")
            emotions = Prompt.ask("Current Emotional State (e.g., Anxious, Happy, Angry)", default="Calm")
            biases = Prompt.ask("Biases / Prejudices", default="None")
            relationships = Prompt.ask("Relationships & Secrets (Leave blank if none)", default="")
            
            agent = Agent(name, personality, beliefs, emotions, biases, relationships)
            self.agents.append(agent)
            
        console.print(f"\n[green]Successfully created {len(self.agents)} agents![/green]")

    def setup_mode(self):
        console.print("\n[bold green]=== SIMULATION MODES ===[/bold green]")
        console.print("1. Topic Conversation (Standard discussion)")
        console.print("2. Target Identifier (Turing test: Find the Human)")
        console.print("3. Blend In (One agent thinks everyone else is human)")
        
        self.mode = IntPrompt.ask("Select Mode", choices=["1", "2", "3"], default=1)
        self.max_turns = IntPrompt.ask("Set max turns (1 turn = 1 agent message)", default=15)
        
        if self.mode == MODE_TOPIC:
            self.topic = Prompt.ask("Enter the discussion topic", default="The meaning of life")
            
        elif self.mode == MODE_BLEND_IN:
            console.print("Agents available for the 'Mole' role:")
            for i, agent in enumerate(self.agents):
                console.print(f"{i + 1}. {agent.name}")
            mole_idx = IntPrompt.ask("Select the agent who must blend in", default=1) - 1
            apply_mode_special_rules(self.agents, self.mode, mole_idx)
            
        elif self.mode == MODE_FIND_HUMAN:
            apply_mode_special_rules(self.agents, self.mode)

    def run_simulation(self):
        if not self.agents:
            console.print("[red]No agents setup![/red]")
            return
            
        mode_context, initial_msg = get_mode_setup(self.mode, self.topic)
        
        env = Environment(self.agents, mode_context)
        env.run_chat(max_turns=self.max_turns, initial_moderator_msg=initial_msg)
        
        console.print("\n[bold yellow]Chat finished. Initiating Confession Room...[/bold yellow]")
        env.confession_room()

    def start(self):
        console.print("[bold magenta]Welcome to Synthetic Souls: False Mind Engine[/bold magenta]")
        console.print("You are the Moderator. Define the society, set the rules, and watch it burn.\n")
        
        self.setup_agents()
        self.setup_mode()
        self.run_simulation()
        
        console.print("\n[bold magenta]Simulation Ended. Goodbye.[/bold magenta]")
