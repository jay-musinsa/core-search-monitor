import React, { useEffect, useState, useRef } from "react";
import { Modal, Button, Space, Typography, Spin } from "antd";
import { ZoomInOutlined, ZoomOutOutlined, ExpandOutlined, ReloadOutlined } from "@ant-design/icons";

const { Text } = Typography;

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
    <Modal
      open={true}
      onCancel={onClose}
      footer={null}
      width="90vw"
      style={{ top: 20 }}
      title={
        <div className="flex justify-between items-center">
          <div>
            <Text strong>{screenshot.platform}</Text>
            <Text className="ml-2 text-gray-600">{screenshot.keyword}</Text>
          </div>
          <Space>
            <Button
              icon={<ZoomOutOutlined />}
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.5}
              title="축소"
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={handleResetZoom}
              title="원본 크기"
            />
            <Button
              icon={<ZoomInOutlined />}
              onClick={handleZoomIn}
              disabled={zoomLevel >= 3}
              title="확대"
            />
            <Button
              icon={<ExpandOutlined />}
              onClick={handleFullScreen}
              title="새 탭에서 열기"
            />
          </Space>
        </div>
      }
      destroyOnClose
    >
      <div className="relative">
        <div
          ref={containerRef}
          className="overflow-hidden border border-gray-200 rounded-lg"
          style={{ height: "70vh" }}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          {!imageLoaded && (
            <div className="flex flex-col items-center justify-center h-full">
              <Spin size="large" className="mb-4" />
              <Text>이미지 로딩 중...</Text>
            </div>
          )}

          <img
            ref={imageRef}
            src={screenshot.url}
            alt={`${screenshot.keyword} 스크린샷`}
            className={`max-w-full max-h-full object-contain ${isDragging ? "cursor-grabbing" : "cursor-grab"}`}
            onLoad={handleImageLoad}
            onError={handleImageError}
            onMouseDown={handleMouseDown}
            style={{
              display: imageLoaded ? "block" : "none",
              transform: `scale(${zoomLevel}) translate(${imagePosition.x}px, ${imagePosition.y}px)`,
              transformOrigin: "center center",
            }}
          />
        </div>
        
        <div className="mt-4 flex justify-between items-center">
          <div>
            <Text strong>{Math.round(zoomLevel * 100)}%</Text>
            {zoomLevel > 1 && (
              <Text className="ml-2 text-gray-600">드래그하여 이동</Text>
            )}
          </div>
          <Space>
            <Button onClick={handleFullScreen}>
              새 탭에서 열기
            </Button>
            <Button onClick={onClose}>
              닫기
            </Button>
          </Space>
        </div>
      </div>
    </Modal>
  );
}
