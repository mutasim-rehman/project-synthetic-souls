import time
from rich.console import Console

console = Console()

class Environment:
    def __init__(self, agents, mode_context=""):
        """
        agents: list of Agent objects
        mode_context: string describing the mode and its rules for the conversation
        """
        self.agents = agents
        self.mode_context = mode_context
        self.history = [] # Global chat history
        
        # Assign colors for UI distinction
        colors = ["cyan", "magenta", "green", "yellow", "blue", "red"]
        for i, agent in enumerate(self.agents):
            agent.set_color(colors[i % len(colors)])

    def broadcast(self, sender, message):
        """Broadcast a message to all agents."""
        if sender != "Moderator" and sender != "System":
            # Find the sender's color
            sender_color = "white"
            for agent in self.agents:
                if agent.name == sender:
                    sender_color = agent.color
                    break
            console.print(f"[{sender_color}][{sender}]:[/{sender_color}] {message}")
        else:
            console.print(f"[bold white][{sender}]: {message}[/bold white]")

        self.history.append({"sender": sender, "message": message})
        
        for agent in self.agents:
            agent.add_to_memory(sender, message)

    def run_chat(self, max_turns=10, initial_moderator_msg=""):
        """
        Runs the group chat in a round-robin format or dynamic format.
        For simplicity, we use strict round-robin here.
        """
        console.print("\n[bold rgb(175,0,255)]--- The Chat Room is now OPEN ---[/bold rgb(175,0,255)]\n")
        
        if initial_moderator_msg:
            self.broadcast("Moderator", initial_moderator_msg)

        turn_count = 0
        while turn_count < max_turns:
            agent = self.agents[turn_count % len(self.agents)]
            
            # Show a thinking indicator
            with console.status(f"[{agent.color}]{agent.name} is typing...[/{agent.color}]"):
                reply = agent.generate_reply(mode_context=self.mode_context)
            
            if reply:
                self.broadcast(agent.name, reply)
            else:
                self.broadcast(agent.name, "*stays silent*")
                
            turn_count += 1
            time.sleep(1.5) # Slight pause for readability
            
        console.print("\n[bold rgb(175,0,255)]--- The Chat Room is now CLOSED ---[/bold rgb(175,0,255)]\n")

    def run_imposter_mode(self, initial_moderator_msg=""):
        """Runs the custom flow for Find the Imposter mode."""
        console.print("\n[bold rgb(175,0,255)]--- Imposter Mode Started ---[/bold rgb(175,0,255)]\n")
        
        if initial_moderator_msg:
            self.broadcast("Moderator", initial_moderator_msg)
            
        from rich.prompt import Prompt
        num_questions = 10
        
        for q_idx in range(num_questions):
            question = Prompt.ask(f"\n[bold white]Moderator (Enter Question {q_idx+1}/{num_questions})[/bold white]")
            self.broadcast("Moderator", question)
            
            for agent in self.agents:
                with console.status(f"[{agent.color}]{agent.name} is thinking...[/{agent.color}]"):
                    reply = agent.generate_reply(mode_context=self.mode_context)
                
                if reply:
                    self.broadcast(agent.name, reply)
                else:
                    self.broadcast(agent.name, "*stays silent*")
                time.sleep(1.0)
                
        # Voting phase
        self.broadcast("Moderator", "The questions have concluded. It is now time to vote. Each of you must state who you think the imposter is and provide your reasoning.")
        for agent in self.agents:
            with console.status(f"[{agent.color}]{agent.name} is making their final decision...[/{agent.color}]"):
                reply = agent.generate_reply(
                    mode_context=self.mode_context,
                    additional_system_instruction="The game is strictly over. Conclude by explicitly stating who you think the imposter is among the other agents and briefly explain your reasoning (even if you are the imposter!). This is your final vote."
                )
            if reply:
                self.broadcast(agent.name, reply)
            else:
                self.broadcast(agent.name, "*stays silent*")
            time.sleep(1.5)
            
        console.print("\n[bold rgb(175,0,255)]--- Imposter Mode Ended ---[/bold rgb(175,0,255)]\n")

    def confession_room(self):
        """Allows humans to interview agents privately after the chat."""
        from rich.prompt import Prompt
        import sys
        
        while True:
            console.print("\n[bold]=== CONFESSION ROOM ===[/bold]")
            console.print("Agents available for interview in the Confession Room:")
            for i, agent in enumerate(self.agents):
                console.print(f"{i + 1}. [{agent.color}]{agent.name}[/{agent.color}]")
            console.print("0. Exit Simulation")
            
            choice = Prompt.ask("Select an agent to interview", default="0")
            
            if choice == "0":
                break
                
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.agents):
                    selected_agent = self.agents[idx]
                    self._interview_agent(selected_agent)
                else:
                    console.print("[red]Invalid selection.[/red]")
            except ValueError:
                console.print("[red]Invalid input.[/red]")

    def _interview_agent(self, agent):
        """1-on-1 interview loop with an agent."""
        from rich.prompt import Prompt
        
        console.print(f"\n[bold]You are now privately interviewing [{agent.color}]{agent.name}[/{agent.color}].[/bold]")
        console.print("They retain all memory of the chat. Type 'exit' to return to the selection menu.")
        
        system_instruction = "You are in a private Confession Room with the Moderator. Be honest about your thoughts, strategies, and lies during the chat."
        
        while True:
            human_msg = Prompt.ask("[bold white]Moderator[/bold white]")
            if human_msg.lower() == "exit":
                break
                
            agent.add_to_memory("Moderator (Private)", human_msg)
            
            with console.status(f"[{agent.color}]{agent.name} is responding...[/{agent.color}]"):
                reply = agent.generate_reply(
                    mode_context=self.mode_context,
                    additional_system_instruction=system_instruction
                )
                
            console.print(f"[{agent.color}][{agent.name}]:[/{agent.color}] {reply}")
            agent.add_to_memory(agent.name, reply)
