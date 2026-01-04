import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button, Input, Card, Select } from '@/components/ui';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { TrendingUp, Mail, Lock, User } from 'lucide-react';
import { api } from '@/lib/api';

type AuthMode = 'login' | 'register';

export default function Login() {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
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

    // Debug: Log what's being sent
    console.log('Login attempt:', { email: loginData.email, passwordLength: loginData.password.length });

    try {
      const result = await api.auth.login({
        email: loginData.email,
        password: loginData.password,
        totp_code: loginData.totp_code || undefined,
      });
      console.log('Login success:', result);

      if (result.requires_2fa) {
        setRequires2FA(true);
        setError('Enter your 2FA code to continue');
        setIsLoading(false);
        return;
      }

      localStorage.setItem('session_token', result.access_token);
      localStorage.setItem('refresh_token', result.refresh_token);

      if (result.user?.client_id) {
        localStorage.setItem('clientId', result.user.client_id.toString());
      }

      await loginWithToken(result.access_token, result.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      console.error('Login error:', err);
      setError(err instanceof Error ? err.message : 'Something\'s not right. Try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!registerData.confirmAge) {
      setError('Age verification required');
      return;
    }

    if (registerData.password !== registerData.confirmPassword) {
      setError('Passwords don\'t match');
      return;
    }

    if (registerData.password.length < 8) {
      setError('Password needs at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      const result = await api.auth.register({
        email: registerData.email,
        username: registerData.username,
        password: registerData.password,
        initial_bankroll: parseFloat(registerData.bankroll),
        risk_profile: registerData.risk_profile,
      });

      localStorage.setItem('session_token', result.access_token);
      localStorage.setItem('refresh_token', result.refresh_token);

      if (result.user?.client_id) {
        localStorage.setItem('clientId', result.user.client_id.toString());
      }

      await loginWithToken(result.access_token, result.refresh_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something\'s not right. Try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-surface-50 dark:bg-surface-950">
      <Card className="w-full max-w-md" padding="lg">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary-600 dark:bg-primary-500 mb-5">
            <TrendingUp className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-h1 text-surface-900 dark:text-white">
            Welcome to EdgeBet.
          </h1>
          <p className="text-surface-500 dark:text-surface-400 mt-2">
            Intelligent edge detection. Beautifully simple.
          </p>
        </div>

        {/* Warning Banner */}
        <div className="mb-6 p-4 bg-warning-50 dark:bg-warning-500/10 rounded-xl border border-warning-100 dark:border-warning-500/20">
          <p className="text-sm text-warning-700 dark:text-warning-400 text-center font-medium">
            Simulation only. For educational purposes.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex mb-8 p-1 bg-surface-100 dark:bg-surface-800 rounded-xl">
          <button
            className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${
              mode === 'register'
                ? 'bg-white dark:bg-surface-700 text-surface-900 dark:text-white shadow-sm'
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-300'
            }`}
            onClick={() => setMode('register')}
          >
            Get Started
          </button>
          <button
            className={`flex-1 py-2.5 text-sm font-semibold rounded-lg transition-all duration-200 ${
              mode === 'login'
                ? 'bg-white dark:bg-surface-700 text-surface-900 dark:text-white shadow-sm'
                : 'text-surface-500 dark:text-surface-400 hover:text-surface-700 dark:hover:text-surface-300'
            }`}
            onClick={() => setMode('login')}
          >
            Sign In
          </button>
        </div>

        {mode === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-5">
            <div className="relative">
              <Mail className="absolute left-4 top-[42px] w-5 h-5 text-surface-400" />
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={loginData.email}
                onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                className="pl-12"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-4 top-[42px] w-5 h-5 text-surface-400" />
              <Input
                label="Password"
                type="password"
                placeholder="Your password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                className="pl-12"
                required
              />
            </div>

            {requires2FA && (
              <Input
                label="Two-Factor Code"
                placeholder="6-digit code"
                value={loginData.totp_code}
                onChange={(e) => setLoginData({ ...loginData, totp_code: e.target.value })}
                maxLength={6}
              />
            )}

            {error && (
              <ErrorMessage
                message={error}
                onDismiss={() => setError('')}
              />
            )}

            <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
              Continue
            </Button>

            <button
              type="button"
              onClick={() => navigate('/reset-password')}
              className="w-full text-sm text-primary-600 dark:text-primary-400 hover:underline font-medium"
            >
              Forgot password?
            </button>

            {/* Dev Login Bypass */}
            <div className="pt-4 border-t border-surface-200 dark:border-surface-700">
              <Button
                type="button"
                variant="secondary"
                className="w-full"
                onClick={async () => {
                  setIsLoading(true);
                  setError('');
                  try {
                    const result = await api.auth.login({
                      email: 'test@edgebet.com',
                      password: 'TestPass123!',
                    });
                    localStorage.setItem('session_token', result.access_token);
                    localStorage.setItem('refresh_token', result.refresh_token);
                    if (result.user?.client_id) {
                      localStorage.setItem('clientId', result.user.client_id.toString());
                    }
                    await loginWithToken(result.access_token, result.refresh_token);
                    navigate('/dashboard');
                  } catch (err) {
                    setError('Dev login failed. Make sure backend is running.');
                  } finally {
                    setIsLoading(false);
                  }
                }}
                isLoading={isLoading}
              >
                Dev Login (test@edgebet.com)
              </Button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-5">
            <div className="relative">
              <Mail className="absolute left-4 top-[42px] w-5 h-5 text-surface-400" />
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={registerData.email}
                onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                className="pl-12"
                required
              />
            </div>

            <div className="relative">
              <User className="absolute left-4 top-[42px] w-5 h-5 text-surface-400" />
              <Input
                label="Username"
                placeholder="Choose a username"
                value={registerData.username}
                onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })}
                className="pl-12"
                required
              />
            </div>

            <div className="relative">
              <Lock className="absolute left-4 top-[42px] w-5 h-5 text-surface-400" />
              <Input
                label="Password"
                type="password"
                placeholder="At least 8 characters"
                value={registerData.password}
                onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })}
                className="pl-12"
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
              placeholder="How you appear on the leaderboard"
              value={registerData.name}
              onChange={(e) => setRegisterData({ ...registerData, name: e.target.value })}
            />

            <Input
              label="Starting Bankroll"
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
                { value: 'conservative', label: 'Conservative — Smaller stakes, steadier returns' },
                { value: 'balanced', label: 'Balanced — Moderate risk, moderate reward' },
                { value: 'aggressive', label: 'Aggressive — Larger stakes, bigger swings' },
              ]}
            />

            <label className="flex items-start gap-3 text-sm cursor-pointer p-3 rounded-xl bg-surface-50 dark:bg-surface-800 border border-surface-200 dark:border-surface-700">
              <input
                type="checkbox"
                checked={registerData.confirmAge}
                onChange={(e) => setRegisterData({ ...registerData, confirmAge: e.target.checked })}
                className="mt-0.5 w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                required
              />
              <span className="text-surface-600 dark:text-surface-300">
                I confirm I am <strong className="text-surface-900 dark:text-white">21 or older</strong> and accept the{' '}
                <a href="/terms" target="_blank" className="text-primary-600 dark:text-primary-400 hover:underline font-medium">
                  Terms
                </a>
              </span>
            </label>

            {error && (
              <ErrorMessage
                message={error}
                onDismiss={() => setError('')}
              />
            )}

            <Button type="submit" className="w-full" size="lg" isLoading={isLoading}>
              Get Started
            </Button>
          </form>
        )}

        <p className="text-xs text-surface-500 dark:text-surface-400 text-center mt-8">
          This is a simulation platform for educational purposes.
        </p>
      </Card>
    </div>
  );
}
