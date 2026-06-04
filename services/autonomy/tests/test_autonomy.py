import pytest
from unittest.mock import MagicMock, patch
from ..core.agent_manager import AgentManager
from ..core.consensus import ConsensusEngine
from ..core.trust_model import TrustModel


class TestAutonomyEngine:
    def setup_method(self):
        self.agent_manager = AgentManager()
        self.trust_model = TrustModel(self.agent_manager)
        self.consensus = ConsensusEngine(self.agent_manager, self.trust_model)
        self.mock_redis = MagicMock()

    @pytest.mark.asyncio
    async def test_proposal_collection(self):
        # Mock agent proposals
        with patch.object(self.agent_manager, 'propose', return_value=MagicMock()):
            proposals = self.consensus.collect_proposals({})
            assert len(proposals) > 0

    def test_consensus_scoring(self):
        # Generate mock proposals
        proposals = [MagicMock() for _ in range(5)]
        scores = self.consensus.calculate_scores(proposals)
        assert len(scores) == len(proposals)

    def test_trust_update(self):
        # Test trust score update with positive delta
        self.trust_model.update_trust('test_agent', 0.2)
        assert self.trust_model.get_trust('test_agent') == 0.3
        # Test upper bound
        self.trust_model.update_trust('test_agent', 1.0)
        assert self.trust_model.get_trust('test_agent') == 1.0
        # Test lower bound
        self.trust_model.update_trust('test_agent', -1.0)
        assert self.trust_model.get_trust('test_agent') == 0.1

    def test_failure_handling(self):
        # Test Redis connection failure
        with patch.object(self.mock_redis, 'get', side_effect=ConnectionError):
            assert self.consensus.receive_state('trace_123') == {}
