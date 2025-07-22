#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 실행 스크립트
다중 평가 시스템 지원을 위한 quality_assessment_daily 테이블 업데이트
"""

import os
import sys
import clickhouse_connect
from datetime import datetime

def run_migration():
    """마이그레이션 실행"""
    try:
        # ClickHouse 연결
        client = clickhouse_connect.get_client(
            host='localhost', 
            port=8123, 
            username='default', 
            password=''
        )
        
        print("ClickHouse 연결 성공")
        
        # 마이그레이션 파일 읽기
        migration_file = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'database', 
            'migrations', 
            '001_add_multi_evaluator_columns.sql'
        )
        
        if not os.path.exists(migration_file):
            print(f"마이그레이션 파일을 찾을 수 없습니다: {migration_file}")
            return False
        
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # SQL 문을 세미콜론으로 분리
        sql_statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
        
        print(f"실행할 SQL 문 개수: {len(sql_statements)}")
        
        # 각 SQL 문 실행
        for i, sql in enumerate(sql_statements, 1):
            if sql.startswith('--') or not sql:
                continue
                
            try:
                print(f"[{i}/{len(sql_statements)}] SQL 실행 중...")
                client.query(sql)
                print(f"[{i}/{len(sql_statements)}] 완료")
            except Exception as e:
                if "already exists" in str(e) or "duplicate" in str(e).lower():
                    print(f"[{i}/{len(sql_statements)}] 이미 존재함 (건너뜀)")
                else:
                    print(f"[{i}/{len(sql_statements)}] 실패: {e}")
                    raise
        
        print("✅ 마이그레이션 완료!")
        
        # 테이블 구조 확인
        result = client.query("DESCRIBE quality_assessment_daily")
        print("\n📋 업데이트된 테이블 구조:")
        for row in result.result_rows:
            print(f"  - {row[0]}: {row[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return False

def check_existing_data():
    """기존 데이터 확인"""
    try:
        client = clickhouse_connect.get_client(
            host='localhost', 
            port=8123, 
            username='default', 
            password=''
        )
        
        # 기존 데이터 개수 확인
        result = client.query("SELECT COUNT(*) FROM quality_assessment_daily")
        count = result.result_rows[0][0] if result.result_rows else 0
        
        print(f"📊 기존 데이터 개수: {count}개")
        
        if count > 0:
            # 새 컬럼에 데이터가 있는지 확인
            result = client.query("""
                SELECT COUNT(*) 
                FROM quality_assessment_daily 
                WHERE ndcg_score > 0.0 OR evaluation_method != 'unknown'
            """)
            migrated_count = result.result_rows[0][0] if result.result_rows else 0
            
            print(f"📈 마이그레이션된 데이터: {migrated_count}개")
            
            if migrated_count < count:
                print("⚠️  일부 데이터가 마이그레이션되지 않았을 수 있습니다.")
        
        return count
        
    except Exception as e:
        print(f"데이터 확인 실패: {e}")
        return 0

if __name__ == "__main__":
    print("🚀 다중 평가 시스템 마이그레이션 시작")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # 기존 데이터 확인
    existing_count = check_existing_data()
    
    if existing_count > 0:
        response = input("\n기존 데이터가 있습니다. 마이그레이션을 계속하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("마이그레이션이 취소되었습니다.")
            sys.exit(0)
    
    # 마이그레이션 실행
    success = run_migration()
    
    if success:
        print("\n🎉 마이그레이션이 성공적으로 완료되었습니다!")
        
        # 마이그레이션 후 데이터 확인
        print("\n📊 마이그레이션 후 상태:")
        check_existing_data()
        
    else:
        print("\n💥 마이그레이션이 실패했습니다.")
        sys.exit(1) 