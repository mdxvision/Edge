import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button, Input, Card, Select } from '@/components/ui';
import { TrendingUp, Mail, Lock, User } from 'lucide-react';
import { api } from '@/lib/api';

type AuthMode = 'login' | 'register';

export default function Login() {
  const navigate = useNavigate();
  const { loginWithToken, createClient } = useAuth();
  const [mode, setMode] = useState<AuthMode>('register');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [requires2FA, setRequires2FA] = useState(false);

  const [loginData, setLoginData] = useState({
    email: '',
    password: '',
    totp_code: '',
  });

  const [registerData, setRegisterData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    name: '',
    bankroll: '10000',
    risk_profile: 'balanced',
    confirmAge: false,
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await api.auth.login({
        email: loginData.email,
        password: loginData.password,
        totp_code: loginData.totp_code || undefined,
      });

      if (result.requires_2fa) {
        setRequires2FA(true);
        setError('Please enter your 2FA code');
        setIsLoading(false);
        return;
      }

      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('refresh_token', result.refresh_token);

      await loginWithToken(result.session_token, result.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to login');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!registerData.confirmAge) {
      setError('You must confirm you are 21 or older');
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (registerData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      const result = await api.auth.register({
        email: registerData.email,
        username: registerData.username,
        password: registerData.password,
      });

      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('refresh_token', result.refresh_token);

      await createClient({
        name: registerData.name || registerData.username,
        bankroll: parseFloat(registerData.bankroll),
        risk_profile: registerData.risk_profile,
      });

      await loginWithToken(result.session_token, result.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-950 dark:to-surface-900">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-500/20 mb-4">
            <TrendingUp className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          </div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Welcome to EdgeBet
          </h1>
          <p className="text-surface-500 mt-2">
            AI-powered sports betting analytics
          </p>
        </div>

        <div className="mb-6 p-3 bg-warning-50 dark:bg-warning-500/10 rounded-lg">
          <p className="text-xs text-warning-700 dark:text-warning-400 text-center">
            <strong>SIMULATION ONLY</strong> - For educational purposes. No real money wagering.
          </p>
        </div>

        <div className="flex mb-6 border-b border-surface-200 dark:border-surface-700">
          <button
            className={`flex-1 pb-3 text-sm font-medium ${
              mode === 'register'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
            }`}
            onClick={() => setMode('register')}
          >
            Create Account
          </button>
          <button
            className={`flex-1 pb-3 text-sm font-medium ${
              mode === 'login'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-surface-500 hover:text-surface-700 dark:hover:text-surface-300'
            }`}
            onClick={() => setMode('login')}
          >
            Sign In
          </button>
        </div>

        {mode === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                className="pl-10"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Password"
                type="password"
                placeholder="Enter your password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                className="pl-10"
                required
              />
            </div>

            {requires2FA && (
              <Input
                label="2FA Code"
                placeholder="Enter 6-digit code"
                value={loginData.totp_code}
                onChange={(e) => setLoginData({ ...loginData, totp_code: e.target.value })}
                maxLength={6}
              />
            )}

            {error && (
              <p className="text-sm text-danger-500 text-center">{error}</p>
            )}

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Sign In
            </Button>

            <button
              type="button"
              onClick={() => navigate('/reset-password')}
              className="w-full text-sm text-primary-600 hover:underline"
            >
              Forgot password?
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={registerData.email}
                onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                className="pl-10"
                required
              />
            </div>

            <div className="relative">
              <User className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Username"
                placeholder="Choose a username"
                value={registerData.username}
                onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                className="pl-10"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Password"
                type="password"
                placeholder="Create a password (min 8 characters)"
                value={registerData.password}
                onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                className="pl-10"
                required
                minLength={8}
              />
            </div>

            <Input
              label="Confirm Password"
              type="password"
              placeholder="Confirm your password"
              value={registerData.confirmPassword}
              onChange={(e) => setRegisterData({ ...registerData, confirmPassword: e.target.value })}
              required
            />

            <Input
              label="Display Name"
              placeholder="Your name (shown on leaderboard)"
              value={registerData.name}
              onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
            />

            <Input
              label="Starting Bankroll ($)"
              type="number"
              placeholder="10000"
              min="100"
              step="100"
              value={registerData.bankroll}
              onChange={(e) => setRegisterData({ ...registerData, bankroll: e.target.value })}
              required
            />

            <Select
              label="Risk Profile"
              value={registerData.risk_profile}
              onChange={(e) => setRegisterData({ ...registerData, risk_profile: e.target.value })}
              options={[
                { value: 'conservative', label: 'Conservative - Lower stakes, safer bets' },
                { value: 'balanced', label: 'Balanced - Moderate risk and reward' },
                { value: 'aggressive', label: 'Aggressive - Higher stakes, bigger swings' },
              ]}
            />

            <label className="flex items-start gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={registerData.confirmAge}
                onChange={(e) => setRegisterData({ ...registerData, confirmAge: e.target.checked })}
                className="mt-1 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                required
              />
              <span className="text-surface-600 dark:text-surface-400">
                I confirm that I am <strong>21 years of age or older</strong> and agree to the{' '}
                <a href="/terms" target="_blank" className="text-primary-600 hover:underline">
                  Terms of Service
                </a>
              </span>
            </label>

            {error && (
              <p className="text-sm text-danger-500 text-center">{error}</p>
            )}

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Create Account
            </Button>
          </form>
        )}

        <p className="text-xs text-surface-500 text-center mt-6">
          By continuing, you acknowledge this is a simulation platform for educational purposes only.
        </p>
      </Card>
    </div>
  );
}
