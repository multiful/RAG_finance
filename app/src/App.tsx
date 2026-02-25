/**
 * FSC Policy RAG System - Simplified 4-Menu Structure
 * 1. 대시보드 (Dashboard) - 경영진 요약 + 핵심 통계
 * 2. 규제 분석 (Analytics) - 트렌드 + 시각화
 * 3. AI 질의 (AI Q&A) - RAG 기반 질의응답
 * 4. 설정 (Settings) - 시스템 설정 및 수집 관리
 */
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import UnifiedDashboard from './sections/UnifiedDashboard';
import AnalyticsDashboard from './sections/AnalyticsDashboard';
import NewQASection from './sections/NewQASection';
import SettingsPage from './sections/SettingsPage';
import TermsPage from './sections/TermsPage';
import PrivacyPolicyPage from './sections/PrivacyPolicyPage';
import { Toaster } from '@/components/ui/sonner';
import { CollectionProvider } from '@/contexts/CollectionContext';

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 animate-page-enter">
      <div className="text-center max-w-md">
        <p className="text-8xl font-black text-slate-200 leading-none">404</p>
        <h2 className="text-2xl font-bold text-slate-900 mt-4">페이지를 찾을 수 없습니다</h2>
        <p className="text-slate-500 mt-2">요청하신 주소가 없거나 변경되었습니다.</p>
        <Link
          to="/"
          className="mt-8 inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 text-white font-semibold hover:bg-slate-800 active:scale-[0.98] transition-all duration-200"
        >
          대시보드로 돌아가기
        </Link>
      </div>
    </div>
  );
}

function App() {
  return (
    <CollectionProvider>
      <DashboardLayout>
        <Routes>
          {/* Main 4 Pages */}
          <Route path="/" element={<UnifiedDashboard />} />
          <Route path="/analytics" element={<AnalyticsDashboard />} />
          <Route path="/qa" element={<NewQASection />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPolicyPage />} />
          
          {/* Legacy redirects for backward compatibility */}
          <Route path="/monitoring" element={<Navigate to="/" replace />} />
          <Route path="/executive" element={<Navigate to="/" replace />} />
          <Route path="/workspace/qa" element={<Navigate to="/qa" replace />} />
          <Route path="/radar" element={<Navigate to="/analytics" replace />} />
          <Route path="/timeline" element={<Navigate to="/analytics" replace />} />
          <Route path="/observability" element={<Navigate to="/settings" replace />} />
          
          <Route path="*" element={<NotFound />} />
        </Routes>
        <Toaster />
      </DashboardLayout>
    </CollectionProvider>
  );
}

export default App;
