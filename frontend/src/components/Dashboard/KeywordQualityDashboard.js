import React, { useState, useEffect, useCallback } from "react";
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Space,
  Drawer,
  Typography,
  Breadcrumb,
  Spin,
  Alert,
  Divider,
  Empty,
} from "antd";
import {
  FilterOutlined,
  ReloadOutlined,
  DownloadOutlined,
  DashboardOutlined,
  RiseOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { metricsApi } from "../../services/metricsApi";
import QualityMetricsCard from "./QualityMetricsCard";
import TrendChart from "./TrendChart";
import ComparisonTable from "./ComparisonTable";
import FilterPanel from "./FilterPanel";

const { Title, Text } = Typography;

const KeywordQualityDashboard = () => {
  const [qualityData, setQualityData] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [summaryStats, setSummaryStats] = useState({
    totalKeywords: 0,
    avgNdcgScore: 0,
    avgPrecision: 0,
    avgRecall: 0,
    anomalyCount: 0,
    lastUpdated: null,
  });
  const [filters, setFilters] = useState({
    platform: "all",
    category: "all",
    dateRange: "7d",
    threshold: 0.5,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedKeyword, setSelectedKeyword] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 품질 데이터 조회
  const fetchQualityData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await metricsApi.getKeywordQuality({
        platform: filters.platform,
        category: filters.category,
        dateRange: filters.dateRange,
        threshold: filters.threshold,
        sortBy: "ndcg_score",
        sortDirection: "desc",
        page: 1,
        limit: 1000,
      });

      if (response.success) {
        setQualityData(response.data);
        setSummaryStats(response.summary);
      } else {
        setError(response.message || "데이터 로드 실패");
      }
    } catch (error) {
      console.error("품질 데이터 조회 실패:", error);

      // 더 상세한 에러 메시지 제공
      let errorMessage = "알 수 없는 오류가 발생했습니다.";

      if (error.message.includes("Failed to fetch")) {
        errorMessage =
          "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.";
      } else if (error.message.includes("NetworkError")) {
        errorMessage = "네트워크 연결에 문제가 있습니다.";
      } else if (error.message.includes("HTTP error")) {
        errorMessage = `서버 오류가 발생했습니다: ${error.message}`;
      } else if (error.name === "TypeError") {
        errorMessage = "데이터 형식에 문제가 있습니다.";
      } else {
        errorMessage = `오류: ${error.message}`;
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 트렌드 데이터 조회
  const fetchTrendData = useCallback(async () => {
    try {
      const response = await metricsApi.getTrendData({
        platform: filters.platform,
        dateRange: filters.dateRange,
      });

      if (response.success) {
        setTrendData(response.data);
      } else {
        console.warn("트렌드 데이터 로드 실패:", response.message);
      }
    } catch (error) {
      console.error("트렌드 데이터 조회 실패:", error);
      // 트렌드 데이터는 선택적이므로 에러 상태를 설정하지 않음
      setTrendData([]);
    }
  }, [filters]);

  // 초기 데이터 로드
  useEffect(() => {
    fetchQualityData();
    fetchTrendData();
  }, [fetchQualityData, fetchTrendData]);

  // 필터 변경 핸들러
  const handleFilterChange = (newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  // 키워드 선택 핸들러
  const handleKeywordSelect = (keyword) => {
    setSelectedKeyword(keyword);
  };

  // 품질 등급 계산
  const getQualityGrade = (score) => {
    if (score >= 0.9) return "excellent";
    if (score >= 0.8) return "good";
    if (score >= 0.7) return "average";
    if (score >= 0.6) return "below-average";
    return "poor";
  };

  // 데이터 새로고침
  const handleRefresh = () => {
    fetchQualityData();
    fetchTrendData();
  };

  // 데이터 내보내기
  const handleExport = () => {
    const csvContent = [
      [
        "키워드",
        "플랫폼",
        "카테고리",
        "NDCG 점수",
        "정확도",
        "재현율",
        "평가일자",
      ],
      ...qualityData.map((item) => [
        item.keyword,
        item.platform,
        item.category || "-",
        item.gpt_ndcg_score,
        item.gpt_precision,
        item.gpt_recall,
        item.assessment_date,
      ]),
    ]
      .map((row) => row.join(","))
      .join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `quality_data_${
      new Date().toISOString().split("T")[0]
    }.csv`;
    link.click();
  };

  // 드로어 토글 핸들러
  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
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
              title: "품질 대시보드",
            },
          ]}
        />

        {/* 페이지 헤더 */}
        <div className="flex justify-between items-center">
          <div>
            <Title level={1} className="typo-heading-1 mb-2">
              품질 대시보드
            </Title>
            <Text className="text-gray-600">검색 품질 모니터링 및 트렌드 분석</Text>
          </div>

          <Space>
            <Button icon={<FilterOutlined />} onClick={toggleDrawer}>
              필터
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleExport}>
              Export CSV
            </Button>
            <Button
              type="primary"
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
            >
              새로고침
            </Button>
          </Space>
        </div>
      </div>

      <div className="p-8 max-w-[1600px] mx-auto">

      {/* 에러 메시지 표시 */}
      {error && (
        <Alert
          message="데이터 로드 실패"
          description={
            <div>
              <p>{error}</p>
              <Button
                type="primary"
                size="small"
                onClick={handleRefresh}
                style={{ marginTop: 8 }}
              >
                다시 시도
              </Button>
            </div>
          }
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      {/* 로딩 상태 표시 */}
      {loading && (
        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <Spin size="large" tip="로딩중..." />
        </div>
      )}

      {/* 메트릭 카드 섹션 */}
      {!loading && !error && (
        <div className="mb-8">
          <Title level={3} className="typo-heading-3 mb-4">
            주요 지표
          </Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card>
                <Statistic
                  title="전체 키워드"
                  value={summaryStats.totalKeywords}
                  precision={0}
                  valueStyle={{ color: "#1677ff" }}
                  prefix={<DashboardOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card>
                <Statistic
                  title="평균 NDCG 점수"
                  value={summaryStats.avgNdcgScore}
                  precision={3}
                  valueStyle={{ color: "#52c41a" }}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card>
                <Statistic
                  title="평균 정확도"
                  value={summaryStats.avgPrecision}
                  precision={3}
                  valueStyle={{ color: "#1677ff" }}
                  prefix={<RiseOutlined />}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={8} lg={6}>
              <Card>
                <Statistic
                  title="이상치 발견"
                  value={summaryStats.anomalyCount}
                  precision={0}
                  valueStyle={{ color: "#ff4d4f" }}
                  prefix={<ExclamationCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>
        </div>
      )}

      {/* 트렌드 차트 및 키워드 테이블 섹션 */}
      {!loading && !error && (
        <>
          {/* 트렌드 차트 섹션 */}
          <Card className="mb-8">
            <Title level={3} className="typo-heading-3 mb-4">
              품질 트렌드
            </Title>
            {trendData && trendData.length > 0 ? (
              <TrendChart
                data={trendData}
                dateRange={filters.dateRange}
                platform={filters.platform}
              />
            ) : (
              <Empty description="트렌드 데이터가 없습니다" />
            )}
          </Card>

          {/* 키워드 테이블 섹션 */}
          <Card>
            <div className="flex justify-between items-center mb-4">
              <Title level={3} className="typo-heading-3 mb-0">
                키워드 품질 상세
              </Title>
            </div>
            <div className="mb-4">
              <Text className="text-sm text-gray-600">
                총 {summaryStats.totalKeywords}개의 키워드
              </Text>
            </div>
            <Divider className="my-4" />
            {qualityData && qualityData.length > 0 ? (
              <ComparisonTable
                data={qualityData}
                onKeywordSelect={handleKeywordSelect}
                getQualityGrade={getQualityGrade}
                filters={filters}
              />
            ) : (
              <Empty description="키워드 데이터가 없습니다" />
            )}
          </Card>
        </>
      )}

      {/* 필터 드로어 */}
        {/* 필터 드로어 */}
        <Drawer
          title="필터 설정"
          placement="right"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          width={400}
        >
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
        </Drawer>
      </div>
    </div>
  );
};

export default KeywordQualityDashboard;
