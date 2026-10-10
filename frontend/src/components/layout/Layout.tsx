import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  ShieldCheck, 
  LayoutDashboard, 
  Upload, 
  Search, 
  ClipboardCheck, 
  Settings,
  FolderUp,
  Menu,
  Bell,
  BarChart3
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '../ui/button';

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);

  const navigation = [
    { name: 'Dashboard',        href: '/',         icon: LayoutDashboard },
    { name: 'Analyze Document', href: '/upload',   icon: Upload },
    { name: 'Analysis Results', href: '/results',  icon: Search },
    { name: 'Review Queue',     href: '/reviews',  icon: ClipboardCheck },
    { name: 'Analytics',        href: '/analytics',icon: BarChart3 },
    { name: 'Upload Dataset',   href: '/dataset',   icon: FolderUp },
    { name: 'System Diagnostics', href: '/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside className={cn(
        "flex flex-col w-64 bg-card border-r transition-all duration-300",
        !sidebarOpen && "w-0 -translate-x-full opacity-0"
      )}>
        <div className="flex h-16 shrink-0 items-center px-6 gap-2 border-b">
          <ShieldCheck className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold tracking-tight text-primary">VeriShield<span className="text-foreground">AI</span></span>
        </div>
        
        <div className="flex flex-1 flex-col overflow-y-auto pt-6">
          <nav className="flex-1 px-4 space-y-2">
            {navigation.map((item) => (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) => cn(
                  "group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors",
                  isActive 
                    ? "bg-primary/10 text-primary" 
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="mr-3 h-5 w-5 flex-shrink-0" aria-hidden="true" />
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>
        
        <div className="p-4 border-t border-border/50">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
              AD
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium">Admin User</span>
              <span className="text-xs text-muted-foreground">admin@verishield.ai</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar */}
        <header className="flex h-16 shrink-0 items-center justify-between border-b px-6 bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-10">
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(!sidebarOpen)} className="mr-4">
            <Menu className="h-5 w-5" />
          </Button>
          
          <div className="flex items-center gap-4">
            <Button variant="outline" size="icon" className="relative">
              <Bell className="h-4 w-4" />
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-destructive"></span>
            </Button>
          </div>
        </header>
        
        <div className="flex-1 overflow-auto p-6 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
