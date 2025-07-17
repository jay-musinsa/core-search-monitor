import React, { useState } from "react";
import "./App.css";
import KeywordSearch from "./components/KeywordSearch";
import KeywordQualityDashboard from "./components/Dashboard/KeywordQualityDashboard";

function App() {
  const [activeTab, setActiveTab] = useState("search");

  return (
    <div className="App">
      {/* 상단 헤더 */}
      <header className="app-header">
        <h1 className="app-title">MUSINSA Search ADMIN</h1>
      </header>

      <div className="app-body">
        {/* 사이드바 네비게이션 */}
        <nav className="sidebar">
          <div className="sidebar-section">
            <div className="sidebar-header">
              <span className="sidebar-icon">👥</span>
              <span className="sidebar-title">검색품질 모니터링</span>
            </div>
            <ul className="sidebar-menu">
              <li className="sidebar-item">
                <button
                  className={`sidebar-link ${
                    activeTab === "search" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("search")}
                >
                  키워드 검색
                </button>
              </li>
              <li className="sidebar-item">
                <button
                  className={`sidebar-link ${
                    activeTab === "dashboard" ? "active" : ""
                  }`}
                  onClick={() => setActiveTab("dashboard")}
                >
                  품질 대시보드
                </button>
              </li>
            </ul>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-header">
              <span className="sidebar-icon">🔄</span>
              <span className="sidebar-title">동기화</span>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-header">
              <span className="sidebar-icon">⚙️</span>
              <span className="sidebar-title">설정</span>
            </div>
          </div>
        </nav>

        {/* 메인 콘텐츠 */}
        <main className="main-content">
          {activeTab === "search" && <KeywordSearch />}
          {activeTab === "dashboard" && <KeywordQualityDashboard />}
        </main>
      </div>
    </div>
  );
}

export default App;
