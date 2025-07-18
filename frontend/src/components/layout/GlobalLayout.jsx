import React from 'react';
import { ConfigProvider, Layout } from 'antd';
import koKR from 'antd/locale/ko_KR';
import GlobalHeader from './GlobalHeader';
import GlobalSidebar from './GlobalSidebar';
import GlobalContent from './GlobalContent';

// 무신사 브랜드 테마 설정
const musinsaTheme = {
  token: {
    colorPrimary: '#1677ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    borderRadius: 4,
    borderRadiusLG: 6,
    fontFamily: 'Pretendard, -apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: 14,
    fontSizeHeading1: 38,
    fontSizeHeading2: 30,
    fontSizeHeading3: 24,
    fontSizeHeading4: 20,
    fontSizeHeading5: 16,
    lineHeight: 1.5,
    colorBgBase: '#ffffff',
    colorBgContainer: '#ffffff',
    colorBgLayout: '#f8f9fa',
    colorBorder: '#e6e6e6',
    colorText: '#333333',
    colorTextSecondary: '#666666',
    colorTextTertiary: '#999999',
  },
  components: {
    Layout: {
      headerBg: '#ffffff',
      siderBg: '#f8f9fa',
      bodyBg: '#ffffff',
      headerHeight: 52,
      headerPadding: '0 24px',
    },
    Menu: {
      itemBorderRadius: 4,
      itemHeight: 40,
      itemPaddingInline: 16,
      itemColor: '#666666',
      itemHoverColor: '#333333',
      itemHoverBg: '#e9ecef',
      itemSelectedColor: '#1677ff',
      itemSelectedBg: '#e6f4ff',
      itemActiveBg: '#e6f4ff',
      fontWeight: 500,
    },
    Button: {
      borderRadius: 4,
      controlHeight: 36,
      controlHeightLG: 40,
      controlHeightSM: 28,
      paddingInline: 16,
      paddingInlineLG: 24,
      paddingInlineSM: 12,
    },
    Input: {
      borderRadius: 4,
      controlHeight: 36,
      controlHeightLG: 40,
      controlHeightSM: 28,
      paddingInline: 12,
      paddingInlineLG: 16,
      paddingInlineSM: 8,
    },
    Card: {
      borderRadius: 6,
      paddingLG: 24,
      padding: 16,
      paddingSM: 12,
    },
    Table: {
      borderRadius: 6,
      cellPaddingBlock: 12,
      cellPaddingInline: 16,
      headerBg: '#f8f9fa',
      headerColor: '#495057',
      headerSplitColor: '#e9ecef',
    },
  },
};

const GlobalLayout = ({ children, activeTab, onTabChange }) => {
  return (
    <ConfigProvider
      theme={musinsaTheme}
      locale={koKR}
      wave={{ disabled: true }}
    >
      <Layout className="min-h-screen">
        <GlobalHeader />
        <Layout hasSider>
          <GlobalSidebar activeTab={activeTab} onTabChange={onTabChange} />
          <GlobalContent>{children}</GlobalContent>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
};

export default GlobalLayout;