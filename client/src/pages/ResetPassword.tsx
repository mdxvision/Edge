import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, Input, Card } from '@/components/ui';
import { TrendingUp, Mail, Lock, CheckCircle } from 'lucide-react';
import { api } from '@/lib/api';

type Mode = 'request' | 'reset' | 'success';

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [mode, setMode] = useState<Mode>(token ? 'reset' : 'request');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [email, setEmail] = useState('');
  const [passwords, setPasswords] = useState({
    password: '',
    confirmPassword: '',
  });

  const handleRequestReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.account.forgotPassword(email);
      setMode('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (passwords.password !== passwords.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (passwords.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setIsLoading(true);

    try {
      await api.account.resetPassword(token!, passwords.password);
      setMode('success');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset password');
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
            {mode === 'request' && 'Reset Password'}
            {mode === 'reset' && 'Create New Password'}
            {mode === 'success' && 'Success!'}
          </h1>
          <p className="text-surface-500 mt-2">
            {mode === 'request' && 'Enter your email to receive a reset link'}
            {mode === 'reset' && 'Enter your new password below'}
            {mode === 'success' && (token ? 'Your password has been reset' : 'Check your email for the reset link')}
          </p>
        </div>

        {mode === 'request' && (
          <form onSubmit={handleRequestReset} className="space-y-4">
            <div className="relative">
              <Mail className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="Email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="pl-10"
                required
              />
            </div>

            {error && (
              <p className="text-sm text-danger-500 text-center">{error}</p>
            )}

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Send Reset Link
            </Button>

            <button
              type="button"
              onClick={() => navigate('/login')}
              className="w-full text-sm text-primary-600 hover:underline"
            >
              Back to login
            </button>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div className="relative">
              <Lock className="absolute left-3 top-9 w-4 h-4 text-surface-400" />
              <Input
                label="New Password"
                type="password"
                placeholder="Create a password (min 8 characters)"
                value={passwords.password}
                onChange={(e) => setPasswords({ ...passwords, password: e.target.value })}
                className="pl-10"
                required
                minLength={8}
              />
            </div>

            <Input
              label="Confirm Password"
              type="password"
              placeholder="Confirm your password"
              value={passwords.confirmPassword}
              onChange={(e) => setPasswords({ ...passwords, confirmPassword: e.target.value })}
              required
            />

            {error && (
              <p className="text-sm text-danger-500 text-center">{error}</p>
            )}

            <Button type="submit" className="w-full" isLoading={isLoading}>
              Reset Password
            </Button>
          </form>
        )}

        {mode === 'success' && (
          <div className="text-center space-y-4">
            <div className="flex justify-center">
              <CheckCircle className="w-16 h-16 text-success-500" />
            </div>
            <p className="text-surface-600 dark:text-surface-400">
              {token
                ? 'Your password has been successfully reset. You can now login with your new password.'
                : 'If an account exists with that email, you will receive a password reset link shortly.'}
            </p>
            <Button onClick={() => navigate('/login')} className="w-full">
              Go to Login
            </Button>
          </div>
        )}
      </Card>
    </div>
  );
}
