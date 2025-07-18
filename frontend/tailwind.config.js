/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      colors: {
        // 무신사 브랜드 색상
        primary: {
          50: '#e6f4ff',
          100: '#bae0ff',
          200: '#91caff',
          300: '#69b1ff',
          400: '#4096ff',
          500: '#1677ff',
          600: '#0958d9',
          700: '#003eb3',
          800: '#002c8c',
          900: '#001d66',
        },
        gray: {
          50: '#ffffff',
          100: '#fafafa',
          200: '#f0f0f0',
          300: '#e6e6e6',
          400: '#cccccc',
          500: '#b3b3b3',
          600: '#999999',
          700: '#808080',
          800: '#666666',
          900: '#4d4d4d',
          950: '#333333',
        },
        success: '#52c41a',
        warning: '#faad14',
        error: '#ff4d4f',
      },
      fontFamily: {
        'pretendard': ['Pretendard', '-apple-system', 'BlinkMacSystemFont', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'heading-1': ['38px', '46px'],
        'heading-2': ['30px', '38px'],
        'heading-3': ['24px', '32px'],
        'heading-4': ['20px', '28px'],
        'heading-5': ['16px', '24px'],
      },
      spacing: {
        '185': '185px',
        '210': '210px',
        '52': '52px',
      },
      minWidth: {
        'content': '1326px',
      },
      borderRadius: {
        'DEFAULT': '4px',
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false, // Ant Design과 충돌 방지
  },
}