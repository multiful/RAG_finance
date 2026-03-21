/**
 * 정책 RAG 시스템 - 대시보드·규제분석·AI Q&A·설정
 * 라우트 단위 lazy 로딩으로 초기 JS 번들·첫 페인트 부담 감소
 */
import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import DashboardLayout from '@/components/dashboard/DashboardLayout';
import { Toaster } from '@/components/ui/sonner';
import { CollectionProvider } from '@/contexts/CollectionContext';

const UnifiedDashboard = lazy(() => import('./sections/UnifiedDashboard'));
const AnalyticsDashboard = lazy(() => import('./sections/AnalyticsDashboard'));
const NewQASection = lazy(() => import('./sections/NewQASection'));
const GapMapDashboard = lazy(() => import('./sections/GapMapDashboard'));
const SandboxChecklistPage = lazy(() => import('./sections/SandboxChecklistPage'));
const PolicySimulatePage = lazy(() => import('./sections/PolicySimulatePage'));
const SettingsPage = lazy(() => import('./sections/SettingsPage'));
const TermsPage = lazy(() => import('./sections/TermsPage'));
const PrivacyPolicyPage = lazy(() => import('./sections/PrivacyPolicyPage'));

function RouteFallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center text-slate-500 text-sm">
      <span className="animate-pulse">페이지 로딩 중…</span>
    </div>
  );
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 animate-page-enter">
      <div className="text-center max-w-md">
        <p className="text-8xl font-black text-slate-200 leading-none">404</p>
        <h2 className="text-2xl font-bold text-slate-900 mt-4">페이지를 찾을 수 없습니다</h2>
        <p className="text-slate-500 mt-2">요청하신 주소가 없거나 변경되었습니다.</p>
        <p className="text-slate-400 mt-1 text-sm">데모 안내는 대시보드에서 「실현 가능성 · 데모 시나리오 안내」를 펼쳐 보세요.</p>
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
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<UnifiedDashboard />} />
            <Route path="/analytics" element={<AnalyticsDashboard />} />
            <Route path="/qa" element={<NewQASection />} />
            <Route path="/gap-map" element={<GapMapDashboard />} />
            <Route path="/sandbox/checklist" element={<SandboxChecklistPage />} />
            <Route path="/policy-simulate" element={<PolicySimulatePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/privacy" element={<PrivacyPolicyPage />} />

            <Route path="/monitoring" element={<Navigate to="/" replace />} />
            <Route path="/executive" element={<Navigate to="/" replace />} />
            <Route path="/workspace/qa" element={<Navigate to="/qa" replace />} />
            <Route path="/radar" element={<Navigate to="/analytics" replace />} />
            <Route path="/timeline" element={<Navigate to="/analytics" replace />} />
            <Route path="/observability" element={<Navigate to="/settings" replace />} />

            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
        <Toaster />
      </DashboardLayout>
    </CollectionProvider>
  );
}

export default App;
