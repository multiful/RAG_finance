/**
 * DashboardLayout: Premium Financial-grade layout with sidebar and top header.
 * React state: sidebarOpen, mobileMenuOpen. Tailwind: transitions, hover, focus.
 */
import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Menu,
  X,
  Settings,
  TrendingUp,
  Bell,
  RefreshCw,
  LayoutDashboard,
  Sparkles,
  LineChart,
  LogOut,
  Loader2,
  CheckCircle2,
  Map,
  ClipboardList,
  GitCompare
} from 'lucide-react';
import { APP_NAME } from '@/lib/constants';
import { Button } from '@/components/ui/button';
import { useCollection } from '@/contexts/CollectionContext';

interface NavItem {
  id: string;
  path: string;
  label: string;
  labelKr: string;
  icon: React.ElementType;
  badge?: number;
  isNew?: boolean;
}

const navItems: NavItem[] = [
  { id: 'dashboard', path: '/', label: 'Dashboard', labelKr: '대시보드', icon: LayoutDashboard },
  { id: 'analytics', path: '/analytics', label: 'Analytics', labelKr: '규제 분석', icon: TrendingUp },
  { id: 'qa', path: '/qa', label: 'AI Assistant', labelKr: 'AI 질의', icon: Sparkles },
  { id: 'gap-map', path: '/gap-map', label: 'Gap Map', labelKr: 'Gap Map', icon: Map },
  { id: 'sandbox', path: '/sandbox/checklist', label: 'Sandbox Checklist', labelKr: 'Sandbox 체크리스트', icon: ClipboardList },
  { id: 'policy-simulate', path: '/policy-simulate', label: 'Policy Simulate', labelKr: '규제 시뮬레이션', icon: GitCompare },
  { id: 'settings', path: '/settings', label: 'Settings', labelKr: '설정', icon: Settings },
];

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ 
  children 
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();
  const { isCollecting, jobProgress, startCollection, lastResult } = useCollection();

  const activeItem = navItems.find(item => item.path === location.pathname);

  return (
    <div className="min-h-screen bg-[#fafafa] flex">
      {/* Sidebar - Clean card style (reference: high-impact clean UI) */}
      <aside
        className={`
          fixed left-0 top-0 z-40 h-screen bg-white
          hidden lg:flex flex-col
          transition-[width] duration-300 ease-out will-change-[width]
          border-r border-[#e9e9e9]
          ${sidebarOpen ? 'w-[260px]' : 'w-[72px]'}
        `}
      >
        <div className="h-[72px] flex items-center px-5 border-b border-[#e9e9e9]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-10 h-10 rounded-2xl bg-slate-900 flex items-center justify-center flex-shrink-0">
              <LineChart className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <div className="whitespace-nowrap min-w-0">
                <p className="font-semibold text-slate-900 text-[15px] tracking-tight truncate">{APP_NAME}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">스테이블코인·STO 규제·Gap 분석</p>
              </div>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => `
                  relative flex items-center gap-3 px-4 py-3 rounded-2xl
                  transition-colors duration-150
                  ${isActive
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}
                `}
              >
                {({ isActive }) => (
                  <>
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-white/10' : 'bg-slate-100'}`}>
                      <Icon className={`w-[22px] h-[22px] ${isActive ? 'text-white' : 'text-slate-600'}`} />
                    </div>
                    {sidebarOpen && (
                      <span className={`text-[15px] font-medium ${isActive ? 'text-white' : 'text-slate-700'}`}>
                        {item.labelKr}
                      </span>
                    )}
                    {item.badge != null && (
                      <span className={`ml-auto text-xs font-semibold px-2 py-0.5 rounded-full ${isActive ? 'bg-white/20' : 'bg-red-100 text-red-600'}`}>
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-[#e9e9e9]">
          <div className={`flex items-center gap-3 p-3 rounded-2xl bg-slate-50 ${!sidebarOpen && 'justify-center p-2'}`}>
            <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold text-sm flex-shrink-0">
              T
            </div>
            {sidebarOpen && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">토스증권 · DB 공모전</p>
                  <p className="text-[11px] text-slate-500 truncate">연구 세션</p>
                </div>
                <button type="button" className="p-2 rounded-xl hover:bg-slate-200/80 text-slate-400 hover:text-slate-600 transition-colors" aria-label="로그아웃">
                  <LogOut className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>
      </aside>

      <div className={`flex-1 flex flex-col transition-[margin] duration-300 ease-out ${sidebarOpen ? 'lg:ml-[260px]' : 'lg:ml-[72px]'}`}>
        <header className="h-[72px] bg-white border-b border-[#e9e9e9] sticky top-0 z-30 flex items-center px-6 lg:px-8">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="hidden lg:flex h-10 w-10 rounded-2xl text-slate-500 hover:bg-slate-100 hover:text-slate-700"
                aria-label={sidebarOpen ? '사이드바 접기' : '사이드바 펼치기'}
              >
                {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>
              <div className="h-6 w-px bg-[#e9e9e9] hidden lg:block" />
              <div>
                <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">DB 보험·금융공모전</p>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">{activeItem?.labelKr || '대시보드'}</h1>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Global Collection Status */}
              {isCollecting && jobProgress && (
                <div className="hidden md:flex items-center gap-3 px-4 py-2 bg-blue-50 border border-blue-200 rounded-xl">
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                  <div className="flex flex-col">
                    <span className="text-sm font-semibold text-blue-700">
                      {jobProgress.stage}
                    </span>
                    <span className="text-xs text-blue-500">
                      {jobProgress.progress}% 완료
                    </span>
                  </div>
                  <div className="w-20 h-2 bg-blue-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-600 transition-all duration-300"
                      style={{ width: `${jobProgress.progress}%` }}
                    />
                  </div>
                </div>
              )}
              
              {/* Last Result Toast */}
              {!isCollecting && lastResult?.status === 'completed' && (
                <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-emerald-50 border border-emerald-200 rounded-xl">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-700">
                    신규 {lastResult.result?.total_new || 0}건 수집 완료
                  </span>
                </div>
              )}
              
              <Button variant="ghost" size="icon" className="relative h-10 w-10 rounded-2xl text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors" aria-label="알림">
                <Bell className="w-5 h-5" />
                <span className="absolute top-2 right-2 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white animate-pulse" />
              </Button>
              
              <div className="h-8 w-px bg-slate-200 mx-2 hidden sm:block" />
              
              {/* Sync Button - Connected to Global Collection */}
              <Button 
                onClick={startCollection}
                disabled={isCollecting}
                className="hidden sm:flex items-center gap-2 h-10 px-5 rounded-2xl bg-slate-900 text-white font-semibold hover:bg-slate-800 transition-colors disabled:opacity-70"
              >
                {isCollecting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    수집 중...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4" />
                    동기화
                  </>
                )}
              </Button>
            </div>
          </div>
        </header>

        <main className="p-6 lg:p-8 flex-1">
          <div className="max-w-[1400px] mx-auto space-y-8">
            {children}
          </div>
        </main>

        <footer className="py-4 px-8 border-t border-[#e9e9e9] bg-white">
          <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
            <span>© 2026 {APP_NAME} · 스테이블코인·STO 규제·Gap · DB 공모전</span>
            <div className="flex items-center gap-4 flex-wrap justify-center">
              <NavLink to="/privacy" className="hover:text-slate-600 transition-colors">개인정보처리방침</NavLink>
              <NavLink to="/terms" className="hover:text-slate-600 transition-colors">이용약관</NavLink>
              <span>Version 2.0.1</span>
              <div className="flex items-center gap-1.5">
                <div className="w-2 h-2 rounded-full bg-emerald-500" />
                <span>시스템 정상</span>
              </div>
            </div>
          </div>
        </footer>
      </div>

      {/* Mobile Nav Header */}
      <div className="lg:hidden fixed bottom-6 right-6 z-50">
        <Button
          size="icon"
          className="h-14 w-14 rounded-full shadow-xl shadow-primary/20 gradient-primary"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
        >
          {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </Button>
      </div>

      {mobileMenuOpen && (
        <div 
          className="lg:hidden fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setMobileMenuOpen(false)}
          role="button"
          tabIndex={0}
          aria-label="메뉴 닫기"
          onKeyDown={(e) => e.key === 'Escape' && setMobileMenuOpen(false)}
        >
          <div 
            className="absolute right-6 bottom-24 w-64 bg-white rounded-3xl shadow-2xl p-4 animate-in slide-in-from-bottom-8 duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="space-y-2">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={({ isActive }) => `
                      w-full flex items-center gap-4 px-4 py-4 rounded-2xl
                      transition-colors duration-150
                      ${isActive 
                        ? 'bg-slate-900 text-white shadow-lg' 
                        : 'text-slate-600 hover:bg-slate-50 active:bg-slate-100'
                      }
                    `}
                  >
                    <Icon className="w-5 h-5 flex-shrink-0" />
                    <span className="flex-1 text-left font-bold">{item.labelKr}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
