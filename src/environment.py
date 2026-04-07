import time
import re
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from .contradiction_engine import ContradictionEngine

console = Console()


class Environment:
    def __init__(self, agents, mode_context=""):
        """
        agents: list of Agent objects
        mode_context: string describing the mode and its rules for the conversation
        """
        self.agents = agents
        self.mode_context = mode_context
        self.history = []   # Global chat history: [{"sender": str, "message": str}]
        self._round = 0     # Tracks full conversation rounds

        # Assign colors for UI distinction
        colors = ["cyan", "magenta", "green", "yellow", "blue", "red"]
        for i, agent in enumerate(self.agents):
            agent.set_color(colors[i % len(colors)])

        # Wire up relationships now that all agents are known
        all_names = [a.name for a in self.agents]
        for agent in self.agents:
            agent.initialize_relationships(all_names)

        # Contradiction engine
        self.contradiction_engine = ContradictionEngine(all_names)

    # ──────────────────────────────────────────────────────────────────
    # Messaging
    # ──────────────────────────────────────────────────────────────────

    def broadcast(self, sender: str, message: str):
        """Broadcast a message to all agents and display it."""
        if sender not in ("Moderator", "System"):
            sender_color = next(
                (a.color for a in self.agents if a.name == sender), "white"
            )
            console.print(f"[{sender_color}][{sender}]:[/{sender_color}] {message}")
        else:
            console.print(f"[bold white][{sender}]: {message}[/bold white]")

        self.history.append({"sender": sender, "message": message})

        # Feed into all agents' LLM memory
        for agent in self.agents:
            agent.add_to_memory(sender, message)

        # Feed into contradiction engine (only agent speech, not system messages)
        if sender not in ("Moderator", "System"):
            self.contradiction_engine.record(sender, message)

    # ──────────────────────────────────────────────────────────────────
    # Post-message processing
    # ──────────────────────────────────────────────────────────────────

    def _process_contradictions_and_state(self, speaker_name: str, reply: str):
        """
        After an agent speaks:
        1. Scan for contradictions → emit suspicion deltas.
        2. Propagate deltas to all OTHER agents' suspicion scores.
        3. Check if the message accuses anyone, update accused agent's state.
        """
        deltas = self.contradiction_engine.scan()

        # Propagate suspicion deltas to every agent except the one who contradicted
        for contradicting_agent_name, delta in deltas.items():
            for agent in self.agents:
                if agent.name != contradicting_agent_name:
                    agent.update_suspicion(contradicting_agent_name, delta)

        # Detect accusation patterns in the new message
        self._detect_and_apply_accusation(speaker_name, reply)

    def _detect_and_apply_accusation(self, speaker_name: str, reply: str):
        """
        Heuristic: if the spoken reply mentions another agent's name alongside
        accusatory keywords, mark that agent as 'accused' this round.
        """
        accusatory_keywords = [
            "imposter", "lying", "liar", "fake", "suspicious", "suspect",
            "deceiving", "manipulating", "not real", "acting weird",
            "hiding something", "not telling the truth",
        ]
        reply_lower = reply.lower()
        has_accusation = any(kw in reply_lower for kw in accusatory_keywords)

        if not has_accusation:
            return

        for agent in self.agents:
            if agent.name == speaker_name:
                continue
            if agent.name.lower() in reply_lower:
                agent.update_state(self._round, accused=True, accuser=speaker_name)
                # The speaker gains a little trust for actively engaging
                for a in self.agents:
                    if a.name == speaker_name:
                        a.update_trust(agent.name, -0.1)  # Accusation lowers trust in accused

    def _end_of_round_update(self):
        """Called after every agent has spoken once (a full round)."""
        self._round += 1
        for agent in self.agents:
            # Non-accused agents recover slightly each round
            agent.update_state(self._round, accused=False)

    # ──────────────────────────────────────────────────────────────────
    # State Snapshot Display
    # ──────────────────────────────────────────────────────────────────

    def _print_state_snapshot(self):
        """Prints a rich table showing all agents' current psychological state."""
        table = Table(
            title=f"[bold]🧠 Round {self._round} — Internal State Snapshot[/bold]",
            show_header=True,
            header_style="bold magenta",
            border_style="bright_black",
        )
        table.add_column("Agent", style="bold", min_width=10)
        table.add_column("Mood", min_width=12)
        table.add_column("Conf%", justify="right", min_width=6)
        table.add_column("Aggr%", justify="right", min_width=6)
        table.add_column("Top Suspect", min_width=20)
        table.add_column("Trust ↓", min_width=20)

        mood_colors = {
            "calm": "green",
            "confident": "cyan",
            "neutral": "white",
            "defensive": "yellow",
            "hostile": "red",
            "paranoid": "magenta",
            "aggressive": "bold red",
        }

        for agent in self.agents:
            state = agent.get_state_summary()
            mood_str = state["mood"]
            mood_color = mood_colors.get(mood_str, "white")

            # Top suspect
            suspects = state["top_suspects"]
            if suspects:
                top_name, top_score = suspects[0]
                suspect_cell = f"{top_name} [{int(top_score*100)}%]"
            else:
                suspect_cell = "—"

            # Distrusted agents
            distrusted = [n for n, v in state["trust"].items() if v < 0.45]
            distrust_cell = ", ".join(distrusted) if distrusted else "—"

            table.add_row(
                Text(agent.name, style=agent.color),
                Text(mood_str, style=mood_color),
                str(int(state["confidence"] * 100)),
                str(int(state["aggression"] * 100)),
                suspect_cell,
                distrust_cell,
            )

        console.print()
        console.print(table)

        # Contradiction summary
        contradictions_brief = self.contradiction_engine.get_all_contradictions_brief()
        console.print(
            Panel(
                contradictions_brief,
                title="[bold yellow]⚡ Contradictions Detected[/bold yellow]",
                border_style="yellow",
            )
        )
        console.print()

    # ──────────────────────────────────────────────────────────────────
    # Simulation Modes
    # ──────────────────────────────────────────────────────────────────

    def run_chat(self, max_turns=10, initial_moderator_msg=""):
        """
        Runs the group chat in a round-robin format.
        Prints a state snapshot after every full round.
        """
        console.print("\n[bold rgb(175,0,255)]--- The Chat Room is now OPEN ---[/bold rgb(175,0,255)]\n")

        if initial_moderator_msg:
            self.broadcast("Moderator", initial_moderator_msg)

        turn_count = 0
        agents_per_round = len(self.agents)

        while turn_count < max_turns:
            agent = self.agents[turn_count % agents_per_round]

            with console.status(f"[{agent.color}]{agent.name} is typing...[/{agent.color}]"):
                reply = agent.generate_reply(mode_context=self.mode_context)

            self.broadcast(agent.name, reply if reply else "*stays silent*")
            self._process_contradictions_and_state(agent.name, reply)

            turn_count += 1
            time.sleep(1.5)

            # At the end of every full round, update state and show snapshot
            if turn_count % agents_per_round == 0:
                self._end_of_round_update()
                self._print_state_snapshot()

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

                self.broadcast(agent.name, reply if reply else "*stays silent*")
                self._process_contradictions_and_state(agent.name, reply)
                time.sleep(1.0)

            # End-of-round update + snapshot after each question round
            self._end_of_round_update()
            self._print_state_snapshot()

        # Voting phase
        self.broadcast(
            "Moderator",
            "The questions have concluded. It is now time to vote. "
            "Each of you must state who you think the imposter is and provide your reasoning."
        )
        for agent in self.agents:
            with console.status(f"[{agent.color}]{agent.name} is making their final decision...[/{agent.color}]"):
                reply = agent.generate_reply(
                    mode_context=self.mode_context,
                    additional_system_instruction=(
                        "The game is strictly over. Conclude by explicitly stating who you think "
                        "the imposter is among the other agents and briefly explain your reasoning "
                        "(even if you are the imposter!). Let your suspicion levels guide your vote. "
                        "This is your final vote."
                    ),
                )
            self.broadcast(agent.name, reply if reply else "*stays silent*")
            time.sleep(1.5)

        console.print("\n[bold rgb(175,0,255)]--- Imposter Mode Ended ---[/bold rgb(175,0,255)]\n")

    # ──────────────────────────────────────────────────────────────────
    # Confession Room
    # ──────────────────────────────────────────────────────────────────

    def confession_room(self):
        """Allows humans to interview agents privately after the chat."""
        from rich.prompt import Prompt

        while True:
            console.print("\n[bold]=== CONFESSION ROOM ===[/bold]")
            console.print("Agents available for interview:")
            for i, agent in enumerate(self.agents):
                state = agent.get_state_summary()
                mood_str = f"[dim]({state['mood']}, conf: {int(state['confidence']*100)}%)[/dim]"
                console.print(
                    f"  {i + 1}. [{agent.color}]{agent.name}[/{agent.color}] {mood_str}"
                )
            console.print("  0. Exit Simulation")

            choice = Prompt.ask("Select an agent to interview", default="0")

            if choice == "0":
                break

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.agents):
                    self._interview_agent(self.agents[idx])
                else:
                    console.print("[red]Invalid selection.[/red]")
            except ValueError:
                console.print("[red]Invalid input.[/red]")

    def _interview_agent(self, agent):
        """1-on-1 interview loop with an agent in the Confession Room."""
        from rich.prompt import Prompt

        state = agent.get_state_summary()
        console.print(
            f"\n[bold]You are now privately interviewing [{agent.color}]{agent.name}[/{agent.color}].[/bold]"
        )
        console.print(
            f"  [dim]Internal state → Mood: {state['mood']} | "
            f"Confidence: {int(state['confidence']*100)}% | "
            f"Aggression: {int(state['aggression']*100)}%[/dim]"
        )
        if state["top_suspects"]:
            suspects_display = ", ".join(
                f"{n} ({int(s*100)}%)" for n, s in state["top_suspects"]
            )
            console.print(f"  [dim]Top suspects: {suspects_display}[/dim]")
        if state["imposter_strategy"]:
            console.print(f"  [bold red]Hidden Strategy: {state['imposter_strategy']}[/bold red]")
        console.print("  They retain all memory of the chat. Type 'exit' to leave.\n")

        system_instruction = (
            "You are in a private Confession Room with the Moderator. "
            "Be honest about your true thoughts, suspicions, and strategies during the chat. "
            "You may now reveal things you kept hidden — but stay in character emotionally."
        )

        while True:
            human_msg = Prompt.ask("[bold white]Moderator[/bold white]")
            if human_msg.lower() == "exit":
                break

            agent.add_to_memory("Moderator (Private)", human_msg)

            with console.status(f"[{agent.color}]{agent.name} is responding...[/{agent.color}]"):
                reply = agent.generate_reply(
                    mode_context=self.mode_context,
                    additional_system_instruction=system_instruction,
                )

            console.print(f"[{agent.color}][{agent.name}]:[/{agent.color}] {reply}")
            agent.add_to_memory(agent.name, reply)
