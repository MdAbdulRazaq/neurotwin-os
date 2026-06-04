from .agent_manager import AgentManager
from .trust_model import TrustProfile


class ConsensusEngine:
    def __init__(self, agent_manager, trust_model):
        self.agent_manager = agent_manager
        self.trust_model = trust_model

    def collect_proposals(self, state):
        proposals = []
        for agent_id in self.agent_manager.registered_agents:
            proposals.append(self.agent_manager.propose(state, agent_id))
        return proposals

    def calculate_scores(self, proposals):
        scores = []
        for proposal in proposals:
            agent_id = proposal.agent_id
            confidence = proposal.confidence
            weight = self.trust_model.get_weight(agent_id)
            trust_score = self.trust_model.get_trust(agent_id)
            historical_accuracy = self.trust_model.get_accuracy(agent_id)

            score = (confidence * weight) + (trust_score * historical_accuracy)
            scores.append((proposal, score))
        return scores

    def select_best_action(self, scored_proposals):
        # Sort proposals by score in descending order
        sorted_proposals = sorted(scored_proposals, key=lambda x: x[1], reverse=True)
        # Select the top proposal
        best_proposal = sorted_proposals[0]
        return best_proposal[0]
