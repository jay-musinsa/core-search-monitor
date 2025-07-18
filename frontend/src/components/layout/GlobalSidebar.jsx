import React, { useState } from 'react';
import { Layout, Menu } from 'antd';
import { 
  SearchOutlined, 
  DashboardOutlined, 
  SyncOutlined, 
  SettingOutlined,
  UserOutlined 
} from '@ant-design/icons';

const { Sider } = Layout;

const GlobalSidebar = ({ activeTab, onTabChange }) => {
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    {
      key: 'search-quality',
      label: '검색품질 모니터링',
      icon: <UserOutlined />,
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
      key: 'sync',
      label: '동기화',
      icon: <SyncOutlined />,
      type: 'group',
      children: [],
    },
    {
      key: 'settings',
      label: '설정',
      icon: <SettingOutlined />,
      type: 'group',
      children: [],
    },
  ];

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={setCollapsed}
      width={280}
      theme="light"
      className="!bg-gray-100 border-r border-gray-300 h-[calc(100vh-52px)] overflow-y-auto"
    >
      <div className="p-4">
        <Menu
          mode="inline"
          selectedKeys={[activeTab]}
          defaultOpenKeys={['search-quality']}
          items={menuItems}
          className="border-none bg-transparent"
        />
      </div>
    </Sider>
  );
};

export default GlobalSidebar;