#!/usr/bin/env python3
"""
ClickHouse 데이터베이스 초기화 스크립트
개발환경에서 데이터베이스 스키마를 자동으로 설정합니다.
"""

import os
import sys
import time
import requests
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python path에 추가
sys.path.append(str(Path(__file__).parent.parent))

from config import Config

def wait_for_clickhouse(host: str, port: int, max_retries: int = 30) -> bool:
    """ClickHouse 서버가 준비될 때까지 대기"""
    print(f"ClickHouse 서버 연결 대기 중... ({host}:{port})")
    
    for i in range(max_retries):
        try:
            response = requests.get(f"http://{host}:{port}/ping", timeout=5)
            if response.status_code == 200:
                print("✅ ClickHouse 서버 연결 성공!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print(f"재시도 중... ({i+1}/{max_retries})")
        time.sleep(2)
    
    print("❌ ClickHouse 서버 연결 실패")
    return False

def execute_sql_file(host: str, port: int, user: str, password: str, sql_file_path: str) -> bool:
    """SQL 파일을 실행"""
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # SQL 문을 세미콜론으로 분리하여 각각 실행
        # 주석과 빈 줄을 제거하되, 라인별로 처리
        processed_lines = []
        for line in sql_content.split('\n'):
            line = line.strip()
            # 빈 줄이나 주석으로 시작하는 줄 제거
            if line and not line.startswith('--'):
                # 라인 끝의 인라인 주석 제거
                if ' --' in line:
                    line = line.split(' --')[0].strip()
                if line:
                    processed_lines.append(line)
        
        # 다시 합치고 세미콜론으로 분리
        cleaned_content = '\n'.join(processed_lines)
        sql_statements = []
        current_statement = ""
        
        for line in cleaned_content.split('\n'):
            current_statement += " " + line
            if line.rstrip().endswith(';'):
                stmt = current_statement.strip()
                if stmt and len(stmt) > 10:  # 최소 길이 체크
                    sql_statements.append(stmt)
                current_statement = ""
        
        # 마지막 문장이 세미콜론으로 끝나지 않은 경우
        if current_statement.strip():
            stmt = current_statement.strip()
            if stmt and len(stmt) > 10:
                sql_statements.append(stmt)
        
        for i, statement in enumerate(sql_statements):
            if not statement:
                continue
                
            print(f"SQL 문 실행 중... ({i+1}/{len(sql_statements)})")
            
            auth = (user, password) if password else None
            response = requests.post(
                f"http://{host}:{port}/",
                data=statement,
                auth=auth,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ SQL 실행 실패: {response.text}")
                return False
        
        print("✅ 모든 SQL 문 실행 완료!")
        return True
        
    except Exception as e:
        print(f"❌ SQL 파일 실행 중 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 ClickHouse 데이터베이스 초기화 시작...")
    
    # 설정 로드
    config = Config()
    
    # ClickHouse 서버 대기
    if not wait_for_clickhouse(config.CLICKHOUSE_HOST, config.CLICKHOUSE_PORT):
        sys.exit(1)
    
    # 스키마 파일 경로
    current_dir = Path(__file__).parent
    schema_file = current_dir / "schema.sql"
    
    if not schema_file.exists():
        print(f"❌ 스키마 파일을 찾을 수 없습니다: {schema_file}")
        sys.exit(1)
    
    # 스키마 실행
    print("📋 데이터베이스 스키마 생성 중...")
    if execute_sql_file(
        config.CLICKHOUSE_HOST,
        config.CLICKHOUSE_PORT,
        config.CLICKHOUSE_USER,
        config.CLICKHOUSE_PASSWORD,
        str(schema_file)
    ):
        print("🎉 데이터베이스 초기화 완료!")
    else:
        print("❌ 데이터베이스 초기화 실패!")
        sys.exit(1)

if __name__ == "__main__":
    main()