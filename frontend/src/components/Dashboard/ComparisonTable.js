import React, { useState } from "react";
import {
  Table,
  Tag,
  Button,
  Typography,
  Space,
  Modal,
  Card,
  Badge,
  Tooltip,
  Image,
  Divider,
  Empty,
} from "antd";
import { EyeOutlined, PictureOutlined } from "@ant-design/icons";
import { safeToFixed, safeToPercent, safeNumber } from "../../utils/formatters";

const { Text, Title } = Typography;
const BACKEND_URL = "http://localhost:8000";

const ComparisonTable = ({
  data,
  onKeywordSelect,
  getQualityGrade,
  filters,
}) => {
  const [selectedAnalysis, setSelectedAnalysis] = useState(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [showScreenshotModal, setShowScreenshotModal] = useState(false);
  const [selectedScreenshot, setSelectedScreenshot] = useState(null);

  // 플랫폼 뱃지
  const getPlatformBadge = (platform) => {
    const platformMap = {
      musinsa: { label: "무신사", color: "blue" },
      "29cm": { label: "29CM", color: "red" },
      all: { label: "전체", color: "default" },
    };
    const platformInfo = platformMap[platform] || {
      label: platform,
      color: "default",
    };

    return <Tag color={platformInfo.color}>{platformInfo.label}</Tag>;
  };

  // 점수 뱃지
  const getScoreBadge = (score, type) => {
    // score가 undefined이거나 null인 경우 처리
    if (score === undefined || score === null || isNaN(score)) {
      return <Tag color="default">-</Tag>;
    }

    const grade = getQualityGrade(score);
    let color = "default";
    if (grade === "excellent") color = "green";
    else if (grade === "good") color = "blue";
    else if (grade === "average") color = "orange";
    else if (grade === "below-average") color = "red";
    else if (grade === "poor") color = "red";

    return <Tag color={color}>{score.toFixed(3)}</Tag>;
  };

  // 신뢰도 색상 계산
  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return "#52c41a";
    if (confidence >= 0.6) return "#1890ff";
    if (confidence >= 0.4) return "#faad14";
    return "#f5222d";
  };

  // 평가 방법 뱃지
  const getEvaluationMethodBadge = (method, confidence) => {
    const color = getConfidenceColor(confidence);
    const methodNames = {
      Composite: "종합",
      "LLM-gpt-4o": "GPT-4",
      "Rule-Based": "규칙",
      "Keyword-Based": "키워드",
      "Embedding-sentence-transformers": "임베딩",
    };

    return (
      <Badge
        color={color}
        text={methodNames[method] || method}
        style={{ fontSize: "12px" }}
      />
    );
  };

  // 분석 상세 보기
  const handleAnalysisClick = (keyword, platform, data) => {
    // precision_issues JSON 파싱 처리
    let precision_issues = [];
    if (data.precision_issues) {
      if (typeof data.precision_issues === "string") {
        try {
          precision_issues = JSON.parse(data.precision_issues);
        } catch (e) {
          console.warn("precision_issues JSON 파싱 실패:", e);
          precision_issues = [];
        }
      } else if (Array.isArray(data.precision_issues)) {
        precision_issues = data.precision_issues;
      }
    }

    setSelectedAnalysis({
      keyword,
      platform,
      data,
      precision_issues,
    });
    setShowAnalysisModal(true);
  };

  const closeAnalysisModal = () => {
    setShowAnalysisModal(false);
    setSelectedAnalysis(null);
  };

  // 스크린샷 처리
  const handleScreenshotClick = (screenshotPath) => {
    if (screenshotPath && screenshotPath !== "N/A") {
      const imageUrl = screenshotPath.startsWith("http")
        ? screenshotPath
        : `${BACKEND_URL}${screenshotPath}`;
      setSelectedScreenshot(imageUrl);
      setShowScreenshotModal(true);
    }
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: "평가일",
      dataIndex: "assessment_date",
      key: "assessment_date",
      width: 100,
      render: (date) => {
        if (!date) return <Text type="secondary">-</Text>;
        return <Text className="text-sm">{date}</Text>;
      },
      sorter: (a, b) =>
        new Date(a.assessment_date || 0) - new Date(b.assessment_date || 0),
    },
    {
      title: "키워드",
      dataIndex: "keyword",
      key: "keyword",
      width: 120,
      render: (text) => (
        <Text strong className="text-gray-900">
          {text}
        </Text>
      ),
    },
    {
      title: "플랫폼",
      dataIndex: "platform",
      key: "platform",
      width: 80,
      render: (platform) => getPlatformBadge(platform),
    },
    {
      title: "NDCG@10",
      dataIndex: "ndcg_score",
      key: "ndcg_score",
      width: 100,
      render: (score) => getScoreBadge(score, "ndcg"),
      sorter: (a, b) => (a.ndcg_score || 0) - (b.ndcg_score || 0),
    },
    {
      title: "Precision",
      dataIndex: "precision",
      key: "precision",
      width: 100,
      render: (score) => getScoreBadge(score, "precision"),
      sorter: (a, b) => (a.precision || 0) - (b.precision || 0),
    },
    {
      title: "Recall",
      dataIndex: "recall",
      key: "recall",
      width: 100,
      render: (score) => getScoreBadge(score, "recall"),
      sorter: (a, b) => (a.recall || 0) - (b.recall || 0),
    },
    {
      title: "평가방법",
      dataIndex: "evaluation_method",
      key: "evaluation_method",
      width: 100,
      render: (method, record) =>
        getEvaluationMethodBadge(method, record.confidence || 0),
    },
    {
      title: "신뢰도",
      dataIndex: "confidence",
      key: "confidence",
      width: 90,
      render: (confidence) => {
        if (confidence === undefined || confidence === null) {
          return <Text type="secondary">-</Text>;
        }
        const color = getConfidenceColor(confidence);
        return (
          <Text style={{ color, fontWeight: "bold" }}>
            {(confidence * 100).toFixed(0)}%
          </Text>
        );
      },
      sorter: (a, b) => (a.confidence || 0) - (b.confidence || 0),
    },
    {
      title: "스크린샷",
      dataIndex: "screenshot_path",
      key: "screenshot_path",
      width: 100,
      render: (screenshot) => {
        if (!screenshot || screenshot === "N/A") {
          return <Text type="secondary">없음</Text>;
        }
        return (
          <Button
            type="link"
            icon={<PictureOutlined />}
            onClick={() => handleScreenshotClick(screenshot)}
            size="small"
          >
            보기
          </Button>
        );
      },
    },
    {
      title: "문제상품",
      dataIndex: "precision_issues",
      key: "precision_issues",
      width: 100,
      render: (issues, record) => {
        let issueCount = 0;

        // precision_issues가 문자열인 경우 JSON 파싱 시도
        if (typeof issues === "string") {
          try {
            const parsedIssues = JSON.parse(issues);
            issueCount = Array.isArray(parsedIssues) ? parsedIssues.length : 0;
          } catch (e) {
            issueCount = 0;
          }
        } else if (Array.isArray(issues)) {
          issueCount = issues.length;
        }

        if (issueCount === 0) {
          return <Text type="secondary">없음</Text>;
        }

        return (
          <Button
            type="link"
            size="small"
            onClick={() =>
              handleAnalysisClick(record.keyword, record.platform, record)
            }
          >
            {issueCount}개
          </Button>
        );
      },
    },
    {
      title: "작업",
      key: "actions",
      width: 80,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="상세 분석">
            <Button
              type="text"
              icon={<EyeOutlined />}
              size="small"
              onClick={() =>
                handleAnalysisClick(record.keyword, record.platform, record)
              }
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  if (!data || data.length === 0) {
    return <Empty description="키워드 데이터가 없습니다" />;
  }

  return (
    <>
      <Table
        dataSource={data}
        columns={columns}
        rowKey={(record) => `${record.keyword}-${record.platform}-${record.id}`}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) =>
            `${range[0]}-${range[1]} / 총 ${total}개`,
        }}
        scroll={{ x: 1200 }}
        size="small"
        onRow={(record) => ({
          onClick: () =>
            handleAnalysisClick(record.keyword, record.platform, record),
          style: { cursor: "pointer" },
          className: "hover:bg-blue-50 transition-colors duration-200",
        })}
        rowClassName={(record, index) =>
          `hover:bg-blue-50 transition-colors duration-200 ${
            index % 2 === 0 ? "bg-gray-50" : "bg-white"
          }`
        }
      />

      {/* 분석 상세 모달 */}
      <Modal
        title={
          selectedAnalysis ? (
            <div className="flex items-center gap-2">
              <Text strong className="text-lg">
                {selectedAnalysis.keyword} - {selectedAnalysis.platform}
              </Text>
              {selectedAnalysis.data?.evaluation_method &&
                getEvaluationMethodBadge(
                  selectedAnalysis.data.evaluation_method,
                  selectedAnalysis.data.confidence || 0
                )}
            </div>
          ) : (
            "상세 분석"
          )
        }
        open={showAnalysisModal}
        onCancel={closeAnalysisModal}
        footer={[
          <Button key="close" onClick={closeAnalysisModal}>
            닫기
          </Button>,
        ]}
        width={900}
        className="analysis-detail-modal"
      >
        {selectedAnalysis && (
          <div className="space-y-6">
            {/* 기본 정보 카드 */}
            <Card size="small" className="border-l-4 border-l-blue-500">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <Text className="text-xs text-gray-500 block">평가일</Text>
                  <Text strong className="text-sm">
                    {selectedAnalysis.data.assessment_date || "실시간"}
                  </Text>
                </div>
                <div>
                  <Text className="text-xs text-gray-500 block">처리시간</Text>
                  <Text strong className="text-sm">
                    {selectedAnalysis.data.processing_time
                      ? `${selectedAnalysis.data.processing_time.toFixed(1)}초`
                      : "-"}
                  </Text>
                </div>
                <div>
                  <Text className="text-xs text-gray-500 block">
                    API 결과수
                  </Text>
                  <Text strong className="text-sm">
                    {selectedAnalysis.data.api_total_results || 0}개
                  </Text>
                </div>
                <div>
                  <Text className="text-xs text-gray-500 block">신뢰도</Text>
                  <Text
                    strong
                    className="text-sm"
                    style={{
                      color: getConfidenceColor(
                        selectedAnalysis.data.confidence || 0
                      ),
                    }}
                  >
                    {((selectedAnalysis.data.confidence || 0) * 100).toFixed(0)}
                    %
                  </Text>
                </div>
              </div>
            </Card>

            {/* 점수 요약 */}
            <Card
              size="small"
              title="평가 점수"
              className="border-l-4 border-l-green-500"
            >
              <div className="grid grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600 mb-1">
                    {safeToFixed(selectedAnalysis.data.ndcg_score || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">NDCG@10</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {getQualityGrade(selectedAnalysis.data.ndcg_score || 0) ===
                    "excellent"
                      ? "우수"
                      : getQualityGrade(
                          selectedAnalysis.data.ndcg_score || 0
                        ) === "good"
                      ? "양호"
                      : getQualityGrade(
                          selectedAnalysis.data.ndcg_score || 0
                        ) === "average"
                      ? "보통"
                      : getQualityGrade(
                          selectedAnalysis.data.ndcg_score || 0
                        ) === "below-average"
                      ? "미흡"
                      : "부족"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600 mb-1">
                    {safeToFixed(selectedAnalysis.data.precision || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">Precision</div>
                  <div className="text-xs text-gray-400 mt-1">정확도</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-purple-600 mb-1">
                    {safeToFixed(selectedAnalysis.data.recall || 0, 3)}
                  </div>
                  <div className="text-sm text-gray-500">Recall</div>
                  <div className="text-xs text-gray-400 mt-1">재현율</div>
                </div>
              </div>
            </Card>

            {/* 평가 방법 및 상세 정보 */}
            {selectedAnalysis.data.evaluation_details && (
              <Card
                size="small"
                title="평가 상세 정보"
                className="border-l-4 border-l-orange-500"
              >
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Text strong className="text-sm">
                      평가 방법:
                    </Text>
                    <Text className="text-sm">
                      {selectedAnalysis.data.evaluation_method}
                    </Text>
                  </div>
                  {selectedAnalysis.data.evaluation_details.model && (
                    <div className="flex items-center gap-2">
                      <Text strong className="text-sm">
                        사용 모델:
                      </Text>
                      <Text className="text-sm">
                        {selectedAnalysis.data.evaluation_details.model}
                      </Text>
                    </div>
                  )}
                  {selectedAnalysis.data.evaluation_details.reasoning && (
                    <div>
                      <Text strong className="text-sm block mb-1">
                        평가 근거:
                      </Text>
                      <Text className="text-sm text-gray-600 bg-gray-50 p-2 rounded">
                        {selectedAnalysis.data.evaluation_details.reasoning}
                      </Text>
                    </div>
                  )}
                  {selectedAnalysis.data.evaluation_details.total_products && (
                    <div className="flex items-center gap-2">
                      <Text strong className="text-sm">
                        평가 상품수:
                      </Text>
                      <Text className="text-sm">
                        {
                          selectedAnalysis.data.evaluation_details
                            .total_products
                        }
                        개
                      </Text>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* 평가 이유 */}
            {(selectedAnalysis.data.ndcg_reason ||
              selectedAnalysis.data.precision_reason ||
              selectedAnalysis.data.recall_reason) && (
              <Card
                size="small"
                title="평가 이유"
                className="border-l-4 border-l-indigo-500"
              >
                <div className="space-y-3">
                  {selectedAnalysis.data.ndcg_reason && (
                    <div className="p-3 bg-blue-50 rounded">
                      <Text strong className="text-blue-700 block mb-1">
                        NDCG@10 평가:
                      </Text>
                      <Text className="text-sm text-blue-600">
                        {selectedAnalysis.data.ndcg_reason}
                      </Text>
                    </div>
                  )}
                  {selectedAnalysis.data.precision_reason && (
                    <div className="p-3 bg-green-50 rounded">
                      <Text strong className="text-green-700 block mb-1">
                        Precision 평가:
                      </Text>
                      <Text className="text-sm text-green-600">
                        {selectedAnalysis.data.precision_reason}
                      </Text>
                    </div>
                  )}
                  {selectedAnalysis.data.recall_reason && (
                    <div className="p-3 bg-purple-50 rounded">
                      <Text strong className="text-purple-700 block mb-1">
                        Recall 평가:
                      </Text>
                      <Text className="text-sm text-purple-600">
                        {selectedAnalysis.data.recall_reason}
                      </Text>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* 스크린샷 표시 */}
            {selectedAnalysis.data.screenshot_path && (
              <Card
                size="small"
                title="검색 결과 스크린샷"
                className="border-l-4 border-l-gray-500"
              >
                <div className="text-center">
                  <Image
                    src={`${BACKEND_URL}${selectedAnalysis.data.screenshot_path}`}
                    alt={`${selectedAnalysis.keyword} ${selectedAnalysis.platform} 스크린샷`}
                    className="rounded border border-gray-200 max-w-full"
                    style={{ maxHeight: "400px" }}
                    preview={{
                      mask: (
                        <div className="text-white">
                          <PictureOutlined className="text-2xl mb-2" />
                          <div>클릭하여 확대</div>
                        </div>
                      ),
                    }}
                  />
                  <Text className="text-xs text-gray-500 block mt-2">
                    {selectedAnalysis.platform === "musinsa"
                      ? "무신사"
                      : "29CM"}{" "}
                    검색 결과 화면
                  </Text>
                </div>
              </Card>
            )}

            {/* 문제 상품 목록 */}
            {selectedAnalysis?.precision_issues &&
              selectedAnalysis.precision_issues.length > 0 && (
                <Card className="border-l-4 border-l-red-500">
                  <div className="flex items-center justify-between mb-4">
                    <Title level={5} className="mb-0">
                      🚨 문제 상품 목록
                    </Title>
                    <Badge
                      count={selectedAnalysis.precision_issues.length}
                      style={{ backgroundColor: "#ff4d4f" }}
                    />
                  </div>
                  <div className="space-y-4">
                    {selectedAnalysis.precision_issues.map((issue, idx) => (
                      <Card
                        key={idx}
                        size="small"
                        className="border-l-4 border-l-red-400 bg-red-50"
                      >
                        <div className="flex items-start space-x-4">
                          {issue.image_url && issue.image_url !== "N/A" && (
                            <div className="flex-shrink-0">
                              <Image
                                src={issue.image_url}
                                alt={issue.goods_name}
                                width={80}
                                height={80}
                                className="rounded object-cover border border-gray-300"
                                fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
                              />
                            </div>
                          )}
                          <div className="flex-1">
                            <div className="mb-2">
                              <Text strong className="text-base text-gray-900">
                                {issue.goods_name}
                              </Text>
                              <br />
                              <Text className="text-xs text-gray-500">
                                상품번호: {issue.goods_no}
                              </Text>
                            </div>
                            <div className="p-3 bg-white border border-red-200 rounded">
                              <div className="flex items-start">
                                <span className="text-red-500 mr-2 mt-0.5">
                                  ⚠️
                                </span>
                                <Text className="text-sm text-red-700 font-medium flex-1">
                                  {issue.reason}
                                </Text>
                              </div>
                            </div>

                            {/* 상세 평가기별 이유 표시 */}
                            {issue.detailed_reasons &&
                              issue.detailed_reasons.length > 0 && (
                                <div className="mt-3 p-3 bg-white border border-orange-200 rounded">
                                  <div className="flex items-center mb-2">
                                    <Text
                                      strong
                                      className="text-orange-700 text-sm"
                                    >
                                      📋 상세 평가 내용
                                    </Text>
                                    {issue.detailed_reasons.length > 1 && (
                                      <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-700 text-xs rounded-full">
                                        {issue.detailed_reasons.length}개 평가기
                                      </span>
                                    )}
                                  </div>
                                  <div className="space-y-1">
                                    {issue.detailed_reasons.map(
                                      (detail, detailIdx) => (
                                        <div
                                          key={detailIdx}
                                          className="flex items-start text-orange-700 text-xs"
                                        >
                                          <span className="text-orange-500 mr-1">
                                            ▪
                                          </span>
                                          <span className="flex-1">
                                            {detail.replace("• ", "")}
                                          </span>
                                        </div>
                                      )
                                    )}
                                  </div>

                                  {/* 다중 평가기인 경우 추가 설명 */}
                                  {issue.detailed_reasons.length > 1 && (
                                    <div className="mt-2 pt-2 border-t border-orange-200">
                                      <Text className="text-xs text-orange-600">
                                        💡 여러 평가기에서 동일한 문제를
                                        발견했습니다.
                                      </Text>
                                    </div>
                                  )}
                                </div>
                              )}
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>

                  {/* 문제 상품 요약 */}
                  <div className="mt-4 p-3 bg-red-100 border border-red-200 rounded">
                    <div className="flex items-center">
                      <span className="text-red-600 mr-2">📊</span>
                      <Text className="text-sm text-red-700">
                        <strong>
                          총 {selectedAnalysis.precision_issues.length}개 상품
                        </strong>
                        에서 품질 문제가 발견되었습니다. 정확도 개선을 위해
                        검토가 필요합니다.
                      </Text>
                    </div>
                  </div>
                </Card>
              )}

            {/* 문제 상품이 없는 경우 */}
            {(!selectedAnalysis?.precision_issues ||
              selectedAnalysis.precision_issues.length === 0) && (
              <Card className="border-l-4 border-l-green-500">
                <div className="text-center py-4">
                  <div className="text-4xl mb-2">✅</div>
                  <Title level={5} className="text-green-600 mb-2">
                    품질 문제 없음
                  </Title>
                  <Text className="text-green-600">
                    이 키워드의 검색 결과에서 특별한 품질 문제가 발견되지
                    않았습니다.
                  </Text>
                </div>
              </Card>
            )}
          </div>
        )}
      </Modal>

      {/* 스크린샷 모달 */}
      <Modal
        title="스크린샷 상세보기"
        open={showScreenshotModal}
        onCancel={() => setShowScreenshotModal(false)}
        footer={null}
        width={1000}
        centered
      >
        {selectedScreenshot && (
          <div className="text-center">
            <Image
              src={selectedScreenshot}
              alt="스크린샷"
              className="max-w-full"
              style={{ maxHeight: "70vh" }}
            />
          </div>
        )}
      </Modal>
    </>
  );
};

export default ComparisonTable;
