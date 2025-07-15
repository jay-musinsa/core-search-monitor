from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class MetricHistory(BaseModel):
    timestamp: str
    ndcg_at_10: float
    precision: float
    recall: float

class KeywordMetrics(BaseModel):
    ndcg: Dict[str, float]
    precision: float
    recall: float
    history: List[MetricHistory] = []

class MetricsResponse(BaseModel):
    status: str
    data: Dict[str, KeywordMetrics]
    timestamp: str 