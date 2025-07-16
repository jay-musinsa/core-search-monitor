# 메트릭 집계 및 관리 로직
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime
import json
import asyncio

from .musinsa_api_service import MusinsaAPIService
from .crawler import CrawlerMusinsa, Crawler29CM
from .gpt import GPTMetricEvaluator


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
            "history": [],
            "last_updated": None,
            "status": "pending",  # pending, processing, completed, failed
            "api_data": None,  # API에서 가져온 상품 데이터
            "total_products": 0,  # 총 상품 수
            "platform": "MUSINSA"  # 플랫폼 정보
        })
        self.last_updated = None
        self.musinsa_api_service = MusinsaAPIService()
        self.musinsa_crawler = CrawlerMusinsa()
        self.crawler_29cm = Crawler29CM()
        self.gpt_evaluator = GPTMetricEvaluator()
        # 기존 데이터 초기화
        self._clear_all_metrics()

    async def process_keyword(self, keyword: str) -> dict:
        """무신사/29CM 각각 스크린샷 캡처 및 GPT 평가 후 결과 반환 (메트릭 저장 없음)"""
        try:
            print(f"[메트릭 매니저] {keyword} 처리 시작")

            # 1. 무신사 API로 상품 데이터 수집 (요약용)
            api_items = self.musinsa_api_service.fetch_100_items(keyword)
            total_products = len(api_items)

            # 2. 무신사/29CM 스크린샷 캡처 (비동기)
            loop = asyncio.get_event_loop()
            screenshot_tasks = [
                loop.run_in_executor(None, self.musinsa_crawler.capture_screenshot, keyword),
                loop.run_in_executor(None, self.crawler_29cm.capture_screenshot, keyword)
            ]
            screenshots = await asyncio.gather(*screenshot_tasks, return_exceptions=True)
            musinsa_screenshot = screenshots[0] if not isinstance(screenshots[0], Exception) else None
            cm29_screenshot = screenshots[1] if not isinstance(screenshots[1], Exception) else None

            # 3. GPT 평가 (무신사 스크린샷 + API 데이터 사용)
            print(f"[메트릭 매니저] {keyword} GPT 평가 시작")
            musinsa_metrics = {}
            cm29_metrics = {}
            
            if musinsa_screenshot:
                musinsa_metrics = self.gpt_evaluator.evaluate_with_api_data(
                    musinsa_screenshot, keyword, api_items
                )
            else:
                print(f"[메트릭 매니저] {keyword} 무신사 스크린샷이 없어 GPT 평가를 건너뜁니다")
                musinsa_metrics = {
                    "ndcg@10": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "ndcg_reason": "스크린샷 캡처 실패",
                    "precision_reason": "스크린샷 캡처 실패",
                    "recall_reason": "스크린샷 캡처 실패",
                    "precision_issues": []
                }
            
            if cm29_screenshot:
                cm29_metrics = self.gpt_evaluator.evaluate(cm29_screenshot, keyword)
                # 29CM은 API 데이터가 없으므로 기본 구조만 추가
                if "precision_issues" not in cm29_metrics:
                    cm29_metrics["precision_issues"] = []
            else:
                print(f"[메트릭 매니저] {keyword} 29CM 스크린샷이 없어 GPT 평가를 건너뜁니다")
                cm29_metrics = {
                    "ndcg@10": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "ndcg_reason": "스크린샷 캡처 실패",
                    "precision_reason": "스크린샷 캡처 실패",
                    "recall_reason": "스크린샷 캡처 실패",
                    "precision_issues": []
                }

            # 4. 요약 로그만 출력
            print(f"[SUMMARY] {keyword} - MUSINSA: {musinsa_metrics['ndcg@10'] if musinsa_metrics else 'X'}, 29CM: {cm29_metrics['ndcg@10'] if cm29_metrics else 'X'} (상품수: {total_products})")

            # 5. 결과 반환
            return {
                "musinsa": {
                    **(musinsa_metrics or {}),
                    "screenshot": musinsa_screenshot
                },
                "29cm": {
                    **(cm29_metrics or {}),
                    "screenshot": cm29_screenshot
                }
            }
        except Exception as e:
            print(f"[메트릭 매니저] {keyword} 처리 실패: {e}")
            return {"error": str(e)}

    def update_metrics_with_api_data(self, keyword: str, ndcg10: float, precision: float, recall: float, 
                                   screenshot_path: str, api_data: List[Dict], total_products: int,
                                   ndcg_reason: str = "", precision_reason: str = "", recall_reason: str = ""):
        """API 데이터와 함께 메트릭 업데이트"""
        current_time = datetime.now().isoformat()
        
        # 메트릭 업데이트
        self.metrics[keyword]["ndcg"]["@10"] = ndcg10
        self.metrics[keyword]["precision"] = precision
        self.metrics[keyword]["recall"] = recall
        self.metrics[keyword]["screenshot"] = screenshot_path
        self.metrics[keyword]["ndcg_reason"] = ndcg_reason
        self.metrics[keyword]["precision_reason"] = precision_reason
        self.metrics[keyword]["recall_reason"] = recall_reason
        self.metrics[keyword]["last_updated"] = current_time
        self.metrics[keyword]["status"] = "completed"
        self.metrics[keyword]["api_data"] = api_data
        self.metrics[keyword]["total_products"] = total_products
        self.metrics[keyword]["platform"] = "MUSINSA"
        
        # 히스토리에 추가 (최대 10개 유지)
        history_entry = {
            "timestamp": current_time,
            "ndcg@10": ndcg10,
            "precision": precision,
            "recall": recall,
            "screenshot": screenshot_path,
            "ndcg_reason": ndcg_reason,
            "precision_reason": precision_reason,
            "recall_reason": recall_reason,
            "total_products": total_products,
            "platform": "MUSINSA"
        }
        
        self.metrics[keyword]["history"].append(history_entry)
        
        # 히스토리 크기 제한 (최근 10개만 유지)
        if len(self.metrics[keyword]["history"]) > 10:
            self.metrics[keyword]["history"] = self.metrics[keyword]["history"][-10:]
        
        # 전체 마지막 업데이트 시간 갱신
        self.last_updated = current_time
        
        # 파일에 저장
        self._save_metrics_to_file()
        
        print(f"[메트릭 매니저] {keyword} 업데이트 완료: NDCG={ndcg10:.3f}, Precision={precision:.3f}, Recall={recall:.3f}")
        print(f"[메트릭 매니저] {keyword} API 데이터: {total_products}개 상품")

    def update_metrics(self, keyword: str, ndcg10: float, precision: float, recall: float, screenshot_path: str, 
                      ndcg_reason: str = "", precision_reason: str = "", recall_reason: str = ""):
        """기존 메트릭 업데이트 (하위 호환성)"""
        self.update_metrics_with_api_data(
            keyword=keyword,
            ndcg10=ndcg10,
            precision=precision,
            recall=recall,
            screenshot_path=screenshot_path,
            api_data=self.metrics[keyword].get("api_data", []),
            total_products=self.metrics[keyword].get("total_products", 0),
            ndcg_reason=ndcg_reason,
            precision_reason=precision_reason,
            recall_reason=recall_reason
        )

    def set_processing_status(self, keyword: str, status: str = "processing"):
        """키워드 처리 상태 설정"""
        self.metrics[keyword]["status"] = status
        if status == "processing":
            self.metrics[keyword]["last_updated"] = datetime.now().isoformat()
        print(f"[메트릭 매니저] {keyword} 상태 변경: {status}")

    def get_metrics(self, keyword: str = None) -> Dict[str, Any]:
        """메트릭 조회"""
        if keyword:
            return dict(self.metrics[keyword])
        return {k: dict(v) for k, v in self.metrics.items()}

    def get_last_updated(self) -> str:
        """마지막 업데이트 시간 조회"""
        return self.last_updated or "업데이트 없음"

    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약 정보 조회"""
        if not self.metrics:
            return {"total_keywords": 0, "completed": 0, "processing": 0, "pending": 0}
        
        total = len(self.metrics)
        completed = sum(1 for m in self.metrics.values() if m["status"] == "completed")
        processing = sum(1 for m in self.metrics.values() if m["status"] == "processing")
        pending = sum(1 for m in self.metrics.values() if m["status"] == "pending")
        
        return {
            "total_keywords": total,
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "last_updated": self.last_updated
        }

    def clear_metrics(self, keyword: str = None):
        """메트릭 초기화"""
        if keyword:
            if keyword in self.metrics:
                del self.metrics[keyword]
                print(f"[메트릭 매니저] {keyword} 메트릭 삭제")
        else:
            self.metrics.clear()
            self.last_updated = None
            print("[메트릭 매니저] 모든 메트릭 삭제")
        
        self._save_metrics_to_file()

    def _save_metrics_to_file(self):
        """메트릭을 파일에 저장"""
        try:
            # defaultdict를 일반 dict로 변환
            metrics_dict = {k: dict(v) for k, v in self.metrics.items()}
            
            data = {
                "metrics": metrics_dict,
                "last_updated": self.last_updated,
                "saved_at": datetime.now().isoformat()
            }
            
            with open("metrics_backup.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[메트릭 매니저] 파일 저장 실패: {e}")

    def _load_metrics_from_file(self):
        """파일에서 메트릭 로드"""
        try:
            with open("metrics_backup.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if "metrics" in data:
                for keyword, metric_data in data["metrics"].items():
                    self.metrics[keyword].update(metric_data)
                
            if "last_updated" in data:
                self.last_updated = data["last_updated"]
                
            print(f"[메트릭 매니저] 파일에서 {len(data.get('metrics', {}))}개 메트릭 로드 완료")
            
        except FileNotFoundError:
            print("[메트릭 매니저] 백업 파일이 없습니다. 새로 시작합니다.")
        except Exception as e:
            print(f"[메트릭 매니저] 파일 로드 실패: {e}")

    def _clear_all_metrics(self):
        """모든 메트릭 초기화"""
        self.metrics.clear()
        self.last_updated = None
        print("[메트릭 매니저] 모든 메트릭 초기화 완료")
        self._save_metrics_to_file()

metrics_manager = MetricsManager() 