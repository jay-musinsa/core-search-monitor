"""
Redis 클라이언트 관리
"""

import os
import redis
from typing import Optional


def get_redis_client() -> redis.Redis:
    """Redis 클라이언트 인스턴스 반환"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    return redis.from_url(redis_url)


def get_test_redis_client() -> redis.Redis:
    """테스트용 Redis 클라이언트 인스턴스 반환"""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6380/0')
    return redis.from_url(redis_url)