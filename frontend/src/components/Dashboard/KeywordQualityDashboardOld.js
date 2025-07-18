import React, { useState, useEffect, useCallback } from "react";
import "./KeywordQualityDashboard.css";
import { metricsApi } from "../../services/metricsApi";
import QualityMetricsCard from "./QualityMetricsCard";
import TrendChart from "./TrendChart";
import ComparisonTable from "./ComparisonTable";
import FilterPanel from "./FilterPanel";

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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
      setError("네트워크 오류가 발생했습니다.");
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
      }
    } catch (error) {
      console.error("트렌드 데이터 조회 실패:", error);
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
        item.category,
        item.ndcg_score,
        item.precision,
        item.recall,
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

  // 사이드바 토글 핸들러
  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  if (loading) {
    return (
      <div className="admin-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>키워드 품질 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-page">
        <div className="error-container">
          <h2>오류 발생</h2>
          <p>{error}</p>
          <button onClick={handleRefresh} className="btn btn-primary">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-page">
      {/* Breadcrumb */}
      <nav className="breadcrumb">
        <span className="breadcrumb-item">검색품질 모니터링</span>
        <span className="breadcrumb-separator">&gt;</span>
        <span className="breadcrumb-item active">품질 대시보드</span>
      </nav>

      {/* 페이지 제목 */}
      <h1 className="page-title">Quality Dashboard</h1>

      {/* 액션 버튼들 */}
      <div className="page-actions">
        <button
          className="sidebar-toggle-btn"
          onClick={toggleSidebar}
          title={sidebarCollapsed ? "필터 패널 열기" : "필터 패널 닫기"}
        >
          {sidebarCollapsed ? "필터 표시" : "필터 숨기기"}
        </button>
        <div className="action-buttons">
          <button className="btn btn-sm" onClick={handleExport}>
            Export CSV
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleRefresh}>
            새로고침
          </button>
        </div>
      </div>

      <div className="dashboard-layout">
        {/* 사이드바 필터 패널 */}
        <div
          className={`dashboard-sidebar ${sidebarCollapsed ? "collapsed" : ""}`}
        >
          <FilterPanel
            filters={filters}
            onFilterChange={handleFilterChange}
            collapsed={sidebarCollapsed}
          />
        </div>

        {/* 메인 대시보드 콘텐츠 */}
        <div className={`dashboard-main ${sidebarCollapsed ? "expanded" : ""}`}>
          {/* 메트릭 카드 섹션 */}
          <div className="metrics-section">
            <h2 className="section-title">주요 지표</h2>
            <div className="metrics-grid">
              <QualityMetricsCard
                title="전체 키워드"
                value={summaryStats.totalKeywords}
                format="integer"
                color="#1976d2"
              />
              <QualityMetricsCard
                title="평균 NDCG 점수"
                value={summaryStats.avgNdcgScore}
                format="decimal"
                color="#388e3c"
              />
              <QualityMetricsCard
                title="이상치 발견"
                value={summaryStats.anomalyCount}
                format="integer"
                color="#d32f2f"
              />
            </div>
          </div>

          {/* 트렌드 차트 섹션 */}
          <div className="chart-section">
            <h2 className="section-title">품질 트렌드</h2>
            <TrendChart
              data={trendData}
              dateRange={filters.dateRange}
              platform={filters.platform}
            />
          </div>

          {/* 키워드 테이블 섹션 */}
          <div className="table-section">
            <h2 className="section-title">키워드 품질 상세</h2>
            <div className="table-meta">
              총 {summaryStats.totalKeywords}개의 키워드
            </div>
            <ComparisonTable
              data={qualityData}
              onKeywordSelect={handleKeywordSelect}
              getQualityGrade={getQualityGrade}
              filters={filters}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeywordQualityDashboard;
