from pydantic import BaseModel, conint, constr, Field

AgentProposal = BaseModel(
    proposal_id: str,
    agent_id: str,
    content: str,
)

AgentVote = BaseModel(
    vote_id: str,
    agent_id: str,
    proposal_id: str,
    vote_value: conint(ge=0, le=10),
)

AgentDecision = BaseModel(
    decision_id: str,
    proposal_id: str,
    final_score: float,
)

AgentState = BaseModel(
    agent_id: str,
    status: constr(min_length=1),
)

TrustProfile = BaseModel(
    agent_id: str,
    trust_score: float = Field(..., ge=0.1, le=1.0),
    historical_accuracy: float = Field(..., ge=0, le=1.0),
)
