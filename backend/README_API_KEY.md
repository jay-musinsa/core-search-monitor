# OpenAI API 키 설정 방법

## 1. OpenAI API 키 발급

1. [OpenAI 웹사이트](https://platform.openai.com/api-keys)에 접속
2. 계정 로그인 후 API 키 생성
3. 생성된 API 키 복사

## 2. 환경변수 설정

### 방법 1: .env 파일 사용 (권장)
```bash
# backend/.env 파일 편집
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 방법 2: 터미널에서 직접 설정
```bash
export OPENAI_API_KEY="sk-your-actual-api-key-here"
```

## 3. 확인 방법

백엔드 실행 시 다음 메시지가 나타나지 않으면 성공:
```
[GPT] 경고: OPENAI_API_KEY 환경변수가 설정되지 않았습니다.
```

## 4. 보안 주의사항

- ⚠️ **절대로 API 키를 Git에 커밋하지 마세요**
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- API 키는 안전한 곳에 보관하세요

## 5. 비용 관리

- GPT-4 Vision API는 유료 서비스입니다
- 사용량을 모니터링하세요
- 필요시 API 키에 사용량 제한을 설정하세요 