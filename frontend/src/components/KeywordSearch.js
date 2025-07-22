import React, { useEffect, useState } from "react";
import {
  Input,
  Button,
  Card,
  Typography,
  Space,
  Alert,
  Progress,
  Breadcrumb,
  Divider,
} from "antd";
import {
  SearchOutlined,
  ReloadOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import {
  getMetrics,
  subscribeMetrics,
  postKeyword,
} from "../services/metricsApi";
import MetricsTable from "./MetricsTable";
import ScreenshotModal from "./ScreenshotModal";

const { Title, Text } = Typography;

function KeywordSearch({ showEvaluatorConfig, setShowEvaluatorConfig }) {
  const [metrics, setMetrics] = useState({});
  const [timestamp, setTimestamp] = useState("");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusUpdates, setStatusUpdates] = useState({});
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    // 최초 데이터 fetch
    getMetrics()
      .then((res) => {
        console.log("초기 메트릭 데이터:", res);
        setMetrics(res.metrics || {});
        setTimestamp(res.timestamp || new Date().toLocaleString());
      })
      .catch((error) => {
        console.error("초기 메트릭 로딩 실패:", error);
      });

    // WebSocket 구독 - 실시간 업데이트
    const ws = subscribeMetrics((data) => {
      console.log("WebSocket 업데이트 수신:", data);
      console.log("현재 metrics 상태:", metrics);

      if (data.type === "status") {
        // 상태 업데이트 처리
        setStatusUpdates((prev) => ({
          ...prev,
          [data.keyword]: {
            status: data.status,
            step: data.step,
            total_steps: data.total_steps,
            timestamp: data.timestamp,
          },
        }));
        // 완료 또는 실패 시 입력 가능하게
        if (data.status.includes("완료") || data.status.includes("실패")) {
          setLoading(false);
        }
      } else if (data.type === "metric_update") {
        // 개별 메트릭 실시간 업데이트 - 새로운 구조 처리
        console.log("metric_update 수신:", data.keyword, data.metrics);
        console.log("업데이트 전 metrics:", metrics);

        setMetrics((prev) => {
          const newMetrics = { ...prev };
          newMetrics[data.keyword] = data.metrics; // 전체 데이터로 교체
          console.log("업데이트 후 metrics:", newMetrics);
          return newMetrics;
        });

        // 메트릭 업데이트 완료 시 상태 업데이트 제거 및 로딩 해제
        setStatusUpdates((prev) => {
          const newStatus = { ...prev };
          delete newStatus[data.keyword];
          return newStatus;
        });
        setLoading(false);

        // 타임스탬프 업데이트
        setTimestamp(new Date().toLocaleString());
      } else if (data.type === "evaluation_complete") {
        // 평가 완료 알림 - 검색 결과 자동 업데이트
        console.log("평가 완료 알림 수신:", data.keyword, data.summary);

        // 최신 메트릭 데이터 다시 가져오기
        getMetrics()
          .then((res) => {
            console.log("평가 완료 후 메트릭 업데이트:", res);
            setMetrics(res.metrics || {});
            setTimestamp(res.timestamp || new Date().toLocaleString());
          })
          .catch((error) => {
            console.error("평가 완료 후 메트릭 업데이트 실패:", error);
          });

        // 상태 업데이트 제거 및 로딩 해제
        setStatusUpdates((prev) => {
          const newStatus = { ...prev };
          delete newStatus[data.keyword];
          return newStatus;
        });
        setLoading(false);

        console.log(
          `[자동 업데이트] ${data.keyword} 평가 완료 - 검색 결과가 자동으로 업데이트되었습니다.`
        );
      } else {
        // 초기 또는 전체 업데이트
        console.log("전체 메트릭 업데이트:", data);
        setMetrics(data.metrics || {});
        if (data.timestamp) {
          setTimestamp(data.timestamp);
        }
      }
    });

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    setError("");

    try {
      const response = await postKeyword(input);
      console.log("키워드 요청 완료:", response);

      // 상태 업데이트 초기화
      setStatusUpdates({
        [input]: {
          status: "요청 처리 시작",
          step: 0,
          total_steps: 5,
          timestamp: new Date().toISOString(),
        },
      });
    } catch (err) {
      console.error("키워드 요청 실패:", err);
      setError("키워드 요청에 실패했습니다. 다시 시도해주세요.");
      setLoading(false);
    }
  };

  const handleScreenshotClick = (screenshot) => {
    setSelectedScreenshot(screenshot);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedScreenshot(null);
  };

  // 데이터 새로고침
  const handleRefresh = () => {
    getMetrics().then((res) => {
      setMetrics((prev) => ({ ...prev, ...res.data }));
      setTimestamp(res.timestamp);
    });
  };

  return (
    <div className="min-h-[calc(100vh-52px)]">
      <div className="bg-white border-b border-gray-200 px-8 py-6">
        {/* Breadcrumb */}
        <Breadcrumb
          className="mb-4"
          items={[
            {
              title: "검색품질 모니터링",
            },
            {
              title: "키워드 검색",
            },
          ]}
        />

        {/* 페이지 제목 */}
        <Title level={1} className="typo-heading-1 mb-0">
          키워드 품질 상세
        </Title>
        <Text className="text-gray-600">
          키워드별 검색 품질을 실시간으로 분석합니다
        </Text>
      </div>

      <div className="p-8 max-w-[1400px] mx-auto">
        {/* 검색 섹션 */}
        <Card className="mb-10 shadow-md">
          <Title level={3} className="typo-heading-3 mb-6">
            검색 테스트
          </Title>

          <div className="flex gap-3 mb-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="키워드를 입력하세요 (예: 반팔티, 청바지, 운동화)"
              size="large"
              disabled={loading}
              onPressEnter={handleSubmit}
              className="flex-1"
            />
            <Button
              type="primary"
              size="large"
              icon={<SearchOutlined />}
              loading={loading}
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="px-6"
            >
              {loading ? "처리중" : "검색"}
            </Button>
            <Button
              size="large"
              icon={<SettingOutlined />}
              onClick={() => setShowEvaluatorConfig(true)}
              className="px-4"
              title="다중 평가 시스템 설정"
            >
              평가 설정
            </Button>
          </div>

          {error && (
            <Alert
              message={error}
              type="error"
              showIcon
              className="mb-4"
              closable
            />
          )}
        </Card>

        {/* 진행 상황 표시 */}
        {Object.keys(statusUpdates).length > 0 && (
          <Card className="mb-10 shadow-md">
            <Title level={3} className="typo-heading-3 mb-6">
              🔄 실시간 처리 현황
            </Title>

            <Space direction="vertical" className="w-full" size="large">
              {Object.entries(statusUpdates).map(([keyword, status]) => {
                const progress = Math.round(
                  (status.step / status.total_steps) * 100
                );
                const isCompleted = status.step === status.total_steps;
                const isError =
                  status.status.includes("실패") ||
                  status.status.includes("오류");

                return (
                  <div
                    key={keyword}
                    className={`p-5 rounded-lg border-2 transition-all duration-300 ${
                      isCompleted
                        ? "bg-green-50 border-green-200"
                        : isError
                        ? "bg-red-50 border-red-200"
                        : "bg-blue-50 border-blue-200"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-4">
                      <div className="flex items-center gap-3">
                        <Text strong className="text-lg text-gray-900">
                          📊 {keyword}
                        </Text>
                        {isCompleted && (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                            ✅ 완료
                          </span>
                        )}
                        {isError && (
                          <span className="px-2 py-1 bg-red-100 text-red-700 text-xs font-medium rounded-full">
                            ❌ 오류
                          </span>
                        )}
                      </div>
                      <Text className="text-sm text-gray-500">
                        {new Date(status.timestamp).toLocaleTimeString()}
                      </Text>
                    </div>

                    <div className="mb-3">
                      <Text className="text-sm font-medium text-gray-700 mb-2 block">
                        현재 단계: {status.status}
                      </Text>
                      <Progress
                        percent={progress}
                        status={
                          isError
                            ? "exception"
                            : isCompleted
                            ? "success"
                            : "active"
                        }
                        showInfo={true}
                        format={(percent) => (
                          <span className="text-sm font-medium">
                            {percent}% ({status.step}/{status.total_steps})
                          </span>
                        )}
                        strokeColor={
                          isError
                            ? "#ff4d4f"
                            : isCompleted
                            ? "#52c41a"
                            : {
                                "0%": "#1677ff",
                                "50%": "#40a9ff",
                                "100%": "#52c41a",
                              }
                        }
                        trailColor={isError ? "#ffccc7" : "#f0f0f0"}
                        strokeWidth={8}
                        className="mb-2"
                      />
                    </div>

                    {/* 단계별 세부 정보 */}
                    <div className="grid grid-cols-4 gap-2 text-xs">
                      {["API 수집", "스크린샷", "무신사 평가", "29CM 평가"].map(
                        (stepName, index) => {
                          const stepNumber = Math.floor((index + 1) * 2);
                          const isStepCompleted = status.step >= stepNumber;
                          const isStepCurrent =
                            status.step === stepNumber ||
                            status.step === stepNumber - 1;

                          return (
                            <div
                              key={stepName}
                              className={`p-2 rounded text-center transition-colors ${
                                isStepCompleted
                                  ? "bg-green-100 text-green-700"
                                  : isStepCurrent
                                  ? "bg-blue-100 text-blue-700 animate-pulse"
                                  : "bg-gray-100 text-gray-500"
                              }`}
                            >
                              {isStepCompleted
                                ? "✅"
                                : isStepCurrent
                                ? "⏳"
                                : "⏸️"}{" "}
                              {stepName}
                            </div>
                          );
                        }
                      )}
                    </div>
                  </div>
                );
              })}
            </Space>
          </Card>
        )}

        {/* 검색 결과 */}
        <Card className="mb-10 shadow-md">
          <div className="flex justify-between items-center mb-6">
            <Title level={3} className="typo-heading-3 mb-0">
              검색 결과
            </Title>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              className="flex items-center gap-2"
            >
              새로고침
            </Button>
          </div>

          <div className="mb-4">
            <Text className="text-sm text-gray-600">
              {Object.keys(metrics).length > 0
                ? `${
                    Object.keys(metrics).length
                  }개의 키워드 • 최종 갱신: ${timestamp}`
                : `최종 갱신: ${timestamp}`}
            </Text>
          </div>

          <Divider className="my-4" />

          {Object.keys(metrics).length === 0 ? (
            <div className="text-center py-16">
              <div className="text-6xl mb-4 text-gray-300">📊</div>
              <Title level={4} className="text-gray-500 mb-2">
                검색 결과가 없습니다
              </Title>
              <Text className="text-gray-400">
                키워드를 입력하여 검색을 시작하세요
              </Text>
            </div>
          ) : (
            <MetricsTable
              metrics={metrics}
              onScreenshotClick={handleScreenshotClick}
            />
          )}
        </Card>

        {isModalOpen && selectedScreenshot && (
          <ScreenshotModal
            screenshot={selectedScreenshot}
            onClose={closeModal}
          />
        )}
      </div>
    </div>
  );
}

export default KeywordSearch;
