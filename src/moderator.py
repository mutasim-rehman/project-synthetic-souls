import sys
import json
import os
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from .agent import Agent
from .environment import Environment
from .modes import get_mode_setup, apply_mode_special_rules
from .config import MODE_TOPIC, MODE_IMPOSTER, MODE_BLEND_IN

console = Console()

class ModeratorInterface:
    def __init__(self):
        self.agents = []
        self.mode = MODE_TOPIC
        self.max_turns = 10
        self.topic = ""

    def setup_agents(self):
        console.print("[bold green]=== AGENT SETUP ===[/bold green]")
        schema_path = os.path.join(os.path.dirname(__file__), "personality_schema.json")
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schemas = json.load(f)
        except Exception as e:
            console.print(f"[bold red]Failed to load personality schemas: {e}[/bold red]")
            return
            
        console.print("\n[bold blue]Available Agents from Schema:[/bold blue]")
        for i, schema in enumerate(schemas):
            console.print(f"{i + 1}. [bold cyan]{schema.get('name', 'Unknown')}[/bold cyan] - {schema.get('archetype', '')}")
            console.print(f"   [yellow]Personality:[/yellow] {schema.get('personality', '')}")
            profile = schema.get('profile', '')
            if len(profile) > 100:
                profile = profile[:100] + "..."
            console.print(f"   [yellow]Profile:[/yellow] {profile}\n")
            
        selected_raw = Prompt.ask("Enter comma-separated numbers of agents to include (e.g. 1,3,4)", default="1,2,3")
        indices = [int(i.strip()) - 1 for i in selected_raw.split(",") if i.strip().isdigit()]
        
        for idx in indices:
            if 0 <= idx < len(schemas):
                agent = Agent(schemas[idx])
                self.agents.append(agent)
                
        console.print(f"\n[green]Successfully loaded {len(self.agents)} agents![/green]")

    def setup_mode(self):
        console.print("\n[bold green]=== SIMULATION MODES ===[/bold green]")
        console.print("1. Topic Conversation (Standard discussion)")
        console.print("2. Find the Imposter (Moderator asks Qs, agents vote)")
        console.print("3. Blend In (One agent thinks everyone else is human)")
        
        self.mode = IntPrompt.ask("Select Mode", choices=["1", "2", "3"], default=1)
        if self.mode != MODE_IMPOSTER:
            self.max_turns = IntPrompt.ask("Set max turns (1 turn = 1 agent message)", default=15)
        
        if self.mode == MODE_TOPIC:
            self.topic = Prompt.ask("Enter the discussion topic", default="The meaning of life")
            
        elif self.mode == MODE_BLEND_IN:
            console.print("Agents available for the 'Mole' role:")
            for i, agent in enumerate(self.agents):
                console.print(f"{i + 1}. {agent.name}")
            mole_idx = IntPrompt.ask("Select the agent who must blend in", default=1) - 1
            apply_mode_special_rules(self.agents, self.mode, mole_idx)
            
        elif self.mode == MODE_IMPOSTER:
            console.print("Agents available for the 'Imposter' role:")
            for i, agent in enumerate(self.agents):
                console.print(f"{i + 1}. {agent.name}")
            imposter_idx = IntPrompt.ask("Select the agent to be the imposter", default=1) - 1
            apply_mode_special_rules(self.agents, self.mode, imposter_idx)

    def run_simulation(self):
        if not self.agents:
            console.print("[red]No agents setup![/red]")
            return
            
        mode_context, initial_msg = get_mode_setup(self.mode, self.topic)
        
        env = Environment(self.agents, mode_context)
        
        if self.mode == MODE_IMPOSTER:
            env.run_imposter_mode(initial_msg)
        else:
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
