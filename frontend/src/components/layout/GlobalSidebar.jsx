import React, { useState, useEffect } from 'react';
import { Layout, Menu, Tooltip } from 'antd';
import { 
  SearchOutlined, 
  DashboardOutlined, 
  SyncOutlined, 
  SettingOutlined,
  MonitorOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined
} from '@ant-design/icons';

const { Sider } = Layout;

const GlobalSidebar = ({ activeTab, onTabChange }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // 반응형 처리
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      if (mobile) {
        setCollapsed(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 접힌 상태에서의 메뉴 아이템 (아이콘만)
  const collapsedMenuItems = [
    {
      key: 'search',
      icon: (
        <Tooltip title="키워드 검색" placement="right">
          <SearchOutlined />
        </Tooltip>
      ),
      onClick: () => onTabChange('search'),
    },
    {
      key: 'dashboard',
      icon: (
        <Tooltip title="품질 대시보드" placement="right">
          <DashboardOutlined />
        </Tooltip>
      ),
      onClick: () => onTabChange('dashboard'),
    },
    {
      type: 'divider',
    },
    {
      key: 'sync',
      icon: (
        <Tooltip title="동기화" placement="right">
          <SyncOutlined />
        </Tooltip>
      ),
      disabled: true,
    },
    {
      key: 'settings',
      icon: (
        <Tooltip title="설정" placement="right">
          <SettingOutlined />
        </Tooltip>
      ),
      disabled: true,
    },
  ];

  // 확장 상태에서의 메뉴 아이템 (그룹화)
  const expandedMenuItems = [
    {
      key: 'search-quality',
      label: '검색품질 모니터링',
      icon: <MonitorOutlined />,
      type: 'group',
      children: [
        {
          key: 'search',
          label: '키워드 검색',
          icon: <SearchOutlined />,
          onClick: () => onTabChange('search'),
        },
        {
          key: 'dashboard',
          label: '품질 대시보드',
          icon: <DashboardOutlined />,
          onClick: () => onTabChange('dashboard'),
        },
      ],
    },
    {
      key: 'system',
      label: '시스템 관리',
      icon: <SettingOutlined />,
      type: 'group',
      children: [
        {
          key: 'sync',
          label: '동기화',
          icon: <SyncOutlined />,
          disabled: true,
        },
        {
          key: 'settings',
          label: '설정',
          icon: <SettingOutlined />,
          disabled: true,
        },
      ],
    },
  ];

  // 토글 버튼 커스텀
  const CustomTrigger = () => (
    <div 
      className={`
        flex items-center justify-center w-full min-h-[48px] py-3
        bg-white border-t border-gray-200 cursor-pointer
        hover:bg-gray-50 transition-colors duration-200
        ${collapsed ? 'px-2' : 'px-4'}
      `}
      onClick={() => setCollapsed(!collapsed)}
    >
      {collapsed ? (
        <MenuUnfoldOutlined className="text-gray-600 text-base" />
      ) : (
        <div className="flex items-center justify-between w-full">
          <span className="text-sm text-gray-600 font-medium">메뉴 접기</span>
          <MenuFoldOutlined className="text-gray-600 text-base" />
        </div>
      )}
    </div>
  );

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      trigger={null} // 기본 트리거 숨기기
      width={280}
      collapsedWidth={64}
      theme="light"
      className={`
        !bg-white border-r border-gray-200 
        transition-all duration-300 ease-in-out
        ${collapsed ? 'shadow-sm' : 'shadow-none'}
      `}
      style={{
        height: '100vh',
        position: 'sticky',
        top: 0,
        overflow: 'hidden'
      }}
    >
              <div className={`${collapsed ? 'p-2' : 'p-4'} flex flex-col h-full`} style={{ paddingTop: '52px' }}>
        {/* 로고/브랜드 영역 */}
        {!collapsed && (
          <div className="mb-6 pb-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <MonitorOutlined className="text-white text-lg" />
              </div>
              <div>
                <div className="font-semibold text-gray-900 text-sm">품질 상세</div>
                <div className="text-xs text-gray-500">Search Monitor</div>
              </div>
            </div>
          </div>
        )}

        {/* 메뉴 영역 */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
          <Menu
            mode="inline"
            selectedKeys={[activeTab]}
            defaultOpenKeys={collapsed ? [] : ['search-quality', 'system']}
            items={collapsed ? collapsedMenuItems : expandedMenuItems}
            className={`
              border-none bg-transparent h-full
              ${collapsed ? '!w-full' : ''}
            `}
            inlineIndent={collapsed ? 0 : 24}
          />
        </div>

        {/* 토글 버튼 */}
        <CustomTrigger />
      </div>
    </Sider>
  );
};

export default GlobalSidebar;