import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Trophy,
  TrendingUp,
  User,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
  Brain,
  Zap,
  BarChart3,
  Shield,
  Bell,
  Layers,
  Award,
  FileText,
  Target,
  Wallet,
  CreditCard,
  Activity,
  ChevronDown,
  Crosshair,
  LineChart,
  Settings
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { useState, useEffect } from 'react';
import { clsx } from 'clsx';

interface NavItem {
  to: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}

interface NavCategory {
  name: string;
  icon: React.ComponentType<{ className?: string }>;
  items: NavItem[];
}

const navCategories: NavCategory[] = [
  {
    name: 'Betting',
    icon: Crosshair,
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Today' },
      { to: '/games', icon: Trophy, label: 'Matchups' },
      { to: '/recommendations', icon: TrendingUp, label: 'Picks' },
      { to: '/tracking', icon: BarChart3, label: 'My Bets' },
      { to: '/parlays', icon: Layers, label: 'Parlays' },
      { to: '/edge-tracker', icon: Activity, label: 'Edge Tracker' },
    ]
  },
  {
    name: 'Analysis',
    icon: LineChart,
    items: [
      { to: '/power-ratings', icon: Target, label: 'Power Ratings' },
      { to: '/models', icon: Brain, label: 'Intelligence' },
      { to: '/dfs', icon: Zap, label: 'DFS Lineups' },
    ]
  },
  {
    name: 'Practice',
    icon: Wallet,
    items: [
      { to: '/paper-trading', icon: Wallet, label: 'Paper Trading' },
      { to: '/leaderboard', icon: Award, label: 'Leaderboard' },
    ]
  },
  {
    name: 'Account',
    icon: Settings,
    items: [
      { to: '/alerts', icon: Bell, label: 'Notifications' },
      { to: '/security', icon: Shield, label: 'Security' },
      { to: '/pricing', icon: CreditCard, label: 'Pricing' },
      { to: '/profile', icon: User, label: 'Profile' },
      { to: '/terms', icon: FileText, label: 'Terms' },
    ]
  }
];

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  const { logout, client } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['Betting']);
  const location = useLocation();

  // Auto-expand category containing current route
  useEffect(() => {
    const currentCategory = navCategories.find(cat =>
      cat.items.some(item => location.pathname === item.to)
    );
    if (currentCategory && !expandedCategories.includes(currentCategory.name)) {
      setExpandedCategories(prev => [...prev, currentCategory.name]);
    }
  }, [location.pathname]);

  const toggleCategory = (categoryName: string) => {
    setExpandedCategories(prev =>
      prev.includes(categoryName)
        ? prev.filter(name => name !== categoryName)
        : [...prev, categoryName]
    );
  };

  const isCategoryActive = (category: NavCategory) => {
    return category.items.some(item => location.pathname === item.to);
  };

  return (
    <>
      {/* Mobile Header Bar */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur-sm border-b border-gray-200 dark:border-slate-700 flex items-center justify-between px-4">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors duration-200"
          aria-label="Toggle menu"
        >
          {isOpen ? (
            <X className="w-5 h-5 text-gray-700 dark:text-slate-300" />
          ) : (
            <Menu className="w-5 h-5 text-gray-700 dark:text-slate-300" />
          )}
        </button>

        <h1 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
          EdgeBet
        </h1>

        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors duration-200"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5 text-gray-700 dark:text-slate-300" />
          ) : (
            <Moon className="w-5 h-5 text-gray-700 dark:text-slate-300" />
          )}
        </button>
      </header>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/40 backdrop-blur-sm z-40 pt-16"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-40 w-72',
          'bg-white dark:bg-slate-900',
          'border-r border-gray-200 dark:border-slate-700',
          'flex flex-col transition-transform duration-300 ease-out',
          'pt-16 lg:pt-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Desktop Logo */}
        <div className="hidden lg:flex items-center gap-3 p-6 border-b border-gray-200 dark:border-slate-700">
          <div className="w-10 h-10 rounded-xl bg-emerald-600 dark:bg-emerald-500 flex items-center justify-center">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-white tracking-tight">
              EdgeBet
            </h1>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              Intelligent Edge
            </p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {navCategories.map((category) => {
            const isExpanded = expandedCategories.includes(category.name);
            const isActive = isCategoryActive(category);

            return (
              <div key={category.name} className="space-y-1">
                {/* Category Header */}
                <button
                  onClick={() => toggleCategory(category.name)}
                  className={clsx(
                    'flex items-center justify-between w-full px-4 py-3 rounded-lg text-sm font-semibold',
                    'transition-all duration-200 ease-out',
                    isActive
                      ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400'
                      : 'text-gray-700 hover:bg-gray-100 dark:text-slate-300 dark:hover:bg-slate-800'
                  )}
                >
                  <span className="flex items-center gap-3">
                    <category.icon className="w-5 h-5" />
                    {category.name}
                  </span>
                  <ChevronDown
                    className={clsx(
                      'w-4 h-4 transition-transform duration-200',
                      isExpanded ? 'rotate-180' : ''
                    )}
                  />
                </button>

                {/* Category Items */}
                <div
                  className={clsx(
                    'overflow-hidden transition-all duration-200 ease-out',
                    isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                  )}
                >
                  <div className="pl-4 space-y-1 pt-1">
                    {category.items.map((item) => (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        onClick={() => setIsOpen(false)}
                        className={({ isActive }) =>
                          clsx(
                            'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium',
                            'transition-all duration-200 ease-out',
                            isActive
                              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300'
                              : 'text-gray-600 hover:bg-gray-50 dark:text-slate-400 dark:hover:bg-slate-800/50'
                          )
                        }
                      >
                        <item.icon className="w-4 h-4" />
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-slate-700 space-y-2">
          {client && (
            <div className="px-4 py-3 rounded-lg bg-gray-50 dark:bg-slate-800">
              <p className="font-semibold text-gray-900 dark:text-white truncate">
                {client.name}
              </p>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                ${client.bankroll.toLocaleString()} bankroll
              </p>
            </div>
          )}

          {/* Desktop Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="hidden lg:flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-slate-400 dark:hover:bg-slate-800 transition-colors duration-200"
          >
            {theme === 'dark' ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
            {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
          </button>

          <button
            onClick={logout}
            className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10 transition-colors duration-200"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
