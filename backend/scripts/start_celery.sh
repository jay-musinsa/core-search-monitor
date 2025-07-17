#!/bin/bash

# Celery 워커 시작 스크립트
# 키워드 품질평가 시스템을 위한 Celery 워커 설정

# 환경 변수 설정
export CELERY_BROKER_URL="redis://localhost:6379/1"
export CELERY_RESULT_BACKEND="redis://localhost:6379/2"
export PYTHONPATH="/Users/jayko/devhub-musinsa/core-search-monitor/backend:$PYTHONPATH"

echo "Starting Celery workers for keyword quality assessment..."

# 메인 워커 (키워드 평가)
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=keyword_assessment \
    --hostname=worker_assessment@%h \
    --pidfile=/tmp/celery_assessment.pid \
    --logfile=/tmp/celery_assessment.log &

# 배치 처리 워커
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=batch_processing \
    --hostname=worker_batch@%h \
    --pidfile=/tmp/celery_batch.pid \
    --logfile=/tmp/celery_batch.log &

# 추이 분석 워커
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=trend_analysis \
    --hostname=worker_trend@%h \
    --pidfile=/tmp/celery_trend.pid \
    --logfile=/tmp/celery_trend.log &

# 이상치 탐지 워커
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=anomaly_detection \
    --hostname=worker_anomaly@%h \
    --pidfile=/tmp/celery_anomaly.pid \
    --logfile=/tmp/celery_anomaly.log &

echo "Celery workers started successfully!"
echo "Monitoring logs:"
echo "  Assessment worker: /tmp/celery_assessment.log"
echo "  Batch worker: /tmp/celery_batch.log"
echo "  Trend worker: /tmp/celery_trend.log"
echo "  Anomaly worker: /tmp/celery_anomaly.log"

echo ""
echo "To stop all workers:"
echo "  pkill -f 'celery.*worker'"
echo ""
echo "To monitor workers:"
echo "  celery -A app.core.celery_app inspect active"
echo "  celery -A app.core.celery_app inspect stats"

# Flower 모니터링 시작 (옵션)
if [ "$1" == "--with-flower" ]; then
    echo "Starting Flower monitoring..."
    celery -A app.core.celery_app flower \
        --port=5555 \
        --basic_auth=admin:admin123 \
        --broker=redis://localhost:6379/1 &
    
    echo "Flower monitoring available at: http://localhost:5555"
    echo "Username: admin, Password: admin123"
fi

# 포그라운드에서 실행을 위해 대기
wait