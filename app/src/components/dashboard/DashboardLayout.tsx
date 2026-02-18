/**
 * DashboardLayout: 좌측 메뉴 + 우측 콘텐츠 대시보드 레이아웃.
 */
import { useState } from 'react';
import { 
  BarChart3, 
  Search,
  CheckSquare, 
  Shield,
  Menu,
  X,
  Settings,
  Database,
  TrendingUp
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface NavItem {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: number;
}

const navItems: NavItem[] = [
  { id: 'monitor', label: '수집 현황', icon: Database },
  { id: 'topics', label: '이슈맵/경보', icon: TrendingUp, badge: 3 },
  { id: 'qa', label: 'RAG 질의응답', icon: Search },
  { id: 'checklist', label: '체크리스트', icon: CheckSquare },
  { id: 'quality', label: '품질 평가', icon: Shield },
];

interface DashboardLayoutProps {
  activeSection: string;
  onSectionChange: (section: string) => void;
  children: React.ReactNode;
}

export default function DashboardLayout({ 
  activeSection, 
  onSectionChange,
  children 
}: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-lavender-50 via-white to-lavender-100">
      {/* Desktop Sidebar */}
      <aside 
        className={`
          fixed left-0 top-0 z-40 h-screen bg-white border-r border-lavender-100
          transition-all duration-300 hidden lg:block
          ${sidebarOpen ? 'w-64' : 'w-20'}
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-lavender-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center flex-shrink-0">
              <BarChart3 className="w-5 h-5 text-white" />
            </div>
            {sidebarOpen && (
              <div>
                <h1 className="font-semibold text-sm">FSC Policy RAG</h1>
                <p className="text-xs text-muted-foreground">금융정책 분석</p>
              </div>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="h-8 w-8"
          >
            {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </Button>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeSection === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => onSectionChange(item.id)}
                className={`
                  w-full flex items-center gap-3 px-3 py-3 rounded-xl
                  transition-all duration-200
                  ${isActive 
                    ? 'bg-primary/10 text-primary' 
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  }
                `}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && (
                  <>
                    <span className="flex-1 text-left text-sm font-medium">
                      {item.label}
                    </span>
                    {item.badge && (
                      <Badge variant="default" className="h-5 min-w-5 px-1 text-xs">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom Actions */}
        <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-lavender-100">
          <button className="w-full flex items-center gap-3 px-3 py-3 rounded-xl text-muted-foreground hover:bg-muted transition-colors">
            <Settings className="w-5 h-5" />
            {sidebarOpen && <span className="text-sm">설정</span>}
          </button>
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-white border-b border-lavender-100">
        <div className="h-14 flex items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg gradient-primary flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold">FSC Policy RAG</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </Button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <nav className="border-t border-lavender-100 p-3 space-y-1 bg-white">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeSection === item.id;
              
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    onSectionChange(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`
                    w-full flex items-center gap-3 px-3 py-3 rounded-xl
                    ${isActive 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-muted-foreground hover:bg-muted'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span className="flex-1 text-left">{item.label}</span>
                  {item.badge && (
                    <Badge variant="default" className="h-5 min-w-5 px-1">
                      {item.badge}
                    </Badge>
                  )}
                </button>
              );
            })}
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main 
        className={`
          transition-all duration-300
          lg:ml-64
          pt-14 lg:pt-0
          min-h-screen
        `}
      >
        <div className="p-4 lg:p-8 max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
