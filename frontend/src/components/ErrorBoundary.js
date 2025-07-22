import React from "react";
import { Alert, Button, Card, Typography } from "antd";
import { ReloadOutlined, BugOutlined } from "@ant-design/icons";

const { Title, Text } = Typography;

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // 다음 렌더링에서 fallback UI가 보이도록 상태를 업데이트합니다.
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // 에러 리포팅 서비스에 에러를 기록할 수 있습니다.
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // 에러 UI를 커스텀하여 렌더링할 수 있습니다.
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <Card className="max-w-2xl w-full">
            <div className="text-center">
              <BugOutlined className="text-6xl text-red-500 mb-4" />
              <Title level={2} className="text-red-600 mb-4">
                앗! 문제가 발생했습니다
              </Title>
              <Text className="text-gray-600 text-lg mb-6 block">
                예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해주세요.
              </Text>

              <Alert
                message="오류 정보"
                description={
                  <div className="text-left">
                    <Text strong>에러 메시지:</Text>
                    <pre className="bg-gray-100 p-2 rounded mt-2 text-sm overflow-auto">
                      {this.state.error && this.state.error.toString()}
                    </pre>
                    {process.env.NODE_ENV === "development" && (
                      <>
                        <Text strong className="block mt-4">
                          스택 트레이스:
                        </Text>
                        <pre className="bg-gray-100 p-2 rounded mt-2 text-xs overflow-auto max-h-40">
                          {this.state.errorInfo.componentStack}
                        </pre>
                      </>
                    )}
                  </div>
                }
                type="error"
                className="text-left mb-6"
              />

              <div className="space-x-4">
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={this.handleReload}
                  size="large"
                >
                  페이지 새로고침
                </Button>
                <Button onClick={this.handleReset} size="large">
                  다시 시도
                </Button>
              </div>

              <Text className="text-gray-500 text-sm block mt-6">
                문제가 계속 발생하면 개발팀에 문의해주세요.
              </Text>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
