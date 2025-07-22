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
import { SearchOutlined, ReloadOutlined } from "@ant-design/icons";
import {
  getMetrics,
  subscribeMetrics,
  postKeyword,
} from "../services/metricsApi";
import MetricsTable from "./MetricsTable";
import ScreenshotModal from "./ScreenshotModal";

const { Title, Text } = Typography;

function KeywordSearch() {
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
    getMetrics().then((res) => {
      setMetrics((prev) => ({ ...prev, ...res.data }));
      setTimestamp(res.timestamp);
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

        setMetrics((prev) => {
          const newMetrics = { ...prev };
          newMetrics[data.keyword] = {
            ...newMetrics[data.keyword],
            ...data.metrics,
          };
          return newMetrics;
        });
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
        <Text className="text-gray-600">키워드별 검색 품질을 실시간으로 분석합니다</Text>
      </div>

             <div className="p-8 max-w-[1400px] mx-auto">

      {/* 검색 섹션 */}
      <Card className="mb-10 shadow-md">
        <Title level={3} className="typo-heading-3 mb-6">
          검색 테스트
        </Title>
        
        <Space.Compact className="w-full mb-4">
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
        </Space.Compact>

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
            진행 상황
          </Title>
          
          <Space direction="vertical" className="w-full" size="large">
            {Object.entries(statusUpdates).map(([keyword, status]) => (
              <div key={keyword} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <div className="flex justify-between items-center mb-3">
                  <Text strong className="text-gray-900">
                    {keyword}
                  </Text>
                  <Text className="text-sm text-gray-500 italic">
                    {status.status}
                  </Text>
                </div>
                <Progress
                  percent={Math.round((status.step / status.total_steps) * 100)}
                  status={status.step === status.total_steps ? "success" : "active"}
                  showInfo={true}
                  format={(percent) => `${percent}% (${status.step}/${status.total_steps})`}
                  strokeColor={{
                    '0%': '#1677ff',
                    '100%': '#52c41a',
                  }}
                  className="mb-0"
                />
              </div>
            ))}
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
              ? `${Object.keys(metrics).length}개의 키워드 • 최종 갱신: ${timestamp}`
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
          <ScreenshotModal screenshot={selectedScreenshot} onClose={closeModal} />
        )}
      </div>
    </div>
  );
}

export default KeywordSearch;
