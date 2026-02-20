/**
 * DashboardLayout: Premium SaaS-style layout with sidebar and top header.
 */
import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  BarChart3, 
  Search,
  CheckSquare, 
  Shield,
  Menu,
  X,
  Settings,
  Database,
  TrendingUp,
  Bell,
  User,
  RefreshCw,
  LayoutDashboard,
  Radar,
  Activity,
  Calendar,
  ClipboardList,
  Zap
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface NavItem {
  id: string;
  path: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

const navItems: NavItem[] = [
  { id: 'executive', path: '/executive', label: 'Executive Summary', icon: Zap },
  { id: 'monitor', path: '/monitoring', label: 'Ingestion Health', icon: LayoutDashboard },
  { id: 'radar', path: '/radar', label: 'Issue Radar', icon: Radar, badge: 3 },
  { id: 'timeline', path: '/timeline', label: 'Policy Timeline', icon: Calendar },
  { id: 'qa', path: '/workspace/qa', label: 'Q&A Workspace', icon: Search },
  { id: 'checklist', path: '/workspace/checklist', label: 'Checklist Gen', icon: CheckSquare },
  { id: 'compliance', path: '/workspace/compliance', label: 'Task Manager', icon: ClipboardList },
  { id: 'quality', path: '/observability', label: 'RAG Observability', icon: Activity },
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

  const activeItem = navItems.find(item => item.path === location.pathname);

  return (
    <div className="min-h-screen bg-slate-50/50 flex">
      {/* Desktop Sidebar */}
      <aside 
        className={`
          fixed left-0 top-0 z-40 h-screen bg-white border-r border-slate-200
          transition-all duration-300 hidden lg:flex flex-col
          ${sidebarOpen ? 'w-64' : 'w-20'}
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-slate-100">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-lg gradient-primary flex items-center justify-center flex-shrink-0 shadow-sm">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <div className="whitespace-nowrap">
                <h1 className="font-bold text-sm tracking-tight text-slate-900">FSC Policy RAG</h1>
                <p className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">Analysis Platform</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => `
                  w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                  transition-all duration-200 group
                  ${isActive 
                    ? 'bg-slate-900 text-white shadow-md shadow-slate-200' 
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                  }
                `}
              >
                {({ isActive }) => (
                  <>
                    <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400 group-hover:text-slate-600'}`} />
                    {sidebarOpen && (
                      <>
                        <span className="flex-1 text-left text-sm font-medium">
                          {item.label}
                        </span>
                        {item.badge && !isActive && (
                          <Badge variant="secondary" className="bg-slate-100 text-slate-600 border-none h-5 px-1.5 text-[10px] font-bold">
                            {item.badge}
                          </Badge>
                        )}
                      </>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-slate-100">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-500 hover:bg-slate-50 hover:text-slate-900 transition-colors group">
            <Settings className="w-5 h-5 text-slate-400 group-hover:text-slate-600" />
            {sidebarOpen && <span className="text-sm font-medium">설정</span>}
          </button>
          
          <div className={`mt-4 flex items-center gap-3 px-3 py-2 rounded-xl bg-slate-50 border border-slate-100 ${!sidebarOpen && 'justify-center px-0'}`}>
            <div className="w-8 h-8 rounded-full bg-white shadow-sm flex items-center justify-center border border-slate-200 flex-shrink-0">
              <User className="w-4 h-4 text-slate-600" />
            </div>
            {sidebarOpen && (
              <div className="overflow-hidden">
                <p className="text-xs font-semibold text-slate-900 truncate">Admin User</p>
                <p className="text-[10px] text-slate-400 truncate">admin@fsc.go.kr</p>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'}`}>
        {/* Top Header */}
        <header className="h-16 bg-white border-b border-slate-200 sticky top-0 z-30 flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="hidden lg:flex h-9 w-9 text-slate-500 hover:bg-slate-50"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
            
            <div className="h-4 w-px bg-slate-200 mx-2 hidden lg:block" />
            
            <div className="flex items-center gap-2">
              <span className="text-slate-400 text-sm font-medium">Pages</span>
              <span className="text-slate-300 text-xs">/</span>
              <span className="text-slate-900 text-sm font-bold">{activeItem?.label || 'Not Found'}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-500">
              <Search className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-9 w-9 text-slate-500 relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
            </Button>
            <div className="h-8 w-px bg-slate-200 mx-1" />
            <Button variant="outline" size="sm" className="hidden sm:flex items-center gap-2 border-slate-200 text-slate-600 font-semibold h-9 px-4 rounded-lg hover:bg-slate-50">
              <RefreshCw className="w-4 h-4" />
              데이터 동기화
            </Button>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6 lg:p-10 flex-1">
          <div className="max-w-7xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
            {children}
          </div>
        </main>
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
        <div className="lg:hidden fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300">
          <div className="absolute right-6 bottom-24 w-64 bg-white rounded-3xl shadow-2xl p-4 animate-in slide-in-from-bottom-8 duration-300">
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
                      ${isActive 
                        ? 'bg-slate-900 text-white shadow-lg shadow-slate-200' 
                        : 'text-slate-600 hover:bg-slate-50'
                      }
                    `}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="flex-1 text-left font-bold">{item.label}</span>
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
