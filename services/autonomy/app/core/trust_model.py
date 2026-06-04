from .agent_manager import AgentManager
from dataclasses import dataclass
from typing import Dict

@dataclass
class AgentTrust:
    trust_score: float
    historical_accuracy: float
    last_updated: str


class TrustModel:
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.agent_trust: Dict[str, AgentTrust] = {}

    def initialize_trust(self, agent_id: str):
        if agent_id not in self.agent_trust:
            self.agent_trust[agent_id] = AgentTrust(
                trust_score=0.1,
                historical_accuracy=0.0,
                last_updated="2026-04-12"
            )

    def update_trust(self, agent_id: str, delta: float):
        self.initialize_trust(agent_id)
        current = self.agent_trust[agent_id].trust_score
        new_score = max(0.1, min(1.0, current + delta))
        self.agent_trust[agent_id].trust_score = new_score
        # Apply decay logic here
        self.apply_decay(agent_id)

    def apply_decay(self, agent_id: str):
        self.agent_trust[agent_id].trust_score *= 0.95  # 5% decay per update
        # Ensure score does not drop below 0.1
        self.agent_trust[agent_id].trust_score = max(0.1, self.agent_trust[agent_id].trust_score)

    def update_accuracy(self, agent_id: str, accuracy_change: float):
        self.initialize_trust(agent_id)
        new_accuracy = max(0.0, min(1.0, self.agent_trust[agent_id].historical_accuracy + accuracy_change))
        self.agent_trust[agent_id].historical_accuracy = new_accuracy

    def get_trust(self, agent_id: str) -> float:
        self.initialize_trust(agent_id)
        return self.agent_trust[agent_id].trust_score

    def get_accuracy(self, agent_id: str) -> float:
        self.initialize_trust(agent_id)
        return self.agent_trust[agent_id].historical_accuracy
