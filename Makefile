.PHONY: help install dev-up dev-down backend frontend test clean

help:
	@echo "사용 가능한 명령어:"
	@echo "  make install     - 의존성 설치"
	@echo "  make dev-up      - Docker 서비스 시작"
	@echo "  make dev-down    - Docker 서비스 중지"
	@echo "  make backend     - 백엔드 서버 실행"
	@echo "  make frontend    - 프론트엔드 서버 실행"
	@echo "  make test        - 테스트 실행"
	@echo "  make clean       - 캐시 정리"

install:
	@echo "백엔드 의존성 설치..."
	cd backend && python3 -m venv venv
	cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "프론트엔드 의존성 설치..."
	cd frontend && npm install

dev-up:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Docker 서비스가 시작되었습니다."

dev-down:
	docker-compose -f docker-compose.dev.yml down
	@echo "Docker 서비스가 중지되었습니다."

backend:
	cd backend && ./venv/bin/uvicorn app.main:app --reload

frontend:
	cd frontend && npm start

test:
	cd backend && ./venv/bin/pytest tests/
	cd frontend && npm test -- --watchAll=false

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
