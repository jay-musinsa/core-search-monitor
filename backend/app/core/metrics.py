# 메트릭 집계 및 관리 로직
from typing import Dict, Any, Optional, List
from collections import defaultdict
from datetime import datetime
import json
import asyncio

from .musinsa_api_service import MusinsaAPIService
from .crawler import CrawlerMusinsa, Crawler29CM
from .gpt import GPTMetricEvaluator
from .evaluators import CompositeEvaluator, LLMEvaluator

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import config


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
        self.gpt_evaluator = GPTMetricEvaluator()  # 하위 호환성을 위해 유지
        
        # 새로운 다중 평가 시스템
        individual_image_llm_enabled = config.get_individual_image_llm_enabled()
        
        # 평가기 설정 로드
        evaluator_config = self._load_evaluator_config()
        
        self.composite_evaluator = CompositeEvaluator(
            enable_individual_image_llm=individual_image_llm_enabled,
            evaluator_config=evaluator_config
        )
        self.llm_evaluator = LLMEvaluator()  # 29CM용 LLM 평가기
        
        if individual_image_llm_enabled:
            print("[메트릭 매니저] Individual Image LLM 평가기가 활성화되었습니다")
        else:
            print("[메트릭 매니저] Individual Image LLM 평가기가 비활성화되었습니다 (기본값)")
        
        # 최근 결과 저장용 (임시)
        self.recent_results = {}
        
        # 기존 데이터 초기화
        self._clear_all_metrics()

    async def process_keyword(self, keyword: str, progress_callback=None) -> dict:
        """무신사/29CM 각각 스크린샷 캡처 및 다중 평가 시스템을 통한 종합 평가 후 결과 반환"""
        try:
            print(f"[메트릭 매니저] {keyword} 다중 평가 시스템 처리 시작")
            
            # 진행 상황 업데이트 함수
            async def update_progress(step: int, total_steps: int, message: str):
                if progress_callback:
                    await progress_callback(keyword, message, step, total_steps)
                print(f"[진행 상황] {keyword}: {message} ({step}/{total_steps})")

            await update_progress(1, 8, "API 데이터 수집 시작")
            
            # 1. 무신사 API로 상품 데이터 수집
            api_items = self.musinsa_api_service.fetch_100_items(keyword)
            total_products = len(api_items)
            print(f"[메트릭 매니저] {keyword} API 데이터 수집 완료: {total_products}개 상품")
            
            await update_progress(2, 8, f"API 데이터 수집 완료 ({total_products}개 상품)")
            await update_progress(3, 8, "스크린샷 캡처 시작")

            # 2. 무신사/29CM 스크린샷 캡처 (비동기)
            loop = asyncio.get_event_loop()
            screenshot_tasks = [
                loop.run_in_executor(None, self.musinsa_crawler.capture_screenshot, keyword),
                loop.run_in_executor(None, self.crawler_29cm.capture_screenshot, keyword)
            ]
            screenshots = await asyncio.gather(*screenshot_tasks, return_exceptions=True)
            musinsa_screenshot = screenshots[0] if not isinstance(screenshots[0], Exception) else None
            cm29_screenshot = screenshots[1] if not isinstance(screenshots[1], Exception) else None
            
            print(f"[메트릭 매니저] {keyword} 스크린샷 캡처 완료: 무신사={bool(musinsa_screenshot)}, 29CM={bool(cm29_screenshot)}")
            
            await update_progress(4, 8, "스크린샷 캡처 완료")
            await update_progress(5, 8, "다중 평가 시스템 시작")

            # 3. 다중 평가 시스템 실행
            print(f"[메트릭 매니저] {keyword} 다중 평가 시스템 시작")
            
            # 무신사: 종합 평가기 사용 (API 데이터 + 스크린샷)
            musinsa_result = None
            if musinsa_screenshot or api_items:
                try:
                    await update_progress(6, 8, "무신사 종합 평가 진행중")
                    musinsa_result = await self.composite_evaluator.evaluate(
                        keyword=keyword, 
                        products=api_items, 
                        screenshot_path=musinsa_screenshot
                    )
                    print(f"[메트릭 매니저] 무신사 종합 평가 완료: NDCG={musinsa_result.ndcg_10:.3f}, 신뢰도={musinsa_result.confidence:.3f}")
                    await update_progress(6, 8, f"무신사 평가 완료 (NDCG: {musinsa_result.ndcg_10:.3f})")
                except Exception as e:
                    print(f"[메트릭 매니저] 무신사 종합 평가 실패: {e}")
                    await update_progress(6, 8, "무신사 평가 실패")
            else:
                await update_progress(6, 8, "무신사 평가 건너뜀 (데이터 없음)")
            
            # 29CM: LLM 평가기만 사용 (스크린샷만)
            cm29_result = None
            if cm29_screenshot:
                try:
                    await update_progress(7, 8, "29CM LLM 평가 진행중")
                    cm29_result = await self.llm_evaluator.evaluate(
                        keyword=keyword, 
                        products=[], 
                        screenshot_path=cm29_screenshot
                    )
                    print(f"[메트릭 매니저] 29CM LLM 평가 완료: NDCG={cm29_result.ndcg_10:.3f}, 신뢰도={cm29_result.confidence:.3f}")
                    await update_progress(7, 8, f"29CM 평가 완료 (NDCG: {cm29_result.ndcg_10:.3f})")
                except Exception as e:
                    print(f"[메트릭 매니저] 29CM LLM 평가 실패: {e}")
                    await update_progress(7, 8, "29CM 평가 실패")
            else:
                await update_progress(7, 8, "29CM 평가 건너뜀 (스크린샷 없음)")

            await update_progress(8, 8, "결과 처리 중")

            # 4. 결과 변환 (기존 형식과 호환)
            musinsa_metrics = self._convert_evaluation_result(musinsa_result, musinsa_screenshot)
            cm29_metrics = self._convert_evaluation_result(cm29_result, cm29_screenshot)

            # 5. 요약 로그 출력
            musinsa_score = musinsa_metrics.get('ndcg@10', 'X')
            cm29_score = cm29_metrics.get('ndcg@10', 'X')
            musinsa_confidence = musinsa_result.confidence if musinsa_result else 0
            cm29_confidence = cm29_result.confidence if cm29_result else 0
            
            print(f"[SUMMARY] {keyword} - MUSINSA: {musinsa_score} (신뢰도: {musinsa_confidence:.2f}), 29CM: {cm29_score} (신뢰도: {cm29_confidence:.2f}) (상품수: {total_products})")

            # 6. 결과 반환
            result = {
                "musinsa": {
                    **musinsa_metrics,
                    "screenshot": musinsa_screenshot,
                    "evaluation_method": musinsa_result.method if musinsa_result else "failed",
                    "confidence": musinsa_confidence,
                    "evaluation_details": musinsa_result.details if musinsa_result else {}
                },
                "29cm": {
                    **cm29_metrics,
                    "screenshot": cm29_screenshot,
                    "evaluation_method": cm29_result.method if cm29_result else "failed",
                    "confidence": cm29_confidence,
                    "evaluation_details": cm29_result.details if cm29_result else {}
                }
            }
            
            # 최근 결과 저장 (JSON 직렬화 안전하게)
            self.recent_results[keyword] = self._sanitize_for_json(result)
            
            # quality_assessment_daily 테이블에 저장
            await self._save_to_quality_assessment_daily(keyword, result)
            
            # 마지막 업데이트 시간 갱신
            self.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 평가 완료 알림 전송 (검색 결과 자동 업데이트용)
            await self._broadcast_evaluation_complete(keyword, result)
            
            return result
            
        except Exception as e:
            print(f"[메트릭 매니저] {keyword} 처리 실패: {e}")
            return {"error": str(e)}
    
    def _sanitize_for_json(self, data):
        """데이터를 JSON 직렬화 가능하도록 변환"""
        import numpy as np
        
        if isinstance(data, dict):
            return {key: self._sanitize_for_json(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, np.floating):
            return float(data)
        elif isinstance(data, np.integer):
            return int(data)
        elif hasattr(data, 'item'):  # numpy 타입
            return data.item()
        elif hasattr(data, 'tolist'):  # numpy 배열
            return data.tolist()
        else:
            return data
    
    def _convert_evaluation_result(self, result, screenshot_path: str = None) -> dict:
        """EvaluationResult를 기존 메트릭 형식으로 변환"""
        if not result:
            return {
                "ndcg@10": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "ndcg_reason": "평가 실패",
                "precision_reason": "평가 실패",
                "recall_reason": "평가 실패",
                "precision_issues": [],
                "evaluation_method": "failed",
                "confidence": 0.0,
                "evaluation_details": {}
            }
        
        # EvaluationResult 객체의 모든 속성을 JSON 직렬화 가능한 형태로 변환
        def safe_float(value):
            """numpy 타입을 포함한 모든 숫자 타입을 안전하게 float로 변환"""
            try:
                if hasattr(value, 'item'):  # numpy 타입인 경우
                    return float(value.item())
                return float(value)
            except (ValueError, TypeError, AttributeError):
                return 0.0
        
        def safe_dict(value):
            """딕셔너리를 안전하게 변환"""
            if not value:
                return {}
            try:
                result_dict = {}
                for k, v in value.items():
                    if hasattr(v, 'item'):  # numpy 타입인 경우
                        result_dict[str(k)] = v.item() if hasattr(v.item(), '__dict__') == False else str(v.item())
                    elif isinstance(v, (int, float, str, bool, type(None))):
                        result_dict[str(k)] = v
                    else:
                        result_dict[str(k)] = str(v)
                return result_dict
            except Exception:
                return {}
        
        return {
            "ndcg@10": safe_float(result.ndcg_10),
            "precision": safe_float(result.precision),
            "recall": safe_float(result.recall),
            "ndcg_reason": str(result.details.get("reasoning", f"{result.method} 평가 결과")),
            "precision_reason": str(result.details.get("reasoning", f"{result.method} 평가 결과")),
            "recall_reason": str(result.details.get("reasoning", f"{result.method} 평가 결과")),
            "precision_issues": [
                {
                    "goods_no": str(issue.get("goods_no", "")),
                    "goods_name": str(issue.get("goods_name", "")),
                    "image_url": str(issue.get("image_url", "N/A")),
                    "reason": str(issue.get("reason", ""))
                } for issue in (result.precision_issues or [])
            ],
            "evaluation_method": str(result.method),
            "confidence": safe_float(result.confidence),
            "evaluation_details": safe_dict(result.details)
        }

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
            return self.recent_results.get(keyword, {})
        return self.recent_results

    def get_last_updated(self) -> str:
        """마지막 업데이트 시간 조회"""
        if self.last_updated:
            return str(self.last_updated)
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    def _load_evaluator_config(self):
        """평가기 설정 로드"""
        try:
            import json
            config_file = "evaluator_config.json"
            if os.path.exists(config_file):
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # configs 키가 있으면 그 안의 데이터 반환, 없으면 전체 반환
                    return data.get('configs', data)
        except Exception as e:
            print(f"[메트릭 매니저] 평가기 설정 로드 실패: {e}")
        return {}

    async def _save_to_quality_assessment_daily(self, keyword: str, result: dict):
        """검색 결과를 quality_assessment_daily 테이블에 저장"""
        try:
            import clickhouse_connect
            import json
            
            # ClickHouse 연결
            try:
                clickhouse_client = clickhouse_connect.get_client(
                    host='localhost', port=8123, username='default', password=''
                )
            except Exception as e:
                print(f"[메트릭 매니저] ClickHouse 연결 실패: {e}")
                return
            
            # 키워드 ID 조회/생성
            keyword_id = await self._get_or_create_keyword_id(keyword, clickhouse_client)
            
            current_time = datetime.now()
            assessment_date = current_time.date()
            
            # 무신사와 29CM 결과를 각각 저장
            for platform_key, platform_data in result.items():
                if platform_key in ['musinsa', '29cm'] and platform_data:
                    try:
                        # 스크린샷 파일 크기 계산
                        screenshot_size = 0
                        screenshot_quality = 'none'
                        screenshot_path = platform_data.get('screenshot', '')
                        
                        if screenshot_path:
                            try:
                                import os
                                if screenshot_path.startswith('/screenshot/'):
                                    abs_path = os.path.join(os.path.dirname(__file__), '..', screenshot_path.lstrip('/'))
                                    if os.path.exists(abs_path):
                                        screenshot_size = os.path.getsize(abs_path)
                                        screenshot_quality = 'high'
                            except Exception:
                                pass
                        
                        # 삽입 데이터 준비
                        assessment_data = [(
                            hash(f"{keyword}_{platform_key}_{current_time.isoformat()}") % (2**63 - 1),  # id (양수로 변환)
                            keyword_id,
                            assessment_date,
                            platform_key,
                            
                            # API 응답 메트릭스 (기본값)
                            0.5,  # api_response_time
                            100 if platform_key == 'musinsa' else 0,  # api_total_results (무신사만 API 데이터 있음)
                            200,  # api_status_code
                            json.dumps({'processed_by': 'metrics_manager'}, ensure_ascii=False),  # api_response_data
                            
                            # 다중 평가 시스템 결과
                            float(platform_data.get('ndcg@10', 0.0)),  # ndcg_score
                            float(platform_data.get('precision', 0.0)),  # precision_score
                            float(platform_data.get('recall', 0.0)),  # recall_score
                            float(platform_data.get('confidence', 0.0)),  # confidence_score
                            str(platform_data.get('evaluation_method', 'unknown')),  # evaluation_method
                            json.dumps(platform_data.get('evaluation_details', {}), ensure_ascii=False),  # evaluation_details
                            
                            # 평가 이유 및 문제점
                            str(platform_data.get('ndcg_reason', '')),  # ndcg_reason
                            str(platform_data.get('precision_reason', '')),  # precision_reason
                            str(platform_data.get('recall_reason', '')),  # recall_reason
                            json.dumps(platform_data.get('precision_issues', []), ensure_ascii=False),  # precision_issues
                            
                            # 기존 GPT 필드들 (하위 호환성)
                            float(platform_data.get('ndcg@10', 0.0)),  # gpt_ndcg_score
                            float(platform_data.get('precision', 0.0)),  # gpt_precision
                            float(platform_data.get('recall', 0.0)),  # gpt_recall
                            float(platform_data.get('confidence', 0.0)),  # gpt_relevance_score
                            f"{platform_data.get('ndcg_reason', '')} | {platform_data.get('precision_reason', '')}",  # gpt_evaluation_text
                            float(platform_data.get('confidence', 0.0)),  # gpt_confidence_score
                            
                            # 스크린샷 정보
                            screenshot_path,
                            screenshot_size,
                            screenshot_quality,
                            
                            # 처리 메타데이터
                            3.0,  # processing_time (평균값)
                            '',   # batch_id
                            0,    # retry_count
                            '',   # error_message
                            current_time
                        )]
                        
                        # 데이터 삽입
                        clickhouse_client.insert(
                            'quality_assessment_daily',
                            assessment_data,
                            column_names=[
                                'id', 'keyword_id', 'assessment_date', 'platform',
                                'api_response_time', 'api_total_results', 'api_status_code', 'api_response_data',
                                'ndcg_score', 'precision_score', 'recall_score', 'confidence_score',
                                'evaluation_method', 'evaluation_details',
                                'ndcg_reason', 'precision_reason', 'recall_reason', 'precision_issues',
                                'gpt_ndcg_score', 'gpt_precision', 'gpt_recall', 'gpt_relevance_score',
                                'gpt_evaluation_text', 'gpt_confidence_score',
                                'screenshot_path', 'screenshot_size', 'screenshot_quality',
                                'processing_time', 'batch_id', 'retry_count', 'error_message', 'created_at'
                            ]
                        )
                        
                        print(f"[메트릭 매니저] {keyword} {platform_key} 데이터 저장 완료")
                        
                    except Exception as e:
                        print(f"[메트릭 매니저] {keyword} {platform_key} 저장 실패: {e}")
                        continue
            
        except Exception as e:
            print(f"[메트릭 매니저] quality_assessment_daily 저장 실패: {e}")
    
    async def _get_or_create_keyword_id(self, keyword: str, clickhouse_client) -> int:
        """키워드 ID 조회 또는 생성"""
        try:
            # 먼저 기존 키워드 조회
            result = clickhouse_client.query(
                "SELECT id FROM keyword_master WHERE keyword = %(keyword)s",
                {'keyword': keyword}
            )
            
            if result.result_rows:
                return result.result_rows[0][0]
            
            # 새 키워드 생성
            new_id = hash(keyword) % (2**31 - 1)  # 양수로 변환
            if new_id < 0:
                new_id = abs(new_id)
            
            clickhouse_client.insert(
                'keyword_master',
                [(new_id, keyword, 'auto', 1, 1, datetime.now(), datetime.now())],
                column_names=['id', 'keyword', 'category', 'priority', 'is_active', 'created_at', 'updated_at']
            )
            
            print(f"[메트릭 매니저] 새 키워드 생성: {keyword} (ID: {new_id})")
            return new_id
            
        except Exception as e:
            print(f"[메트릭 매니저] 키워드 ID 조회/생성 실패: {e}")
            return hash(keyword) % (2**31 - 1)  # fallback 

    async def _broadcast_evaluation_complete(self, keyword: str, result: dict):
        """평가 완료 알림을 WebSocket으로 전송 (검색 결과 자동 업데이트용)"""
        try:
            from app.websocket_manager import websocket_manager
            
            # 평가 완료 메시지 구성
            complete_message = {
                "type": "evaluation_complete",
                "keyword": keyword,
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "musinsa": {
                        "ndcg_score": result.get("musinsa", {}).get("ndcg@10", 0),
                        "precision": result.get("musinsa", {}).get("precision", 0),
                        "recall": result.get("musinsa", {}).get("recall", 0),
                        "evaluation_method": result.get("musinsa", {}).get("evaluation_method", "unknown"),
                        "confidence": result.get("musinsa", {}).get("confidence", 0)
                    },
                    "29cm": {
                        "ndcg_score": result.get("29cm", {}).get("ndcg@10", 0),
                        "precision": result.get("29cm", {}).get("precision", 0),
                        "recall": result.get("29cm", {}).get("recall", 0),
                        "evaluation_method": result.get("29cm", {}).get("evaluation_method", "unknown"),
                        "confidence": result.get("29cm", {}).get("confidence", 0)
                    }
                }
            }
            
            print(f"[평가 완료 알림] {keyword}: 검색 결과 업데이트 알림 전송")
            await websocket_manager.broadcast_message(complete_message)
            
        except Exception as e:
            print(f"[평가 완료 알림] 전송 실패: {e}")
            # 알림 전송 실패해도 평가 자체는 계속 진행

metrics_manager = MetricsManager() 