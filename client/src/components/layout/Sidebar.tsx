import { NavLink } from 'react-router-dom';
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
  FileText
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import { useAuth } from '@/context/AuthContext';
import { useState } from 'react';
import { clsx } from 'clsx';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/games', icon: Trophy, label: 'Games' },
  { to: '/recommendations', icon: TrendingUp, label: 'Picks' },
  { to: '/tracking', icon: BarChart3, label: 'Bet Tracking' },
  { to: '/parlays', icon: Layers, label: 'Parlay Builder' },
  { to: '/leaderboard', icon: Award, label: 'Leaderboard' },
  { to: '/dfs', icon: Zap, label: 'DFS Lineups' },
  { to: '/models', icon: Brain, label: 'Models' },
  { to: '/alerts', icon: Bell, label: 'Alerts' },
  { to: '/security', icon: Shield, label: 'Security' },
  { to: '/profile', icon: User, label: 'Profile' },
  { to: '/terms', icon: FileText, label: 'Terms of Service' },
];

export default function Sidebar() {
  const { theme, toggleTheme } = useTheme();
  const { logout, client } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Mobile Header Bar */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 bg-white dark:bg-surface-900 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between px-4">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
          aria-label="Toggle menu"
        >
          {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <h1 className="text-lg font-bold text-surface-900 dark:text-white">
          EdgeBet
        </h1>

        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? (
            <Sun className="w-5 h-5" />
          ) : (
            <Moon className="w-5 h-5" />
          )}
        </button>
      </header>

      {/* Mobile Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40 pt-16"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed lg:static inset-y-0 left-0 z-40 w-64 bg-white dark:bg-surface-900 border-r border-surface-200 dark:border-surface-800 flex flex-col transition-transform duration-300',
          'pt-16 lg:pt-0',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Desktop Logo - Hidden on Mobile */}
        <div className="hidden lg:block p-6 border-b border-surface-200 dark:border-surface-800">
          <h1 className="text-xl font-bold text-surface-900 dark:text-white">
            EdgeBet
          </h1>
          <p className="text-xs text-surface-500 mt-1">Analytics Platform</p>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setIsOpen(false)}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-600 dark:bg-primary-500/10 dark:text-primary-400'
                    : 'text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800'
                )
              }
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t border-surface-200 dark:border-surface-800 space-y-2">
          {client && (
            <div className="px-3 py-2 text-sm">
              <p className="font-medium text-surface-900 dark:text-white truncate">
                {client.name}
              </p>
              <p className="text-xs text-surface-500">
                ${client.bankroll.toLocaleString()} bankroll
              </p>
            </div>
          )}

          {/* Desktop Theme Toggle - Hidden on Mobile */}
          <button
            onClick={toggleTheme}
            className="hidden lg:flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-100 dark:text-surface-400 dark:hover:bg-surface-800 transition-colors"
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
            className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-500/10 transition-colors"
          >
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
