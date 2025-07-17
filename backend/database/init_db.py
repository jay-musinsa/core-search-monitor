#!/usr/bin/env python3
"""
ClickHouse 데이터베이스 초기화 스크립트
키워드 품질평가 시스템을 위한 스키마 생성 및 초기 데이터 설정
"""

import asyncio
import clickhouse_connect
from pathlib import Path
import logging
from typing import Optional
import os
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """ClickHouse 데이터베이스 초기화 클래스"""
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 8123,
                 username: str = 'default',
                 password: str = ''):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[clickhouse_connect.driver.Client] = None
        
    async def connect(self) -> bool:
        """ClickHouse 연결 시도"""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password
            )
            
            # 연결 테스트
            result = self.client.query("SELECT 1")
            logger.info(f"ClickHouse 연결 성공: {self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"ClickHouse 연결 실패: {e}")
            return False
    
    def disconnect(self):
        """ClickHouse 연결 종료"""
        if self.client:
            self.client.close()
            logger.info("ClickHouse 연결 종료")
    
    async def execute_schema_file(self, schema_path: Path) -> bool:
        """스키마 파일 실행"""
        try:
            if not schema_path.exists():
                logger.error(f"스키마 파일을 찾을 수 없습니다: {schema_path}")
                return False
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema_content = f.read()
            
            # SQL 문을 개별적으로 실행
            statements = self._split_sql_statements(schema_content)
            
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        logger.info(f"SQL 문 실행 중... ({i+1}/{len(statements)})")
                        self.client.query(statement)
                        logger.debug(f"실행 완료: {statement[:50]}...")
                    except Exception as e:
                        logger.error(f"SQL 문 실행 실패: {e}")
                        logger.error(f"문제 구문: {statement[:100]}...")
                        # 테이블 생성 실패는 무시하고 계속 진행
                        if "already exists" not in str(e).lower():
                            raise
            
            logger.info("스키마 파일 실행 완료")
            return True
            
        except Exception as e:
            logger.error(f"스키마 파일 실행 중 오류: {e}")
            return False
    
    def _split_sql_statements(self, content: str) -> list:
        """SQL 문을 개별 문장으로 분할"""
        # 주석 제거
        lines = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('--'):
                lines.append(line)
        
        content = '\n'.join(lines)
        
        # 세미콜론으로 분할하되, 문자열 내부의 세미콜론은 무시
        statements = []
        current_statement = ""
        in_string = False
        escape_next = False
        
        for char in content:
            if escape_next:
                escape_next = False
                current_statement += char
                continue
                
            if char == '\\':
                escape_next = True
                current_statement += char
                continue
                
            if char == "'" and not in_string:
                in_string = True
            elif char == "'" and in_string:
                in_string = False
            elif char == ';' and not in_string:
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
                continue
            
            current_statement += char
        
        # 마지막 문장 추가
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    async def verify_tables(self) -> bool:
        """테이블 생성 확인"""
        try:
            expected_tables = [
                'keyword_master',
                'quality_assessment_daily',
                'keyword_trends',
                'batch_jobs',
                'system_metrics'
            ]
            
            result = self.client.query("SHOW TABLES")
            existing_tables = [row[0] for row in result.result_rows]
            
            logger.info(f"생성된 테이블: {existing_tables}")
            
            missing_tables = set(expected_tables) - set(existing_tables)
            if missing_tables:
                logger.warning(f"누락된 테이블: {missing_tables}")
                return False
            
            # 각 테이블의 구조 확인
            for table in expected_tables:
                try:
                    result = self.client.query(f"DESCRIBE {table}")
                    logger.info(f"{table} 테이블 구조: {len(result.result_rows)} 컬럼")
                except Exception as e:
                    logger.error(f"{table} 테이블 구조 확인 실패: {e}")
                    return False
            
            logger.info("모든 테이블 생성 및 구조 확인 완료")
            return True
            
        except Exception as e:
            logger.error(f"테이블 확인 중 오류: {e}")
            return False
    
    async def insert_sample_data(self) -> bool:
        """샘플 데이터 삽입"""
        try:
            # 기존 데이터 확인
            result = self.client.query("SELECT COUNT(*) FROM keyword_master")
            existing_count = result.result_rows[0][0]
            
            if existing_count > 0:
                logger.info(f"기존 키워드 데이터 {existing_count}개 확인")
                return True
            
            # 샘플 키워드 데이터
            sample_keywords = [
                (1, '원피스', 'clothing', 1),
                (2, '청바지', 'clothing', 1),
                (3, '운동화', 'shoes', 1),
                (4, '백팩', 'bags', 2),
                (5, '시계', 'accessories', 2),
                (6, '후드티', 'clothing', 1),
                (7, '스니커즈', 'shoes', 1),
                (8, '크로스백', 'bags', 2),
                (9, '반지', 'accessories', 3),
                (10, '모자', 'accessories', 2)
            ]
            
            # 데이터 삽입
            self.client.insert(
                'keyword_master',
                sample_keywords,
                column_names=['id', 'keyword', 'category', 'priority']
            )
            
            logger.info(f"샘플 키워드 데이터 {len(sample_keywords)}개 삽입 완료")
            
            # 샘플 배치 작업 데이터
            sample_batch = [(
                'init_batch_001',
                'system_init',
                'completed',
                10,
                10,
                0,
                datetime.now(),
                datetime.now(),
                datetime.now(),
                '',
                'Database initialization completed',
                0.0,
                0,
                0.0
            )]
            
            self.client.insert(
                'batch_jobs',
                sample_batch,
                column_names=[
                    'batch_id', 'job_type', 'status', 'total_keywords',
                    'processed_keywords', 'failed_keywords', 'scheduled_at',
                    'started_at', 'completed_at', 'error_message', 'log_data',
                    'avg_processing_time', 'gpt_api_calls', 'gpt_api_cost'
                ]
            )
            
            logger.info("샘플 배치 작업 데이터 삽입 완료")
            return True
            
        except Exception as e:
            logger.error(f"샘플 데이터 삽입 실패: {e}")
            return False
    
    async def test_views(self) -> bool:
        """뷰 생성 및 테스트"""
        try:
            # 각 뷰 테스트
            views = [
                'v_keyword_latest_scores',
                'v_daily_performance_summary',
                'v_anomaly_alerts'
            ]
            
            for view in views:
                try:
                    result = self.client.query(f"SELECT * FROM {view} LIMIT 5")
                    logger.info(f"{view} 뷰 테스트 완료: {len(result.result_rows)} 행")
                except Exception as e:
                    logger.error(f"{view} 뷰 테스트 실패: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"뷰 테스트 중 오류: {e}")
            return False


async def main():
    """메인 실행 함수"""
    logger.info("ClickHouse 데이터베이스 초기화 시작")
    
    # 환경 변수에서 설정 읽기
    db_config = {
        'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
        'port': int(os.getenv('CLICKHOUSE_PORT', '8123')),
        'username': os.getenv('CLICKHOUSE_USER', 'default'),
        'password': os.getenv('CLICKHOUSE_PASSWORD', '')
    }
    
    # 데이터베이스 초기화
    initializer = DatabaseInitializer(**db_config)
    
    try:
        # 1. 연결 시도
        if not await initializer.connect():
            logger.error("데이터베이스 연결 실패")
            return False
        
        # 2. 스키마 파일 실행
        schema_path = Path(__file__).parent / 'schema.sql'
        if not await initializer.execute_schema_file(schema_path):
            logger.error("스키마 생성 실패")
            return False
        
        # 3. 테이블 확인
        if not await initializer.verify_tables():
            logger.error("테이블 확인 실패")
            return False
        
        # 4. 샘플 데이터 삽입
        if not await initializer.insert_sample_data():
            logger.error("샘플 데이터 삽입 실패")
            return False
        
        # 5. 뷰 테스트
        if not await initializer.test_views():
            logger.error("뷰 테스트 실패")
            return False
        
        logger.info("데이터베이스 초기화 완료!")
        return True
        
    except Exception as e:
        logger.error(f"초기화 중 예외 발생: {e}")
        return False
    
    finally:
        initializer.disconnect()


if __name__ == "__main__":
    success = asyncio.run(main())
    if success:
        logger.info("✅ 데이터베이스 초기화 성공")
    else:
        logger.error("❌ 데이터베이스 초기화 실패")
        exit(1)