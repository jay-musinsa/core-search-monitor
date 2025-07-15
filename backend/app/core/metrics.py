# 메트릭 집계 및 관리 로직
from typing import Dict, Any
from collections import defaultdict
from datetime import datetime

class MetricsManager:
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "ndcg": {"@10": 0.0},
            "precision": 0.0,
            "recall": 0.0,
            "screenshot": None,
            "ndcg_reason": "",
            "precision_reason": "",
            "recall_reason": "",
            "history": []
        })
        self.last_updated = None

    def update_metrics(self, keyword: str, ndcg10: float, precision: float, recall: float, screenshot_path: str, 
                      ndcg_reason: str = "", precision_reason: str = "", recall_reason: str = ""):
        self.metrics[keyword]["ndcg"]["@10"] = ndcg10
        self.metrics[keyword]["precision"] = precision
        self.metrics[keyword]["recall"] = recall
        self.metrics[keyword]["screenshot"] = screenshot_path
        self.metrics[keyword]["ndcg_reason"] = ndcg_reason
        self.metrics[keyword]["precision_reason"] = precision_reason
        self.metrics[keyword]["recall_reason"] = recall_reason
        self.metrics[keyword]["history"].append({
            "timestamp": datetime.now().isoformat(),
            "ndcg@10": ndcg10,
            "precision": precision,
            "recall": recall,
            "screenshot": screenshot_path,
            "ndcg_reason": ndcg_reason,
            "precision_reason": precision_reason,
            "recall_reason": recall_reason
        })
        # 실제 업데이트 시에만 갱신 시간 변경
        self.last_updated = datetime.now().isoformat()

    def get_metrics(self, keyword: str = None) -> Dict[str, Any]:
        if keyword:
            return self.metrics[keyword]
        return self.metrics

    def get_last_updated(self) -> str:
        return self.last_updated or "업데이트 없음"

metrics_manager = MetricsManager() 