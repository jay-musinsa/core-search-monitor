import React, { useState, useMemo } from "react";
import "./ComparisonTable.css";

const ComparisonTable = ({
  data,
  onKeywordSelect,
  getQualityGrade,
  filters,
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);
  const [sortConfig, setSortConfig] = useState({
    key: "ndcg_score",
    direction: "desc",
  });

  // 정렬된 데이터
  const sortedData = useMemo(() => {
    let sortableData = [...data];
    if (sortConfig.key) {
      sortableData.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === "asc" ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
          return sortConfig.direction === "asc" ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableData;
  }, [data, sortConfig]);

  // 페이지네이션
  const totalPages = Math.ceil(sortedData.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const currentData = sortedData.slice(startIndex, endIndex);

  // 정렬 핸들러
  const handleSort = (key) => {
    setSortConfig({
      key,
      direction:
        sortConfig.key === key && sortConfig.direction === "asc"
          ? "desc"
          : "asc",
    });
  };

  // 페이지 변경 핸들러
  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  // 정렬 아이콘
  const getSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return "↕";
    }
    return sortConfig.direction === "asc" ? "↑" : "↓";
  };

  // 플랫폼 뱃지
  const getPlatformBadge = (platform) => {
    const platformMap = {
      musinsa: { label: "무신사", color: "#000" },
      "29cm": { label: "29CM", color: "#ff6b6b" },
      all: { label: "전체", color: "#6c757d" },
    };
    const platformInfo = platformMap[platform] || {
      label: platform,
      color: "#6c757d",
    };

    return (
      <span
        className="platform-badge"
        style={{ backgroundColor: platformInfo.color }}
      >
        {platformInfo.label}
      </span>
    );
  };

  // 점수 뱃지
  const getScoreBadge = (score, type) => {
    const grade = getQualityGrade(score);
    return <span className={`score-badge ${grade}`}>{score.toFixed(3)}</span>;
  };

  if (!data || data.length === 0) {
    return (
      <div className="no-data">
        <div className="no-data-content">
          <div className="no-data-icon">📊</div>
          <div className="no-data-text">품질 데이터가 없습니다</div>
          <div className="no-data-subtext">
            필터 조건을 변경하거나 데이터를 수집해보세요
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="comparison-table">
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort("keyword")}>
                키워드 {getSortIcon("keyword")}
              </th>
              <th onClick={() => handleSort("platform")}>
                플랫폼 {getSortIcon("platform")}
              </th>
              <th onClick={() => handleSort("ndcg_score")}>
                NDCG 점수 {getSortIcon("ndcg_score")}
              </th>
              <th onClick={() => handleSort("precision")}>
                정확도 {getSortIcon("precision")}
              </th>
              <th onClick={() => handleSort("recall")}>
                재현율 {getSortIcon("recall")}
              </th>
              <th onClick={() => handleSort("assessment_date")}>
                평가일 {getSortIcon("assessment_date")}
              </th>
            </tr>
          </thead>
          <tbody>
            {currentData.map((item, index) => (
              <tr
                key={item.id || index}
                className="table-row"
                onClick={() => onKeywordSelect && onKeywordSelect(item)}
              >
                <td className="keyword-cell">
                  <span className="keyword-text">{item.keyword}</span>
                </td>
                <td className="platform-cell">
                  {getPlatformBadge(item.platform)}
                </td>
                <td className="score-cell">
                  {getScoreBadge(item.ndcg_score, "ndcg")}
                </td>
                <td className="score-cell">
                  {getScoreBadge(item.precision, "precision")}
                </td>
                <td className="score-cell">
                  {getScoreBadge(item.recall, "recall")}
                </td>
                <td className="date-cell">
                  {item.assessment_date
                    ? new Date(item.assessment_date).toLocaleDateString()
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* 페이지네이션 */}
        {totalPages > 1 && (
          <div className="pagination">
            <button
              className="page-btn"
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
            >
              이전
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                className={`page-btn ${currentPage === page ? "active" : ""}`}
                onClick={() => handlePageChange(page)}
              >
                {page}
              </button>
            ))}

            <button
              className="page-btn"
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
            >
              다음
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ComparisonTable;
