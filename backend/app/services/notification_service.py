"""
실시간 알림 및 모니터링 시스템
키워드 품질 이상치 탐지 시 실시간 알림 발송
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import requests
import websockets
import os

from app.core.database import get_database_client
from app.core.redis_client import get_redis_client
from app.services.trend_analyzer import TrendAnalyzer


logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """알림 레벨"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """알림 채널"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    WEBSOCKET = "websocket"
    SMS = "sms"


@dataclass
class NotificationRule:
    """알림 규칙"""
    id: str
    name: str
    description: str
    conditions: Dict[str, Any]
    channels: List[NotificationChannel]
    level: NotificationLevel
    enabled: bool = True
    cooldown_minutes: int = 60
    recipients: List[str] = None


@dataclass
class NotificationEvent:
    """알림 이벤트"""
    id: str
    rule_id: str
    level: NotificationLevel
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    keyword_id: int
    platform: str
    channels: List[NotificationChannel]
    status: str = "pending"


class NotificationService:
    """알림 서비스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.db_client = get_database_client()
        self.redis_client = get_redis_client()
        self.trend_analyzer = TrendAnalyzer()
        
        # 알림 규칙 캐시
        self.notification_rules: Dict[str, NotificationRule] = {}
        
        # WebSocket 연결 관리
        self.websocket_connections: List[websockets.WebSocketServerProtocol] = []
        
        # 알림 큐
        self.notification_queue = asyncio.Queue()
        
        # 백그라운드 작업
        self.background_tasks: List[asyncio.Task] = []
    
    def _load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        return {
            "email": {
                "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                "username": os.getenv("SMTP_USERNAME", ""),
                "password": os.getenv("SMTP_PASSWORD", ""),
                "from_email": os.getenv("FROM_EMAIL", ""),
                "use_tls": True
            },
            "slack": {
                "webhook_url": os.getenv("SLACK_WEBHOOK_URL", ""),
                "channel": os.getenv("SLACK_CHANNEL", "#alerts"),
                "username": "KeywordMonitor",
                "icon_emoji": ":warning:"
            },
            "webhook": {
                "default_url": os.getenv("WEBHOOK_URL", ""),
                "timeout": 30,
                "retry_count": 3
            },
            "websocket": {
                "port": int(os.getenv("WEBSOCKET_PORT", "8765")),
                "host": os.getenv("WEBSOCKET_HOST", "localhost")
            },
            "monitoring": {
                "check_interval": 300,  # 5분마다 체크
                "batch_size": 100,
                "max_alerts_per_hour": 50
            },
            "rate_limiting": {
                "enabled": True,
                "max_notifications_per_minute": 10,
                "cooldown_period": 3600  # 1시간
            }
        }
    
    async def start_service(self) -> None:
        """서비스 시작"""
        try:
            # 알림 규칙 로드
            await self._load_notification_rules()
            
            # WebSocket 서버 시작
            await self._start_websocket_server()
            
            # 백그라운드 작업 시작
            self.background_tasks.append(
                asyncio.create_task(self._process_notification_queue())
            )
            self.background_tasks.append(
                asyncio.create_task(self._periodic_monitoring())
            )
            
            logger.info("알림 서비스 시작 완료")
            
        except Exception as e:
            logger.error(f"알림 서비스 시작 실패: {e}")
            raise
    
    async def stop_service(self) -> None:
        """서비스 중지"""
        try:
            # 백그라운드 작업 중지
            for task in self.background_tasks:
                task.cancel()
            
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            # WebSocket 연결 종료
            for connection in self.websocket_connections:
                await connection.close()
            
            logger.info("알림 서비스 종료 완료")
            
        except Exception as e:
            logger.error(f"알림 서비스 종료 실패: {e}")
    
    async def _load_notification_rules(self) -> None:
        """알림 규칙 로드"""
        try:
            # 기본 알림 규칙 설정
            default_rules = [
                NotificationRule(
                    id="ndcg_drop_high",
                    name="NDCG 급감 (High)",
                    description="NDCG 점수가 20% 이상 급감한 경우",
                    conditions={
                        "metric": "ndcg_score",
                        "change_type": "drop",
                        "threshold": 0.2,
                        "timeframe": "1day"
                    },
                    channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBSOCKET],
                    level=NotificationLevel.HIGH,
                    cooldown_minutes=30
                ),
                NotificationRule(
                    id="precision_drop_medium",
                    name="Precision 급감 (Medium)",
                    description="Precision이 15% 이상 급감한 경우",
                    conditions={
                        "metric": "precision",
                        "change_type": "drop",
                        "threshold": 0.15,
                        "timeframe": "1day"
                    },
                    channels=[NotificationChannel.SLACK, NotificationChannel.WEBSOCKET],
                    level=NotificationLevel.MEDIUM,
                    cooldown_minutes=60
                ),
                NotificationRule(
                    id="batch_failure_critical",
                    name="배치 처리 실패 (Critical)",
                    description="배치 처리가 연속으로 실패한 경우",
                    conditions={
                        "event_type": "batch_failure",
                        "consecutive_failures": 3
                    },
                    channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK, NotificationChannel.WEBHOOK],
                    level=NotificationLevel.CRITICAL,
                    cooldown_minutes=15
                ),
                NotificationRule(
                    id="anomaly_detection_high",
                    name="이상치 탐지 (High)",
                    description="이상치가 탐지된 경우",
                    conditions={
                        "event_type": "anomaly_detected",
                        "anomaly_score": 0.8
                    },
                    channels=[NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET],
                    level=NotificationLevel.HIGH,
                    cooldown_minutes=30
                ),
                NotificationRule(
                    id="daily_summary_low",
                    name="일일 요약 (Low)",
                    description="일일 처리 요약 정보",
                    conditions={
                        "event_type": "daily_summary",
                        "schedule": "daily"
                    },
                    channels=[NotificationChannel.EMAIL],
                    level=NotificationLevel.LOW,
                    cooldown_minutes=1440  # 24시간
                )
            ]
            
            for rule in default_rules:
                self.notification_rules[rule.id] = rule
            
            logger.info(f"알림 규칙 로드 완료: {len(self.notification_rules)}개")
            
        except Exception as e:
            logger.error(f"알림 규칙 로드 실패: {e}")
    
    async def _start_websocket_server(self) -> None:
        """WebSocket 서버 시작"""
        try:
            async def handle_websocket(websocket, path):
                self.websocket_connections.append(websocket)
                try:
                    await websocket.wait_closed()
                finally:
                    self.websocket_connections.remove(websocket)
            
            server = await websockets.serve(
                handle_websocket,
                self.config["websocket"]["host"],
                self.config["websocket"]["port"]
            )
            
            logger.info(f"WebSocket 서버 시작: {self.config['websocket']['host']}:{self.config['websocket']['port']}")
            
        except Exception as e:
            logger.error(f"WebSocket 서버 시작 실패: {e}")
    
    async def _process_notification_queue(self) -> None:
        """알림 큐 처리"""
        while True:
            try:
                # 큐에서 알림 이벤트 가져오기
                event = await self.notification_queue.get()
                
                # 레ート 제한 확인
                if await self._check_rate_limit(event):
                    await self._send_notification(event)
                else:
                    logger.warning(f"알림 레이트 제한으로 인해 스킵: {event.id}")
                
                # 큐 작업 완료 표시
                self.notification_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"알림 큐 처리 중 오류: {e}")
                await asyncio.sleep(1)
    
    async def _periodic_monitoring(self) -> None:
        """주기적 모니터링"""
        while True:
            try:
                await asyncio.sleep(self.config["monitoring"]["check_interval"])
                
                # 키워드 이상치 체크
                await self._check_keyword_anomalies()
                
                # 배치 작업 상태 체크
                await self._check_batch_job_status()
                
                # 시스템 상태 체크
                await self._check_system_health()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"주기적 모니터링 중 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도
    
    async def _check_keyword_anomalies(self) -> None:
        """키워드 이상치 체크"""
        try:
            # 최근 처리된 키워드 조회
            recent_query = f"""
            SELECT DISTINCT keyword_id, platform
            FROM quality_assessment_daily
            WHERE assessment_date >= today() - INTERVAL 1 DAY
            LIMIT {self.config['monitoring']['batch_size']}
            """
            
            result = self.db_client.query(recent_query)
            
            for row in result.result_rows:
                keyword_id, platform = row
                
                # 추이 분석 실행
                trend_result = await self.trend_analyzer.analyze_keyword_trends(keyword_id, platform)
                
                if trend_result.get("success", False):
                    # 이상치 알림 체크
                    await self._evaluate_anomaly_alerts(keyword_id, platform, trend_result)
                    
                    # 성능 변화 알림 체크
                    await self._evaluate_performance_alerts(keyword_id, platform, trend_result)
            
        except Exception as e:
            logger.error(f"키워드 이상치 체크 실패: {e}")
    
    async def _check_batch_job_status(self) -> None:
        """배치 작업 상태 체크"""
        try:
            # 실패한 배치 작업 조회
            failed_query = """
            SELECT batch_id, job_type, error_message, failed_keywords
            FROM batch_jobs
            WHERE status = 'failed'
            AND created_at >= now() - INTERVAL 1 HOUR
            """
            
            result = self.db_client.query(failed_query)
            
            for row in result.result_rows:
                batch_id, job_type, error_message, failed_keywords = row
                
                # 배치 실패 알림 생성
                await self._create_batch_failure_alert(batch_id, job_type, error_message, failed_keywords)
            
        except Exception as e:
            logger.error(f"배치 작업 상태 체크 실패: {e}")
    
    async def _check_system_health(self) -> None:
        """시스템 상태 체크"""
        try:
            # 시스템 메트릭 조회
            system_query = """
            SELECT 
                metric_type,
                AVG(metric_value) as avg_value,
                MAX(metric_value) as max_value
            FROM system_metrics
            WHERE metric_time >= now() - INTERVAL 1 HOUR
            GROUP BY metric_type
            """
            
            result = self.db_client.query(system_query)
            
            for row in result.result_rows:
                metric_type, avg_value, max_value = row
                
                # 시스템 알림 규칙 확인
                await self._evaluate_system_alerts(metric_type, avg_value, max_value)
            
        except Exception as e:
            logger.error(f"시스템 상태 체크 실패: {e}")
    
    async def _evaluate_anomaly_alerts(self, keyword_id: int, platform: str, trend_result: Dict[str, Any]) -> None:
        """이상치 알림 평가"""
        try:
            anomaly_info = trend_result.get("anomaly_detection", {})
            recent_anomaly = anomaly_info.get("recent_anomaly_alert", {})
            
            if recent_anomaly.get("has_recent_anomalies", False):
                # 키워드 정보 조회
                keyword_query = f"SELECT keyword FROM keyword_master WHERE id = {keyword_id}"
                keyword_result = self.db_client.query(keyword_query)
                keyword = keyword_result.result_rows[0][0] if keyword_result.result_rows else f"ID:{keyword_id}"
                
                # 이상치 알림 이벤트 생성
                event = NotificationEvent(
                    id=f"anomaly_{keyword_id}_{platform}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    rule_id="anomaly_detection_high",
                    level=NotificationLevel.HIGH,
                    title=f"키워드 이상치 탐지: {keyword}",
                    message=f"키워드 '{keyword}' ({platform})에서 이상치가 탐지되었습니다.",
                    data={
                        "keyword_id": keyword_id,
                        "keyword": keyword,
                        "platform": platform,
                        "anomaly_count": recent_anomaly.get("recent_anomaly_count", 0),
                        "severity": recent_anomaly.get("severity", "medium"),
                        "alert_reasons": recent_anomaly.get("alert_reasons", [])
                    },
                    timestamp=datetime.now(),
                    keyword_id=keyword_id,
                    platform=platform,
                    channels=[NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET]
                )
                
                await self.notification_queue.put(event)
            
        except Exception as e:
            logger.error(f"이상치 알림 평가 실패: {e}")
    
    async def _evaluate_performance_alerts(self, keyword_id: int, platform: str, trend_result: Dict[str, Any]) -> None:
        """성능 변화 알림 평가"""
        try:
            trend_analysis = trend_result.get("trend_analysis", {})
            
            # NDCG 급감 체크
            ndcg_info = trend_analysis.get("ndcg_score", {})
            ndcg_change = ndcg_info.get("recent_change", {}).get("1day", 0)
            
            if ndcg_change < -20:  # 20% 이상 급감
                await self._create_performance_alert(keyword_id, platform, "ndcg_drop_high", "NDCG", ndcg_change)
            
            # Precision 급감 체크
            precision_info = trend_analysis.get("precision", {})
            precision_change = precision_info.get("recent_change", {}).get("1day", 0)
            
            if precision_change < -15:  # 15% 이상 급감
                await self._create_performance_alert(keyword_id, platform, "precision_drop_medium", "Precision", precision_change)
            
        except Exception as e:
            logger.error(f"성능 변화 알림 평가 실패: {e}")
    
    async def _create_performance_alert(self, keyword_id: int, platform: str, rule_id: str, metric_name: str, change_value: float) -> None:
        """성능 알림 생성"""
        try:
            # 키워드 정보 조회
            keyword_query = f"SELECT keyword FROM keyword_master WHERE id = {keyword_id}"
            keyword_result = self.db_client.query(keyword_query)
            keyword = keyword_result.result_rows[0][0] if keyword_result.result_rows else f"ID:{keyword_id}"
            
            rule = self.notification_rules.get(rule_id)
            if not rule:
                return
            
            event = NotificationEvent(
                id=f"performance_{keyword_id}_{platform}_{metric_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                rule_id=rule_id,
                level=rule.level,
                title=f"{metric_name} 성능 급감: {keyword}",
                message=f"키워드 '{keyword}' ({platform})의 {metric_name}이 {abs(change_value):.1f}% 급감했습니다.",
                data={
                    "keyword_id": keyword_id,
                    "keyword": keyword,
                    "platform": platform,
                    "metric_name": metric_name,
                    "change_value": change_value,
                    "alert_threshold": rule.conditions.get("threshold", 0) * 100
                },
                timestamp=datetime.now(),
                keyword_id=keyword_id,
                platform=platform,
                channels=rule.channels
            )
            
            await self.notification_queue.put(event)
            
        except Exception as e:
            logger.error(f"성능 알림 생성 실패: {e}")
    
    async def _create_batch_failure_alert(self, batch_id: str, job_type: str, error_message: str, failed_keywords: int) -> None:
        """배치 실패 알림 생성"""
        try:
            rule = self.notification_rules.get("batch_failure_critical")
            if not rule:
                return
            
            event = NotificationEvent(
                id=f"batch_failure_{batch_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                rule_id="batch_failure_critical",
                level=NotificationLevel.CRITICAL,
                title=f"배치 처리 실패: {batch_id}",
                message=f"배치 작업 '{job_type}'이 실패했습니다. 실패한 키워드: {failed_keywords}개",
                data={
                    "batch_id": batch_id,
                    "job_type": job_type,
                    "error_message": error_message,
                    "failed_keywords": failed_keywords
                },
                timestamp=datetime.now(),
                keyword_id=0,
                platform="system",
                channels=rule.channels
            )
            
            await self.notification_queue.put(event)
            
        except Exception as e:
            logger.error(f"배치 실패 알림 생성 실패: {e}")
    
    async def _evaluate_system_alerts(self, metric_type: str, avg_value: float, max_value: float) -> None:
        """시스템 알림 평가"""
        try:
            # 시스템 메트릭 임계값 체크
            thresholds = {
                "cpu": {"warning": 80, "critical": 90},
                "memory": {"warning": 85, "critical": 95},
                "disk": {"warning": 90, "critical": 95}
            }
            
            if metric_type in thresholds:
                threshold = thresholds[metric_type]
                
                if max_value > threshold["critical"]:
                    await self._create_system_alert(metric_type, max_value, "critical")
                elif avg_value > threshold["warning"]:
                    await self._create_system_alert(metric_type, avg_value, "warning")
            
        except Exception as e:
            logger.error(f"시스템 알림 평가 실패: {e}")
    
    async def _create_system_alert(self, metric_type: str, value: float, severity: str) -> None:
        """시스템 알림 생성"""
        try:
            level = NotificationLevel.CRITICAL if severity == "critical" else NotificationLevel.HIGH
            
            event = NotificationEvent(
                id=f"system_{metric_type}_{severity}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                rule_id="system_alert",
                level=level,
                title=f"시스템 {metric_type.upper()} 알림",
                message=f"시스템 {metric_type} 사용률이 {value:.1f}%에 도달했습니다.",
                data={
                    "metric_type": metric_type,
                    "value": value,
                    "severity": severity
                },
                timestamp=datetime.now(),
                keyword_id=0,
                platform="system",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK]
            )
            
            await self.notification_queue.put(event)
            
        except Exception as e:
            logger.error(f"시스템 알림 생성 실패: {e}")
    
    async def _check_rate_limit(self, event: NotificationEvent) -> bool:
        """알림 레이트 제한 체크"""
        try:
            if not self.config["rate_limiting"]["enabled"]:
                return True
            
            # 쿨다운 기간 체크
            cooldown_key = f"notification_cooldown:{event.rule_id}:{event.keyword_id}:{event.platform}"
            cooldown_data = await self.redis_client.get(cooldown_key)
            
            if cooldown_data:
                return False
            
            # 분당 알림 횟수 체크
            rate_key = f"notification_rate:{datetime.now().strftime('%Y%m%d%H%M')}"
            current_count = await self.redis_client.get(rate_key)
            
            if current_count and int(current_count) >= self.config["rate_limiting"]["max_notifications_per_minute"]:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"레이트 제한 체크 실패: {e}")
            return True
    
    async def _send_notification(self, event: NotificationEvent) -> None:
        """알림 발송"""
        try:
            # 각 채널별로 알림 발송
            for channel in event.channels:
                try:
                    if channel == NotificationChannel.EMAIL:
                        await self._send_email_notification(event)
                    elif channel == NotificationChannel.SLACK:
                        await self._send_slack_notification(event)
                    elif channel == NotificationChannel.WEBHOOK:
                        await self._send_webhook_notification(event)
                    elif channel == NotificationChannel.WEBSOCKET:
                        await self._send_websocket_notification(event)
                    
                except Exception as e:
                    logger.error(f"알림 발송 실패 ({channel.value}): {e}")
            
            # 쿨다운 설정
            rule = self.notification_rules.get(event.rule_id)
            if rule:
                cooldown_key = f"notification_cooldown:{event.rule_id}:{event.keyword_id}:{event.platform}"
                await self.redis_client.setex(cooldown_key, rule.cooldown_minutes * 60, "1")
            
            # 레이트 제한 카운터 증가
            rate_key = f"notification_rate:{datetime.now().strftime('%Y%m%d%H%M')}"
            await self.redis_client.incr(rate_key)
            await self.redis_client.expire(rate_key, 60)
            
            # 알림 로그 저장
            await self._log_notification(event)
            
        except Exception as e:
            logger.error(f"알림 발송 실패: {e}")
    
    async def _send_email_notification(self, event: NotificationEvent) -> None:
        """이메일 알림 발송"""
        try:
            email_config = self.config["email"]
            
            if not email_config["username"] or not email_config["from_email"]:
                logger.warning("이메일 설정이 없어 알림을 건너뜁니다")
                return
            
            # 이메일 내용 생성
            msg = MIMEMultipart()
            msg['From'] = email_config["from_email"]
            msg['To'] = ", ".join(event.data.get("recipients", [email_config["from_email"]]))
            msg['Subject'] = f"[{event.level.value.upper()}] {event.title}"
            
            # HTML 템플릿
            html_content = f"""
            <html>
            <body>
                <h2>{event.title}</h2>
                <p><strong>레벨:</strong> {event.level.value.upper()}</p>
                <p><strong>시간:</strong> {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>메시지:</strong> {event.message}</p>
                
                <h3>상세 정보:</h3>
                <ul>
                    {"".join([f"<li><strong>{k}:</strong> {v}</li>" for k, v in event.data.items()])}
                </ul>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            # SMTP 발송
            server = smtplib.SMTP(email_config["smtp_server"], email_config["smtp_port"])
            if email_config["use_tls"]:
                server.starttls()
            server.login(email_config["username"], email_config["password"])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"이메일 알림 발송 완료: {event.id}")
            
        except Exception as e:
            logger.error(f"이메일 알림 발송 실패: {e}")
    
    async def _send_slack_notification(self, event: NotificationEvent) -> None:
        """슬랙 알림 발송"""
        try:
            slack_config = self.config["slack"]
            
            if not slack_config["webhook_url"]:
                logger.warning("슬랙 설정이 없어 알림을 건너뜁니다")
                return
            
            # 슬랙 메시지 구성
            color = {
                NotificationLevel.LOW: "good",
                NotificationLevel.MEDIUM: "warning",
                NotificationLevel.HIGH: "danger",
                NotificationLevel.CRITICAL: "danger"
            }.get(event.level, "warning")
            
            slack_data = {
                "channel": slack_config["channel"],
                "username": slack_config["username"],
                "icon_emoji": slack_config["icon_emoji"],
                "attachments": [
                    {
                        "color": color,
                        "title": event.title,
                        "text": event.message,
                        "fields": [
                            {
                                "title": "레벨",
                                "value": event.level.value.upper(),
                                "short": True
                            },
                            {
                                "title": "시간",
                                "value": event.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                                "short": True
                            }
                        ],
                        "footer": "KeywordMonitor",
                        "ts": event.timestamp.timestamp()
                    }
                ]
            }
            
            # 상세 정보 추가
            for key, value in event.data.items():
                if key not in ["recipients"]:
                    slack_data["attachments"][0]["fields"].append({
                        "title": key,
                        "value": str(value),
                        "short": True
                    })
            
            # HTTP 요청 발송
            response = requests.post(
                slack_config["webhook_url"],
                json=slack_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"슬랙 알림 발송 완료: {event.id}")
            else:
                logger.error(f"슬랙 알림 발송 실패: {response.status_code}")
            
        except Exception as e:
            logger.error(f"슬랙 알림 발송 실패: {e}")
    
    async def _send_webhook_notification(self, event: NotificationEvent) -> None:
        """웹훅 알림 발송"""
        try:
            webhook_config = self.config["webhook"]
            
            if not webhook_config["default_url"]:
                logger.warning("웹훅 설정이 없어 알림을 건너뜁니다")
                return
            
            # 웹훅 페이로드 구성
            payload = {
                "event_id": event.id,
                "rule_id": event.rule_id,
                "level": event.level.value,
                "title": event.title,
                "message": event.message,
                "timestamp": event.timestamp.isoformat(),
                "keyword_id": event.keyword_id,
                "platform": event.platform,
                "data": event.data
            }
            
            # HTTP 요청 발송
            response = requests.post(
                webhook_config["default_url"],
                json=payload,
                timeout=webhook_config["timeout"]
            )
            
            if response.status_code == 200:
                logger.info(f"웹훅 알림 발송 완료: {event.id}")
            else:
                logger.error(f"웹훅 알림 발송 실패: {response.status_code}")
            
        except Exception as e:
            logger.error(f"웹훅 알림 발송 실패: {e}")
    
    async def _send_websocket_notification(self, event: NotificationEvent) -> None:
        """WebSocket 알림 발송"""
        try:
            if not self.websocket_connections:
                logger.debug("WebSocket 연결이 없어 알림을 건너뜁니다")
                return
            
            # WebSocket 메시지 구성
            message = {
                "type": "notification",
                "event_id": event.id,
                "level": event.level.value,
                "title": event.title,
                "message": event.message,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }
            
            # 모든 연결된 클라이언트에게 발송
            disconnected_connections = []
            for connection in self.websocket_connections:
                try:
                    await connection.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    disconnected_connections.append(connection)
            
            # 연결 종료된 클라이언트 제거
            for connection in disconnected_connections:
                self.websocket_connections.remove(connection)
            
            logger.info(f"WebSocket 알림 발송 완료: {event.id} (연결: {len(self.websocket_connections)})")
            
        except Exception as e:
            logger.error(f"WebSocket 알림 발송 실패: {e}")
    
    async def _log_notification(self, event: NotificationEvent) -> None:
        """알림 로그 저장"""
        try:
            log_data = {
                "event_id": event.id,
                "rule_id": event.rule_id,
                "level": event.level.value,
                "title": event.title,
                "message": event.message,
                "keyword_id": event.keyword_id,
                "platform": event.platform,
                "channels": [c.value for c in event.channels],
                "data": json.dumps(event.data),
                "timestamp": event.timestamp,
                "status": "sent"
            }
            
            self.db_client.insert("notification_logs", [log_data])
            
        except Exception as e:
            logger.error(f"알림 로그 저장 실패: {e}")
    
    async def send_custom_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel,
        channels: List[NotificationChannel],
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """사용자 정의 알림 발송"""
        try:
            event = NotificationEvent(
                id=f"custom_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                rule_id="custom",
                level=level,
                title=title,
                message=message,
                data=data or {},
                timestamp=datetime.now(),
                keyword_id=0,
                platform="custom",
                channels=channels
            )
            
            await self.notification_queue.put(event)
            
            return {
                "success": True,
                "event_id": event.id,
                "message": "알림이 큐에 추가되었습니다"
            }
            
        except Exception as e:
            logger.error(f"사용자 정의 알림 발송 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_notification_history(self, limit: int = 100) -> Dict[str, Any]:
        """알림 히스토리 조회"""
        try:
            query = f"""
            SELECT 
                event_id, rule_id, level, title, message, 
                keyword_id, platform, channels, timestamp, status
            FROM notification_logs
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
            
            result = self.db_client.query(query)
            
            history = [
                {
                    "event_id": row[0],
                    "rule_id": row[1],
                    "level": row[2],
                    "title": row[3],
                    "message": row[4],
                    "keyword_id": row[5],
                    "platform": row[6],
                    "channels": json.loads(row[7]),
                    "timestamp": row[8].isoformat(),
                    "status": row[9]
                }
                for row in result.result_rows
            ]
            
            return {
                "success": True,
                "history": history,
                "total": len(history)
            }
            
        except Exception as e:
            logger.error(f"알림 히스토리 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 알림 관련 데이터베이스 테이블 스키마
NOTIFICATION_LOGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS notification_logs (
    event_id String,
    rule_id String,
    level String,
    title String,
    message String,
    keyword_id UInt32,
    platform String,
    channels String,
    data String DEFAULT '{}',
    timestamp DateTime DEFAULT now(),
    status String DEFAULT 'sent'
) ENGINE = MergeTree()
ORDER BY timestamp
SETTINGS index_granularity = 8192;
"""