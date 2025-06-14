from pydantic import BaseModel

class Evidence(BaseModel):
    code: str
    score: int
    data: dict

class TierResult(BaseModel):
    tier: str
    total_score: int
    evidence: list[Evidence]
