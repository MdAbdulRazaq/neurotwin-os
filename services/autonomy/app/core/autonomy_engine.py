from .agent_manager import AgentManager
from .consensus import ConsensusEngine
from .trust_model import TrustModel
import json
import redis
import logging


class AutonomyEngine:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.agent_manager = AgentManager()
        self.consensus = ConsensusEngine(self.agent_manager, TrustModel(self.agent_manager))
        self.redis_client = redis.Redis(host=redis_host, port=redis_port)
        self.logger = logging.getLogger(__name__)

    def _safe_publish(self, channel, message, trace_id, error_handler=None):
        try:
            self.redis_client.publish(
                channel=channel,
                message=json.dumps({"trace_id": trace_id, "data": message})
            )
            self.logger.info(f"Published to {channel} for trace {trace_id}")
            return True
        except redis.exceptions.ConnectionError as e:
            self.logger.error(f"Redis connection error for trace {trace_id}: {str(e)}")
            if error_handler:
                error_handler(e)
            return False

    def run_pipeline(self, trace_id: str):
        self.logger.info(f"Processing decision for trace {trace_id}")
        state = self.receive_state(trace_id)
        proposals = self.consensus.collect_proposals(state)
        self._safe_publish('neurotwin:agent_proposals', [p.dict() for p in proposals], trace_id)
        scores = self.consensus.calculate_scores(proposals)
        self._safe_publish('neurotwin:agent_votes', scores, trace_id)
        best_proposal = self.consensus.select_best_action(scores)
        self._safe_publish('neurotwin:agent_decisions', best_proposal.dict(), trace_id)
        return best_proposal

    def receive_state(self, trace_id: str) -> dict:
        try:
            state_data = self.redis_client.get(f"system_state_{trace_id}")
            return json.loads(state_data) if state_data else {}
        except redis.exceptions.RedisError as e:
            self.logger.error(f"Redis error fetching state for trace {trace_id}: {str(e)}")
            return {}
