import React, { useEffect, useState, useRef } from "react";
import "./ScreenshotModal.css";

export default function ScreenshotModal({ screenshot, onClose }) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [imagePosition, setImagePosition] = useState({ x: 0, y: 0 });
  const imageRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [onClose]);

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleImageError = () => {
    console.error("스크린샷 이미지 로드 실패:", screenshot.url);
  };

  // 줌 컨트롤
  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.5, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.5, 0.5));
  };

  const handleResetZoom = () => {
    setZoomLevel(1);
    setImagePosition({ x: 0, y: 0 });
  };

  const handleFullScreen = () => {
    window.open(screenshot.url, "_blank");
  };

  // 드래그 컨트롤
  const handleMouseDown = (e) => {
    if (zoomLevel <= 1) return;

    e.preventDefault();
    setIsDragging(true);
    setDragStart({
      x: e.clientX - imagePosition.x,
      y: e.clientY - imagePosition.y,
    });
  };

  const handleMouseMove = (e) => {
    if (!isDragging || zoomLevel <= 1) return;

    e.preventDefault();
    const newX = e.clientX - dragStart.x;
    const newY = e.clientY - dragStart.y;

    setImagePosition({ x: newX, y: newY });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // 터치 컨트롤
  const handleTouchStart = (e) => {
    if (zoomLevel <= 1) return;

    e.preventDefault();
    const touch = e.touches[0];
    setIsDragging(true);
    setDragStart({
      x: touch.clientX - imagePosition.x,
      y: touch.clientY - imagePosition.y,
    });
  };

  const handleTouchMove = (e) => {
    if (!isDragging || zoomLevel <= 1) return;

    e.preventDefault();
    const touch = e.touches[0];
    const newX = touch.clientX - dragStart.x;
    const newY = touch.clientY - dragStart.y;

    setImagePosition({ x: newX, y: newY });
  };

  const handleTouchEnd = () => {
    setIsDragging(false);
  };

  // 휠 줌
  const handleWheel = (e) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      handleZoomIn();
    } else {
      handleZoomOut();
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-container">
        <div className="modal-header">
          <div className="modal-title">
            <span className="modal-platform">{screenshot.platform}</span>
            <span className="modal-keyword">{screenshot.keyword}</span>
          </div>
          <div className="modal-controls">
            <button
              className="control-btn"
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.5}
              title="축소"
            >
              −
            </button>
            <button
              className="control-btn"
              onClick={handleResetZoom}
              title="원본 크기"
            >
              ⌂
            </button>
            <button
              className="control-btn"
              onClick={handleZoomIn}
              disabled={zoomLevel >= 3}
              title="확대"
            >
              +
            </button>
            <button
              className="control-btn primary"
              onClick={handleFullScreen}
              title="새 탭에서 열기"
            >
              ↗
            </button>
            <button className="modal-close" onClick={onClose} title="닫기">
              ×
            </button>
          </div>
        </div>

        <div className="modal-content">
          <div
            ref={containerRef}
            className="screenshot-viewer"
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            onWheel={handleWheel}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            {!imageLoaded && (
              <div className="loading-placeholder">
                <div className="loading-spinner"></div>
                <div>이미지 로딩 중...</div>
              </div>
            )}

            <img
              ref={imageRef}
              src={screenshot.url}
              alt={`${screenshot.keyword} 스크린샷`}
              className={`screenshot-image ${isDragging ? "dragging" : ""}`}
              onLoad={handleImageLoad}
              onError={handleImageError}
              onMouseDown={handleMouseDown}
              style={{
                display: imageLoaded ? "block" : "none",
                cursor:
                  zoomLevel > 1
                    ? isDragging
                      ? "grabbing"
                      : "grab"
                    : "default",
                transform: `scale(${zoomLevel}) translate(${imagePosition.x}px, ${imagePosition.y}px)`,
                transformOrigin: "center center",
              }}
            />
          </div>
        </div>

        <div className="modal-footer">
          <div className="zoom-info">
            <span className="zoom-level">{Math.round(zoomLevel * 100)}%</span>
            {zoomLevel > 1 && (
              <span className="drag-hint">드래그하여 이동</span>
            )}
          </div>
          <div className="modal-actions">
            <button className="action-btn secondary" onClick={handleFullScreen}>
              새 탭에서 열기
            </button>
            <button className="action-btn" onClick={onClose}>
              닫기
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
