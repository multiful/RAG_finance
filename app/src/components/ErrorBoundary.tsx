import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertCircle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
          <div className="max-w-md w-full">
            <Alert variant="destructive" className="border-2 shadow-lg bg-white">
              <AlertCircle className="h-5 w-5" />
              <AlertTitle className="text-lg font-bold">시스템 오류가 발생했습니다</AlertTitle>
              <AlertDescription className="mt-2 text-slate-600">
                애플리케이션 실행 중 예기치 않은 문제가 발생했습니다. 페이지를 새로고침 하거나 나중에 다시 시도해주세요.
                {this.state.error && (
                  <pre className="mt-4 p-3 bg-slate-100 rounded text-xs overflow-auto max-h-32 text-slate-500">
                    {this.state.error.message}
                  </pre>
                )}
              </AlertDescription>
              <div className="mt-6">
                <Button 
                  onClick={() => window.location.reload()} 
                  className="w-full gradient-primary text-white font-bold"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  페이지 새로고침
                </Button>
              </div>
            </Alert>
          </div>
        </div>
      );
    }

    return this.children;
  }
}

export default ErrorBoundary;
