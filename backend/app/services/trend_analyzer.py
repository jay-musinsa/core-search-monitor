"""
날짜별 추이 분석 및 이상치 탐지 서비스
키워드 품질 메트릭의 시간적 변화를 분석하고 이상치를 탐지
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date, timedelta
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import json
import asyncio

from app.core.database import get_database_client
from app.core.redis_client import get_redis_client


logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """추이 분석 및 이상치 탐지 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._load_default_config()
        self.db_client = get_database_client()
        self.redis_client = get_redis_client()
        
        # 이상치 탐지 모델 초기화
        self.isolation_forest = IsolationForest(
            contamination=self.config["contamination_rate"],
            random_state=42
        )
        self.scaler = StandardScaler()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """기본 설정 로드"""
        return {
            "analysis_window_days": 30,
            "trend_window_days": 7,
            "contamination_rate": 0.1,
            "significance_threshold": 0.05,
            "change_threshold": 0.15,
            "min_data_points": 5,
            "cache_ttl": 3600,
            "anomaly_sensitivity": 0.8,
            "trend_patterns": ["increasing", "decreasing", "stable", "volatile"],
            "alert_thresholds": {
                "ndcg_drop": 0.2,
                "precision_drop": 0.15,
                "recall_drop": 0.15
            }
        }
    
    async def analyze_keyword_trends(
        self,
        keyword_id: int,
        platform: str,
        analysis_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        키워드별 추이 분석
        
        Args:
            keyword_id: 키워드 ID
            platform: 플랫폼
            analysis_days: 분석 기간 (일)
            
        Returns:
            Dict[str, Any]: 분석 결과
        """
        try:
            analysis_days = analysis_days or self.config["analysis_window_days"]
            
            # 캐시 확인
            cache_key = f"trend_analysis:{keyword_id}:{platform}:{analysis_days}"
            cached_result = await self.redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # 데이터 수집
            historical_data = await self._collect_historical_data(keyword_id, platform, analysis_days)
            
            if len(historical_data) < self.config["min_data_points"]:
                return {
                    "success": False,
                    "error": "분석을 위한 데이터가 부족합니다",
                    "data_points": len(historical_data)
                }
            
            # 추이 분석 실행
            trend_analysis = await self._perform_trend_analysis(historical_data)
            
            # 이상치 탐지
            anomaly_detection = await self._detect_anomalies(historical_data)
            
            # 계절성 분석
            seasonality_analysis = await self._analyze_seasonality(historical_data)
            
            # 성능 변화 분석
            performance_changes = await self._analyze_performance_changes(historical_data)
            
            # 결과 통합
            result = {
                "success": True,
                "keyword_id": keyword_id,
                "platform": platform,
                "analysis_period": analysis_days,
                "data_points": len(historical_data),
                "trend_analysis": trend_analysis,
                "anomaly_detection": anomaly_detection,
                "seasonality_analysis": seasonality_analysis,
                "performance_changes": performance_changes,
                "generated_at": datetime.now().isoformat()
            }
            
            # 캐시에 저장
            await self.redis_client.setex(
                cache_key,
                self.config["cache_ttl"],
                json.dumps(result, default=str)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"키워드 추이 분석 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "keyword_id": keyword_id,
                "platform": platform
            }
    
    async def _collect_historical_data(
        self,
        keyword_id: int,
        platform: str,
        days: int
    ) -> pd.DataFrame:
        """과거 데이터 수집"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            query = f"""
            SELECT 
                assessment_date,
                gpt_ndcg_score,
                gpt_precision,
                gpt_recall,
                gpt_relevance_score,
                gpt_confidence_score,
                api_response_time,
                api_total_results,
                processing_time
            FROM quality_assessment_daily
            WHERE keyword_id = {keyword_id}
            AND platform = '{platform}'
            AND assessment_date >= '{start_date}'
            AND assessment_date <= '{end_date}'
            ORDER BY assessment_date ASC
            """
            
            result = self.db_client.query(query)
            
            if not result.result_rows:
                return pd.DataFrame()
            
            # DataFrame 생성
            df = pd.DataFrame(result.result_rows, columns=[
                'assessment_date', 'ndcg_score', 'precision', 'recall',
                'relevance_score', 'confidence_score', 'api_response_time',
                'api_total_results', 'processing_time'
            ])
            
            # 날짜 변환
            df['assessment_date'] = pd.to_datetime(df['assessment_date'])
            df.set_index('assessment_date', inplace=True)
            
            # 수치형 변환
            numeric_columns = ['ndcg_score', 'precision', 'recall', 'relevance_score',
                             'confidence_score', 'api_response_time', 'api_total_results', 'processing_time']
            df[numeric_columns] = df[numeric_columns].apply(pd.to_numeric, errors='coerce')
            
            return df
            
        except Exception as e:
            logger.error(f"과거 데이터 수집 실패: {e}")
            return pd.DataFrame()
    
    async def _perform_trend_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """추이 분석 실행"""
        try:
            metrics = ['ndcg_score', 'precision', 'recall', 'relevance_score']
            trend_results = {}
            
            for metric in metrics:
                if metric not in data.columns:
                    continue
                
                values = data[metric].dropna()
                if len(values) < self.config["min_data_points"]:
                    continue
                
                # 추세 계산
                x = np.arange(len(values))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
                
                # 추세 분류
                if p_value < self.config["significance_threshold"]:
                    if slope > self.config["change_threshold"]:
                        trend_type = "increasing"
                    elif slope < -self.config["change_threshold"]:
                        trend_type = "decreasing"
                    else:
                        trend_type = "stable"
                else:
                    trend_type = "no_significant_trend"
                
                # 변동성 계산
                volatility = values.std() / values.mean() if values.mean() != 0 else 0
                
                # 이동평균 계산
                ma_7 = values.rolling(window=min(7, len(values))).mean()
                ma_30 = values.rolling(window=min(30, len(values))).mean()
                
                trend_results[metric] = {
                    "trend_type": trend_type,
                    "slope": slope,
                    "correlation": r_value,
                    "p_value": p_value,
                    "volatility": volatility,
                    "current_value": values.iloc[-1] if len(values) > 0 else 0,
                    "average_value": values.mean(),
                    "min_value": values.min(),
                    "max_value": values.max(),
                    "moving_average_7": ma_7.iloc[-1] if len(ma_7) > 0 else 0,
                    "moving_average_30": ma_30.iloc[-1] if len(ma_30) > 0 else 0,
                    "recent_change": self._calculate_recent_change(values)
                }
            
            return trend_results
            
        except Exception as e:
            logger.error(f"추이 분석 실행 실패: {e}")
            return {}
    
    def _calculate_recent_change(self, values: pd.Series) -> Dict[str, float]:
        """최근 변화 계산"""
        if len(values) < 2:
            return {"1day": 0.0, "7day": 0.0, "30day": 0.0}
        
        current = values.iloc[-1]
        
        changes = {}
        periods = {"1day": 1, "7day": 7, "30day": 30}
        
        for period_name, days in periods.items():
            if len(values) > days:
                previous = values.iloc[-(days+1)]
                change = (current - previous) / previous * 100 if previous != 0 else 0
                changes[period_name] = change
            else:
                changes[period_name] = 0.0
        
        return changes
    
    async def _detect_anomalies(self, data: pd.DataFrame) -> Dict[str, Any]:
        """이상치 탐지"""
        try:
            metrics = ['ndcg_score', 'precision', 'recall', 'relevance_score']
            anomaly_results = {}
            
            # 이상치 탐지를 위한 특성 준비
            features = []
            feature_names = []
            
            for metric in metrics:
                if metric in data.columns:
                    values = data[metric].dropna()
                    if len(values) >= self.config["min_data_points"]:
                        features.append(values.values)
                        feature_names.append(metric)
            
            if not features:
                return {"error": "이상치 탐지를 위한 데이터가 부족합니다"}
            
            # 특성 매트릭스 생성
            min_length = min(len(f) for f in features)
            feature_matrix = np.column_stack([f[-min_length:] for f in features])
            
            # 정규화
            feature_matrix_scaled = self.scaler.fit_transform(feature_matrix)
            
            # 이상치 탐지 모델 훈련
            outliers = self.isolation_forest.fit_predict(feature_matrix_scaled)
            anomaly_scores = self.isolation_forest.decision_function(feature_matrix_scaled)
            
            # 이상치 분석
            anomaly_indices = np.where(outliers == -1)[0]
            anomaly_dates = data.index[-min_length:][anomaly_indices]
            
            # 통계 기반 이상치 탐지
            statistical_anomalies = {}
            for i, metric in enumerate(feature_names):
                values = features[i][-min_length:]
                
                # Z-score 기반 이상치
                z_scores = np.abs(stats.zscore(values))
                z_outliers = np.where(z_scores > 3)[0]
                
                # IQR 기반 이상치
                q1, q3 = np.percentile(values, [25, 75])
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                iqr_outliers = np.where((values < lower_bound) | (values > upper_bound))[0]
                
                statistical_anomalies[metric] = {
                    "z_score_outliers": len(z_outliers),
                    "iqr_outliers": len(iqr_outliers),
                    "outlier_indices": np.union1d(z_outliers, iqr_outliers).tolist()
                }
            
            anomaly_results = {
                "isolation_forest": {
                    "anomaly_count": len(anomaly_indices),
                    "anomaly_dates": [date.isoformat() for date in anomaly_dates],
                    "anomaly_scores": anomaly_scores.tolist(),
                    "average_anomaly_score": np.mean(anomaly_scores)
                },
                "statistical_anomalies": statistical_anomalies,
                "recent_anomaly_alert": self._check_recent_anomalies(data, anomaly_dates)
            }
            
            return anomaly_results
            
        except Exception as e:
            logger.error(f"이상치 탐지 실패: {e}")
            return {"error": str(e)}
    
    def _check_recent_anomalies(self, data: pd.DataFrame, anomaly_dates: List[date]) -> Dict[str, Any]:
        """최근 이상치 알림 체크"""
        try:
            recent_threshold = datetime.now() - timedelta(days=3)
            recent_anomalies = [d for d in anomaly_dates if d >= recent_threshold]
            
            if not recent_anomalies:
                return {"has_recent_anomalies": False}
            
            # 최근 이상치의 원인 분석
            alert_reasons = []
            latest_data = data.iloc[-1]
            
            for metric, threshold in self.config["alert_thresholds"].items():
                if metric in data.columns:
                    current_value = latest_data[metric]
                    avg_value = data[metric].mean()
                    
                    if current_value < avg_value * (1 - threshold):
                        alert_reasons.append(f"{metric} 급감: {current_value:.3f} (평균: {avg_value:.3f})")
            
            return {
                "has_recent_anomalies": True,
                "recent_anomaly_count": len(recent_anomalies),
                "recent_anomaly_dates": [d.isoformat() for d in recent_anomalies],
                "alert_reasons": alert_reasons,
                "severity": "high" if len(alert_reasons) > 1 else "medium"
            }
            
        except Exception as e:
            logger.error(f"최근 이상치 알림 체크 실패: {e}")
            return {"has_recent_anomalies": False, "error": str(e)}
    
    async def _analyze_seasonality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """계절성 분석"""
        try:
            if len(data) < 14:  # 최소 2주 데이터 필요
                return {"error": "계절성 분석을 위한 데이터가 부족합니다"}
            
            metrics = ['ndcg_score', 'precision', 'recall']
            seasonality_results = {}
            
            for metric in metrics:
                if metric not in data.columns:
                    continue
                
                values = data[metric].dropna()
                if len(values) < 14:
                    continue
                
                # 요일별 패턴 분석
                data_with_weekday = data.copy()
                data_with_weekday['weekday'] = data_with_weekday.index.dayofweek
                
                weekday_stats = data_with_weekday.groupby('weekday')[metric].agg(['mean', 'std'])
                
                # 시간대별 패턴 (가능한 경우)
                if len(values) >= 30:
                    # 주간 패턴
                    weekly_pattern = self._detect_weekly_pattern(values)
                    
                    # 월간 패턴
                    monthly_pattern = self._detect_monthly_pattern(data_with_weekday, metric)
                    
                    seasonality_results[metric] = {
                        "weekday_pattern": weekday_stats.to_dict(),
                        "weekly_pattern": weekly_pattern,
                        "monthly_pattern": monthly_pattern,
                        "seasonality_strength": self._calculate_seasonality_strength(values)
                    }
                else:
                    seasonality_results[metric] = {
                        "weekday_pattern": weekday_stats.to_dict(),
                        "insufficient_data": True
                    }
            
            return seasonality_results
            
        except Exception as e:
            logger.error(f"계절성 분석 실패: {e}")
            return {"error": str(e)}
    
    def _detect_weekly_pattern(self, values: pd.Series) -> Dict[str, Any]:
        """주간 패턴 탐지"""
        try:
            # 7일 주기 분석
            if len(values) < 21:  # 최소 3주 데이터
                return {"insufficient_data": True}
            
            # 주간 이동평균
            weekly_ma = values.rolling(window=7).mean()
            
            # 주간 변동성
            weekly_volatility = values.rolling(window=7).std()
            
            return {
                "pattern_detected": True,
                "weekly_average": weekly_ma.mean(),
                "weekly_volatility": weekly_volatility.mean(),
                "pattern_strength": self._calculate_pattern_strength(values, 7)
            }
            
        except Exception as e:
            logger.error(f"주간 패턴 탐지 실패: {e}")
            return {"pattern_detected": False, "error": str(e)}
    
    def _detect_monthly_pattern(self, data: pd.DataFrame, metric: str) -> Dict[str, Any]:
        """월간 패턴 탐지"""
        try:
            if len(data) < 60:  # 최소 2개월 데이터
                return {"insufficient_data": True}
            
            # 월별 통계
            data_with_month = data.copy()
            data_with_month['month'] = data_with_month.index.month
            
            monthly_stats = data_with_month.groupby('month')[metric].agg(['mean', 'std', 'count'])
            
            return {
                "pattern_detected": True,
                "monthly_statistics": monthly_stats.to_dict(),
                "pattern_strength": self._calculate_pattern_strength(data[metric], 30)
            }
            
        except Exception as e:
            logger.error(f"월간 패턴 탐지 실패: {e}")
            return {"pattern_detected": False, "error": str(e)}
    
    def _calculate_seasonality_strength(self, values: pd.Series) -> float:
        """계절성 강도 계산"""
        try:
            if len(values) < 14:
                return 0.0
            
            # 자기상관 계산
            autocorr_7 = values.autocorr(lag=7)  # 주간 자기상관
            autocorr_30 = values.autocorr(lag=min(30, len(values)//2))  # 월간 자기상관
            
            # 계절성 강도 = 자기상관의 절댓값 평균
            seasonality_strength = (abs(autocorr_7) + abs(autocorr_30)) / 2
            
            return seasonality_strength if not np.isnan(seasonality_strength) else 0.0
            
        except Exception as e:
            logger.error(f"계절성 강도 계산 실패: {e}")
            return 0.0
    
    def _calculate_pattern_strength(self, values: pd.Series, period: int) -> float:
        """패턴 강도 계산"""
        try:
            if len(values) < period * 2:
                return 0.0
            
            # 주기적 자기상관
            autocorr = values.autocorr(lag=period)
            
            return abs(autocorr) if not np.isnan(autocorr) else 0.0
            
        except Exception as e:
            logger.error(f"패턴 강도 계산 실패: {e}")
            return 0.0
    
    async def _analyze_performance_changes(self, data: pd.DataFrame) -> Dict[str, Any]:
        """성능 변화 분석"""
        try:
            metrics = ['ndcg_score', 'precision', 'recall']
            performance_results = {}
            
            for metric in metrics:
                if metric not in data.columns:
                    continue
                
                values = data[metric].dropna()
                if len(values) < 10:
                    continue
                
                # 성능 변화 구간 분석
                change_points = self._detect_change_points(values)
                
                # 성능 등급 분류
                performance_grade = self._classify_performance_grade(values)
                
                # 개선/악화 추세
                improvement_trend = self._analyze_improvement_trend(values)
                
                performance_results[metric] = {
                    "change_points": change_points,
                    "performance_grade": performance_grade,
                    "improvement_trend": improvement_trend,
                    "stability_score": self._calculate_stability_score(values)
                }
            
            return performance_results
            
        except Exception as e:
            logger.error(f"성능 변화 분석 실패: {e}")
            return {"error": str(e)}
    
    def _detect_change_points(self, values: pd.Series) -> List[Dict[str, Any]]:
        """변화점 탐지"""
        try:
            if len(values) < 10:
                return []
            
            change_points = []
            window_size = min(5, len(values) // 3)
            
            for i in range(window_size, len(values) - window_size):
                before = values.iloc[i-window_size:i].mean()
                after = values.iloc[i:i+window_size].mean()
                
                # 변화 크기 계산
                change_magnitude = abs(after - before) / before if before != 0 else 0
                
                if change_magnitude > self.config["change_threshold"]:
                    change_points.append({
                        "index": i,
                        "date": values.index[i].isoformat(),
                        "change_magnitude": change_magnitude,
                        "direction": "increase" if after > before else "decrease",
                        "before_value": before,
                        "after_value": after
                    })
            
            return change_points
            
        except Exception as e:
            logger.error(f"변화점 탐지 실패: {e}")
            return []
    
    def _classify_performance_grade(self, values: pd.Series) -> Dict[str, Any]:
        """성능 등급 분류"""
        try:
            current_value = values.iloc[-1]
            percentiles = values.quantile([0.25, 0.5, 0.75, 0.9])
            
            if current_value >= percentiles[0.9]:
                grade = "excellent"
            elif current_value >= percentiles[0.75]:
                grade = "good"
            elif current_value >= percentiles[0.5]:
                grade = "average"
            elif current_value >= percentiles[0.25]:
                grade = "below_average"
            else:
                grade = "poor"
            
            return {
                "current_grade": grade,
                "current_value": current_value,
                "percentile_rank": stats.percentileofscore(values, current_value),
                "grade_distribution": {
                    "excellent": len(values[values >= percentiles[0.9]]),
                    "good": len(values[(values >= percentiles[0.75]) & (values < percentiles[0.9])]),
                    "average": len(values[(values >= percentiles[0.5]) & (values < percentiles[0.75])]),
                    "below_average": len(values[(values >= percentiles[0.25]) & (values < percentiles[0.5])]),
                    "poor": len(values[values < percentiles[0.25]])
                }
            }
            
        except Exception as e:
            logger.error(f"성능 등급 분류 실패: {e}")
            return {"current_grade": "unknown", "error": str(e)}
    
    def _analyze_improvement_trend(self, values: pd.Series) -> Dict[str, Any]:
        """개선 추세 분석"""
        try:
            if len(values) < 5:
                return {"trend": "insufficient_data"}
            
            # 최근 값들과 이전 값들 비교
            recent_values = values.iloc[-5:]
            previous_values = values.iloc[-10:-5] if len(values) >= 10 else values.iloc[:-5]
            
            if len(previous_values) == 0:
                return {"trend": "insufficient_data"}
            
            recent_mean = recent_values.mean()
            previous_mean = previous_values.mean()
            
            improvement_rate = (recent_mean - previous_mean) / previous_mean * 100 if previous_mean != 0 else 0
            
            if improvement_rate > 5:
                trend = "improving"
            elif improvement_rate < -5:
                trend = "deteriorating"
            else:
                trend = "stable"
            
            return {
                "trend": trend,
                "improvement_rate": improvement_rate,
                "recent_average": recent_mean,
                "previous_average": previous_mean,
                "consistency": self._calculate_consistency(recent_values)
            }
            
        except Exception as e:
            logger.error(f"개선 추세 분석 실패: {e}")
            return {"trend": "unknown", "error": str(e)}
    
    def _calculate_stability_score(self, values: pd.Series) -> float:
        """안정성 점수 계산"""
        try:
            if len(values) < 2:
                return 0.0
            
            # 변동계수 (CV = std/mean)
            cv = values.std() / values.mean() if values.mean() != 0 else float('inf')
            
            # 안정성 점수 (낮은 변동계수 = 높은 안정성)
            stability_score = 1 / (1 + cv) if cv != float('inf') else 0
            
            return stability_score
            
        except Exception as e:
            logger.error(f"안정성 점수 계산 실패: {e}")
            return 0.0
    
    def _calculate_consistency(self, values: pd.Series) -> float:
        """일관성 계산"""
        try:
            if len(values) < 2:
                return 0.0
            
            # 연속된 값들 간의 변화량의 평균
            changes = values.diff().abs()
            avg_change = changes.mean()
            
            # 일관성 점수 (낮은 변화량 = 높은 일관성)
            consistency = 1 / (1 + avg_change) if avg_change != 0 else 1
            
            return consistency
            
        except Exception as e:
            logger.error(f"일관성 계산 실패: {e}")
            return 0.0
    
    async def update_trend_data(self, keyword_id: int, platform: str) -> Dict[str, Any]:
        """추이 데이터 업데이트"""
        try:
            # 최신 분석 실행
            analysis_result = await self.analyze_keyword_trends(keyword_id, platform)
            
            if not analysis_result.get("success", False):
                return analysis_result
            
            # keyword_trends 테이블에 저장
            trend_data = {
                "keyword_id": keyword_id,
                "platform": platform,
                "trend_date": date.today(),
                "ndcg_7day_avg": analysis_result["trend_analysis"].get("ndcg_score", {}).get("moving_average_7", 0),
                "ndcg_30day_avg": analysis_result["trend_analysis"].get("ndcg_score", {}).get("moving_average_30", 0),
                "precision_7day_avg": analysis_result["trend_analysis"].get("precision", {}).get("moving_average_7", 0),
                "precision_30day_avg": analysis_result["trend_analysis"].get("precision", {}).get("moving_average_30", 0),
                "ndcg_change_rate": analysis_result["trend_analysis"].get("ndcg_score", {}).get("recent_change", {}).get("7day", 0),
                "precision_change_rate": analysis_result["trend_analysis"].get("precision", {}).get("recent_change", {}).get("7day", 0),
                "relevance_change_rate": analysis_result["trend_analysis"].get("relevance_score", {}).get("recent_change", {}).get("7day", 0),
                "is_anomaly": 1 if analysis_result["anomaly_detection"].get("recent_anomaly_alert", {}).get("has_recent_anomalies", False) else 0,
                "anomaly_score": analysis_result["anomaly_detection"].get("isolation_forest", {}).get("average_anomaly_score", 0),
                "anomaly_type": analysis_result["anomaly_detection"].get("recent_anomaly_alert", {}).get("severity", ""),
                "data_points_count": analysis_result["data_points"],
                "confidence_interval": analysis_result["trend_analysis"].get("ndcg_score", {}).get("correlation", 0),
                "updated_at": datetime.now()
            }
            
            # 기존 데이터 확인 및 업데이트/삽입
            existing_query = f"""
            SELECT COUNT(*) FROM keyword_trends 
            WHERE keyword_id = {keyword_id} 
            AND platform = '{platform}' 
            AND trend_date = '{date.today()}'
            """
            
            existing_result = self.db_client.query(existing_query)
            
            if existing_result.result_rows[0][0] > 0:
                # 업데이트
                update_query = f"""
                ALTER TABLE keyword_trends 
                UPDATE {', '.join([f"{k} = '{v}'" for k, v in trend_data.items() if k not in ['keyword_id', 'platform', 'trend_date']])}
                WHERE keyword_id = {keyword_id} 
                AND platform = '{platform}' 
                AND trend_date = '{date.today()}'
                """
                self.db_client.query(update_query)
            else:
                # 삽입
                self.db_client.insert("keyword_trends", [trend_data])
            
            return {
                "success": True,
                "keyword_id": keyword_id,
                "platform": platform,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"추이 데이터 업데이트 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "keyword_id": keyword_id,
                "platform": platform
            }
    
    async def get_trend_summary(self, days: int = 7) -> Dict[str, Any]:
        """추이 요약 정보 조회"""
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # 전체 키워드 추이 요약
            summary_query = f"""
            SELECT 
                platform,
                COUNT(*) as total_keywords,
                SUM(is_anomaly) as anomaly_count,
                AVG(ndcg_7day_avg) as avg_ndcg,
                AVG(precision_7day_avg) as avg_precision,
                AVG(ndcg_change_rate) as avg_ndcg_change,
                AVG(precision_change_rate) as avg_precision_change
            FROM keyword_trends
            WHERE trend_date >= '{start_date}' AND trend_date <= '{end_date}'
            GROUP BY platform
            """
            
            summary_result = self.db_client.query(summary_query)
            
            platform_summary = {}
            for row in summary_result.result_rows:
                platform_summary[row[0]] = {
                    "total_keywords": row[1],
                    "anomaly_count": row[2],
                    "anomaly_rate": (row[2] / row[1] * 100) if row[1] > 0 else 0,
                    "avg_ndcg": row[3],
                    "avg_precision": row[4],
                    "avg_ndcg_change": row[5],
                    "avg_precision_change": row[6]
                }
            
            # 최근 이상치 키워드 조회
            anomaly_query = f"""
            SELECT 
                km.keyword,
                kt.platform,
                kt.anomaly_score,
                kt.anomaly_type,
                kt.trend_date
            FROM keyword_trends kt
            JOIN keyword_master km ON kt.keyword_id = km.id
            WHERE kt.is_anomaly = 1 
            AND kt.trend_date >= '{start_date}' 
            AND kt.trend_date <= '{end_date}'
            ORDER BY kt.anomaly_score DESC
            LIMIT 10
            """
            
            anomaly_result = self.db_client.query(anomaly_query)
            
            recent_anomalies = [
                {
                    "keyword": row[0],
                    "platform": row[1],
                    "anomaly_score": row[2],
                    "anomaly_type": row[3],
                    "trend_date": row[4].isoformat()
                }
                for row in anomaly_result.result_rows
            ]
            
            return {
                "success": True,
                "summary_period": days,
                "platform_summary": platform_summary,
                "recent_anomalies": recent_anomalies,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"추이 요약 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e)
            }