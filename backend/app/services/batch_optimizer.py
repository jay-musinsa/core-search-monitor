"""
배치 처리 최적화 서비스
15,000개 키워드 처리를 위한 고성능 배치 처리 시스템
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import json
import uuid
from dataclasses import dataclass
from enum import Enum

from app.core.database import get_database_client
from app.tasks.keyword_assessment import assess_single_keyword
from app.core.redis_client import get_redis_client


logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """배치 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class BatchConfig:
    """배치 설정 클래스"""
    batch_size: int = 20
    max_workers: int = 5
    retry_count: int = 3
    retry_delay: int = 60
    timeout: int = 300
    memory_limit: int = 1024 * 1024 * 1024  # 1GB
    priority_threshold: int = 2


@dataclass
class BatchMetrics:
    """배치 메트릭 클래스"""
    total_keywords: int = 0
    processed_keywords: int = 0
    successful_keywords: int = 0
    failed_keywords: int = 0
    retry_keywords: int = 0
    avg_processing_time: float = 0.0
    total_processing_time: float = 0.0
    gpt_api_calls: int = 0
    gpt_api_cost: float = 0.0
    memory_usage: float = 0.0
    throughput: float = 0.0


class BatchOptimizer:
    """배치 처리 최적화 클래스"""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self.db_client = get_database_client()
        self.redis_client = get_redis_client()
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        self.metrics = BatchMetrics()
        self.active_batches: Dict[str, Dict[str, Any]] = {}
        
    async def optimize_batch_processing(
        self,
        target_date: date,
        platforms: List[str],
        keyword_count: int = 15000
    ) -> Dict[str, Any]:
        """
        대용량 키워드 배치 처리 최적화
        
        Args:
            target_date: 처리 대상 날짜
            platforms: 처리할 플랫폼 리스트
            keyword_count: 처리할 키워드 수
            
        Returns:
            Dict[str, Any]: 처리 결과
        """
        batch_id = f"batch_{target_date.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        try:
            # 1. 배치 작업 초기화
            await self._initialize_batch_job(batch_id, target_date, platforms, keyword_count)
            
            # 2. 키워드 분할 및 우선순위 정렬
            keyword_batches = await self._create_optimized_batches(keyword_count, platforms)
            
            # 3. 병렬 처리 실행
            results = await self._execute_parallel_processing(batch_id, keyword_batches)
            
            # 4. 결과 집계 및 메트릭 수집
            final_metrics = await self._collect_final_metrics(batch_id, results)
            
            # 5. 배치 상태 업데이트
            await self._update_batch_status(batch_id, BatchStatus.COMPLETED, final_metrics)
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "batch_id": batch_id,
                "processing_time": processing_time,
                "metrics": final_metrics,
                "throughput": keyword_count / processing_time if processing_time > 0 else 0,
                "optimization_applied": True
            }
            
        except Exception as e:
            logger.error(f"배치 처리 최적화 실패: {e}")
            await self._update_batch_status(batch_id, BatchStatus.FAILED, {"error": str(e)})
            
            return {
                "success": False,
                "batch_id": batch_id,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    async def _initialize_batch_job(
        self,
        batch_id: str,
        target_date: date,
        platforms: List[str],
        keyword_count: int
    ) -> None:
        """배치 작업 초기화"""
        try:
            # 데이터베이스에 배치 작업 생성
            batch_data = {
                "batch_id": batch_id,
                "job_type": "optimized_daily_assessment",
                "status": BatchStatus.PENDING.value,
                "total_keywords": keyword_count,
                "processed_keywords": 0,
                "failed_keywords": 0,
                "scheduled_at": datetime.now(),
                "started_at": None,
                "completed_at": None,
                "error_message": "",
                "log_data": json.dumps({
                    "target_date": target_date.isoformat(),
                    "platforms": platforms,
                    "optimization_config": {
                        "batch_size": self.config.batch_size,
                        "max_workers": self.config.max_workers,
                        "retry_count": self.config.retry_count
                    }
                }),
                "avg_processing_time": 0.0,
                "gpt_api_calls": 0,
                "gpt_api_cost": 0.0
            }
            
            self.db_client.insert("batch_jobs", [batch_data])
            
            # Redis에 배치 상태 캐싱
            await self.redis_client.setex(
                f"batch_status:{batch_id}",
                3600,  # 1시간 TTL
                json.dumps(batch_data)
            )
            
            self.active_batches[batch_id] = {
                "start_time": time.time(),
                "status": BatchStatus.PENDING,
                "metrics": BatchMetrics()
            }
            
            logger.info(f"배치 작업 초기화 완료: {batch_id}")
            
        except Exception as e:
            logger.error(f"배치 작업 초기화 실패: {e}")
            raise
    
    async def _create_optimized_batches(
        self,
        keyword_count: int,
        platforms: List[str]
    ) -> List[Dict[str, Any]]:
        """최적화된 배치 생성"""
        try:
            # 활성 키워드 조회 (우선순위 기준 정렬)
            query = """
            SELECT id, keyword, category, priority
            FROM keyword_master 
            WHERE is_active = 1 
            ORDER BY priority ASC, id ASC
            LIMIT {}
            """.format(keyword_count)
            
            result = self.db_client.query(query)
            keywords = result.result_rows
            
            # 플랫폼별 키워드 분할
            batches = []
            for platform in platforms:
                platform_keywords = []
                
                # 우선순위 기반 키워드 분할
                high_priority = [k for k in keywords if k[3] <= self.config.priority_threshold]
                low_priority = [k for k in keywords if k[3] > self.config.priority_threshold]
                
                # 우선순위가 높은 키워드를 먼저 처리
                all_keywords = high_priority + low_priority
                
                # 배치 크기에 따른 분할
                for i in range(0, len(all_keywords), self.config.batch_size):
                    batch_keywords = all_keywords[i:i + self.config.batch_size]
                    
                    batches.append({
                        "batch_index": len(batches),
                        "platform": platform,
                        "keywords": batch_keywords,
                        "priority": "high" if any(k[3] <= self.config.priority_threshold for k in batch_keywords) else "low",
                        "estimated_time": len(batch_keywords) * 3.0,  # 키워드당 평균 3초 예상
                        "retry_count": 0
                    })
            
            # 우선순위 기준 정렬
            batches.sort(key=lambda x: (x["priority"] == "low", x["estimated_time"]))
            
            logger.info(f"최적화된 배치 생성 완료: {len(batches)}개 배치")
            return batches
            
        except Exception as e:
            logger.error(f"배치 생성 실패: {e}")
            raise
    
    async def _execute_parallel_processing(
        self,
        batch_id: str,
        keyword_batches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """병렬 처리 실행"""
        try:
            # 배치 상태 업데이트
            await self._update_batch_status(batch_id, BatchStatus.RUNNING)
            
            # 병렬 처리 실행
            futures = []
            for batch in keyword_batches:
                future = self.executor.submit(
                    self._process_keyword_batch,
                    batch_id,
                    batch
                )
                futures.append(future)
            
            # 결과 수집
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout)
                    results.append(result)
                    
                    # 실시간 진행률 업데이트
                    await self._update_progress(batch_id, len(results), len(keyword_batches))
                    
                except Exception as e:
                    logger.error(f"배치 처리 중 오류: {e}")
                    results.append({
                        "success": False,
                        "error": str(e),
                        "batch_index": -1,
                        "processed_keywords": 0,
                        "failed_keywords": 1
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"병렬 처리 실행 실패: {e}")
            raise
    
    def _process_keyword_batch(
        self,
        batch_id: str,
        batch: Dict[str, Any]
    ) -> Dict[str, Any]:
        """개별 배치 처리"""
        batch_start_time = time.time()
        processed_keywords = 0
        successful_keywords = 0
        failed_keywords = 0
        processing_times = []
        
        try:
            for keyword_data in batch["keywords"]:
                keyword_id, keyword, category, priority = keyword_data
                
                try:
                    # 키워드 평가 실행
                    result = assess_single_keyword(keyword, batch["platform"])
                    
                    if result.get("success", False):
                        successful_keywords += 1
                        processing_times.append(result.get("processing_time", 0))
                    else:
                        failed_keywords += 1
                        
                    processed_keywords += 1
                    
                    # 메모리 사용량 체크
                    if self._check_memory_usage():
                        logger.warning(f"메모리 사용량 초과, 배치 {batch['batch_index']} 일시 중지")
                        time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"키워드 '{keyword}' 처리 실패: {e}")
                    failed_keywords += 1
                    processed_keywords += 1
            
            batch_processing_time = time.time() - batch_start_time
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
            
            return {
                "success": True,
                "batch_id": batch_id,
                "batch_index": batch["batch_index"],
                "platform": batch["platform"],
                "processed_keywords": processed_keywords,
                "successful_keywords": successful_keywords,
                "failed_keywords": failed_keywords,
                "processing_time": batch_processing_time,
                "avg_processing_time": avg_processing_time,
                "throughput": processed_keywords / batch_processing_time if batch_processing_time > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"배치 {batch['batch_index']} 처리 실패: {e}")
            return {
                "success": False,
                "batch_id": batch_id,
                "batch_index": batch["batch_index"],
                "platform": batch["platform"],
                "error": str(e),
                "processed_keywords": processed_keywords,
                "failed_keywords": len(batch["keywords"]) - processed_keywords
            }
    
    def _check_memory_usage(self) -> bool:
        """메모리 사용량 체크"""
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            return memory_info.used > self.config.memory_limit
        except ImportError:
            return False
    
    async def _update_progress(
        self,
        batch_id: str,
        completed_batches: int,
        total_batches: int
    ) -> None:
        """진행률 업데이트"""
        try:
            progress = (completed_batches / total_batches) * 100 if total_batches > 0 else 0
            
            # Redis에 진행률 캐싱
            await self.redis_client.setex(
                f"batch_progress:{batch_id}",
                3600,
                json.dumps({
                    "completed_batches": completed_batches,
                    "total_batches": total_batches,
                    "progress": progress,
                    "updated_at": datetime.now().isoformat()
                })
            )
            
            logger.info(f"배치 {batch_id} 진행률: {progress:.1f}% ({completed_batches}/{total_batches})")
            
        except Exception as e:
            logger.error(f"진행률 업데이트 실패: {e}")
    
    async def _collect_final_metrics(
        self,
        batch_id: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """최종 메트릭 수집"""
        try:
            total_processed = sum(r.get("processed_keywords", 0) for r in results)
            total_successful = sum(r.get("successful_keywords", 0) for r in results)
            total_failed = sum(r.get("failed_keywords", 0) for r in results)
            total_processing_time = sum(r.get("processing_time", 0) for r in results)
            
            avg_processing_time = total_processing_time / len(results) if results else 0
            success_rate = (total_successful / total_processed) * 100 if total_processed > 0 else 0
            
            # 플랫폼별 메트릭
            platform_metrics = {}
            for result in results:
                platform = result.get("platform", "unknown")
                if platform not in platform_metrics:
                    platform_metrics[platform] = {
                        "processed": 0,
                        "successful": 0,
                        "failed": 0,
                        "avg_time": 0
                    }
                
                platform_metrics[platform]["processed"] += result.get("processed_keywords", 0)
                platform_metrics[platform]["successful"] += result.get("successful_keywords", 0)
                platform_metrics[platform]["failed"] += result.get("failed_keywords", 0)
            
            return {
                "total_processed": total_processed,
                "total_successful": total_successful,
                "total_failed": total_failed,
                "success_rate": success_rate,
                "avg_processing_time": avg_processing_time,
                "total_processing_time": total_processing_time,
                "platform_metrics": platform_metrics,
                "batch_count": len(results),
                "optimization_metrics": {
                    "parallel_efficiency": self._calculate_parallel_efficiency(results),
                    "memory_efficiency": self._calculate_memory_efficiency(),
                    "throughput_improvement": self._calculate_throughput_improvement(results)
                }
            }
            
        except Exception as e:
            logger.error(f"최종 메트릭 수집 실패: {e}")
            return {
                "error": str(e),
                "total_processed": 0,
                "total_successful": 0,
                "total_failed": 0
            }
    
    def _calculate_parallel_efficiency(self, results: List[Dict[str, Any]]) -> float:
        """병렬 처리 효율성 계산"""
        if not results:
            return 0.0
        
        total_time = sum(r.get("processing_time", 0) for r in results)
        sequential_time = sum(r.get("avg_processing_time", 0) * r.get("processed_keywords", 0) for r in results)
        
        return (sequential_time / total_time) if total_time > 0 else 0.0
    
    def _calculate_memory_efficiency(self) -> float:
        """메모리 효율성 계산"""
        try:
            import psutil
            memory_info = psutil.virtual_memory()
            return (1 - memory_info.percent / 100) * 100
        except ImportError:
            return 80.0  # 기본값
    
    def _calculate_throughput_improvement(self, results: List[Dict[str, Any]]) -> float:
        """처리량 개선 계산"""
        if not results:
            return 0.0
        
        avg_throughput = sum(r.get("throughput", 0) for r in results) / len(results)
        baseline_throughput = 1.0  # 기준 처리량 (키워드/초)
        
        return ((avg_throughput - baseline_throughput) / baseline_throughput) * 100
    
    async def _update_batch_status(
        self,
        batch_id: str,
        status: BatchStatus,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """배치 상태 업데이트"""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.now()
            }
            
            if status == BatchStatus.RUNNING:
                update_data["started_at"] = datetime.now()
            elif status == BatchStatus.COMPLETED:
                update_data["completed_at"] = datetime.now()
                if metrics:
                    update_data.update({
                        "processed_keywords": metrics.get("total_processed", 0),
                        "failed_keywords": metrics.get("total_failed", 0),
                        "avg_processing_time": metrics.get("avg_processing_time", 0),
                        "log_data": json.dumps(metrics)
                    })
            elif status == BatchStatus.FAILED and metrics:
                update_data["error_message"] = metrics.get("error", "")
            
            # 데이터베이스 업데이트
            query = """
            ALTER TABLE batch_jobs 
            UPDATE {updates}
            WHERE batch_id = '{batch_id}'
            """.format(
                updates=", ".join([f"{k} = '{v}'" for k, v in update_data.items()]),
                batch_id=batch_id
            )
            
            self.db_client.query(query)
            
            # Redis 캐시 업데이트
            cached_data = await self.redis_client.get(f"batch_status:{batch_id}")
            if cached_data:
                data = json.loads(cached_data)
                data.update(update_data)
                await self.redis_client.setex(
                    f"batch_status:{batch_id}",
                    3600,
                    json.dumps(data)
                )
            
            logger.info(f"배치 상태 업데이트: {batch_id} -> {status.value}")
            
        except Exception as e:
            logger.error(f"배치 상태 업데이트 실패: {e}")
    
    async def get_batch_status(self, batch_id: str) -> Dict[str, Any]:
        """배치 상태 조회"""
        try:
            # Redis 캐시 확인
            cached_data = await self.redis_client.get(f"batch_status:{batch_id}")
            if cached_data:
                return json.loads(cached_data)
            
            # 데이터베이스 조회
            query = f"SELECT * FROM batch_jobs WHERE batch_id = '{batch_id}'"
            result = self.db_client.query(query)
            
            if result.result_rows:
                return {
                    "batch_id": result.result_rows[0][0],
                    "status": result.result_rows[0][2],
                    "total_keywords": result.result_rows[0][3],
                    "processed_keywords": result.result_rows[0][4],
                    "failed_keywords": result.result_rows[0][5],
                    "started_at": result.result_rows[0][7],
                    "completed_at": result.result_rows[0][8]
                }
            
            return {"error": "배치 작업을 찾을 수 없습니다"}
            
        except Exception as e:
            logger.error(f"배치 상태 조회 실패: {e}")
            return {"error": str(e)}
    
    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)