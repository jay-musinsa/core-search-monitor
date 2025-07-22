// API 서비스 모듈
const BASE_URL = "http://localhost:8000";

// /api/metrics REST API 호출
export async function getMetrics() {
  const res = await fetch("http://localhost:8000/api/metrics");
  if (!res.ok) throw new Error("메트릭 조회 실패");
  return await res.json();
}

// /ws WebSocket 구독
export function subscribeMetrics(onMessage) {
  const ws = new WebSocket("ws://localhost:8000/ws");
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("[WebSocket] 메시지 수신:", data);

      // 모든 메시지 타입을 onMessage 콜백으로 전달
      onMessage(data);
    } catch (error) {
      console.error("[WebSocket] 메시지 파싱 오류:", error);
    }
  };
  return ws;
}

// 키워드 입력 API
export async function postKeyword(keyword) {
  const res = await fetch("http://localhost:8000/api/keyword", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keyword }),
  });
  if (!res.ok) throw new Error("키워드 전송 실패");
  return await res.json();
}

// Quality Dashboard API들

// 키워드 품질 데이터 조회
export const getKeywordQuality = async (filters = {}) => {
  try {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response = await fetch(
      `${BASE_URL}/api/quality/dashboard/data?${params}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("키워드 품질 데이터 조회 실패:", error);
    throw error;
  }
};

// 트렌드 데이터 조회
export const getTrendData = async (filters = {}) => {
  try {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value.toString());
      }
    });

    const response = await fetch(
      `${BASE_URL}/api/quality/trend/data?${params}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("트렌드 데이터 조회 실패:", error);
    throw error;
  }
};

// 특정 키워드 분석 조회
export const getKeywordAnalysis = async (
  keywordId,
  platform = "musinsa",
  days = 30
) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/keyword/${keywordId}/analysis?platform=${platform}&days=${days}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("키워드 분석 조회 실패:", error);
    throw error;
  }
};

// 배치 작업 시작
export const startBatchJob = async (request) => {
  try {
    const response = await fetch(`${BASE_URL}/api/quality/batch/optimize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("배치 작업 시작 실패:", error);
    throw error;
  }
};

// 배치 작업 상태 조회
export const getBatchStatus = async (batchId) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/batch/${batchId}/status`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("배치 상태 조회 실패:", error);
    throw error;
  }
};

// 트렌드 요약 조회
export const getTrendSummary = async (days = 7) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/trends/summary?days=${days}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("트렌드 요약 조회 실패:", error);
    throw error;
  }
};

// 이미지 메타데이터 조회
export const getImageMetadata = async (imageId) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/images/${imageId}/metadata`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("이미지 메타데이터 조회 실패:", error);
    throw error;
  }
};

// 이미지 저장소 통계 조회
export const getStorageStats = async () => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/images/storage/stats`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("저장소 통계 조회 실패:", error);
    throw error;
  }
};

// 이미지 정리
export const cleanupImages = async (retentionDays = 90) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/images/cleanup?retention_days=${retentionDays}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("이미지 정리 실패:", error);
    throw error;
  }
};

// 사용자 정의 알림 발송
export const sendCustomNotification = async (notification) => {
  try {
    const params = new URLSearchParams();
    params.append("title", notification.title);
    params.append("message", notification.message);
    params.append("level", notification.level || "medium");

    if (notification.channels && notification.channels.length > 0) {
      notification.channels.forEach((channel) => {
        params.append("channels", channel);
      });
    }

    const response = await fetch(
      `${BASE_URL}/api/quality/notifications/send?${params}`,
      {
        method: "POST",
      }
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("사용자 정의 알림 발송 실패:", error);
    throw error;
  }
};

// 알림 히스토리 조회
export const getNotificationHistory = async (limit = 100) => {
  try {
    const response = await fetch(
      `${BASE_URL}/api/quality/notifications/history?limit=${limit}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("알림 히스토리 조회 실패:", error);
    throw error;
  }
};

// 서비스 상태 체크
export const getHealthStatus = async () => {
  try {
    const response = await fetch(`${BASE_URL}/api/quality/health`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("서비스 상태 체크 실패:", error);
    throw error;
  }
};

// 품질 업데이트 WebSocket 구독
export const subscribeQualityUpdates = (callback) => {
  const ws = new WebSocket(`ws://localhost:8000/ws/quality`); // 품질 전용 WebSocket

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("[WebSocket] 메시지 수신:", data);

      // 기존 메시지 타입들
      if (data.type === "status") {
        callback(data);
      } else if (data.type === "metric_update") {
        callback(data);
      } else if (data.type === "evaluation_complete") {
        // 평가 완료 알림 - 검색 결과 자동 업데이트
        callback(data);
      }
    } catch (error) {
      console.error("[WebSocket] 메시지 파싱 오류:", error);
    }
  };

  ws.onerror = (error) => {
    console.error("품질 업데이트 WebSocket 오류:", error);
  };

  ws.onclose = () => {
    console.log("품질 업데이트 WebSocket 연결 종료");
  };

  ws.onopen = () => {
    console.log("품질 업데이트 WebSocket 연결 성공");
  };

  // 연결 종료 함수 반환
  return () => {
    ws.close();
  };
};

// 통합 API 객체
export const metricsApi = {
  // 기존 API
  getMetrics,
  postKeyword,
  subscribeMetrics,

  // Quality Dashboard API
  getKeywordQuality,
  getTrendData,
  getKeywordAnalysis,
  startBatchJob,
  getBatchStatus,
  getTrendSummary,
  getImageMetadata,
  getStorageStats,
  cleanupImages,
  sendCustomNotification,
  getNotificationHistory,
  getHealthStatus,
  subscribeQualityUpdates,
};
