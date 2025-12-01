import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Button, Input, Card, Select } from '@/components/ui';
import { TrendingUp } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const { createClient } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    bankroll: '10000',
    risk_profile: 'balanced',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await createClient({
        name: formData.name,
        bankroll: parseFloat(formData.bankroll),
        risk_profile: formData.risk_profile,
      });
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

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Your Name"
            placeholder="Enter your name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />

          <Input
            label="Starting Bankroll ($)"
            type="number"
            placeholder="10000"
            min="100"
            step="100"
            value={formData.bankroll}
            onChange={(e) => setFormData({ ...formData, bankroll: e.target.value })}
            required
          />

          <Select
            label="Risk Profile"
            value={formData.risk_profile}
            onChange={(e) => setFormData({ ...formData, risk_profile: e.target.value })}
            options={[
              { value: 'conservative', label: 'Conservative - Lower stakes, safer bets' },
              { value: 'balanced', label: 'Balanced - Moderate risk and reward' },
              { value: 'aggressive', label: 'Aggressive - Higher stakes, bigger swings' },
            ]}
          />

          {error && (
            <p className="text-sm text-danger-500 text-center">{error}</p>
          )}

          <Button type="submit" className="w-full" isLoading={isLoading}>
            Get Started
          </Button>
        </form>

        <p className="text-xs text-surface-500 text-center mt-6">
          By continuing, you acknowledge this is a simulation platform for educational purposes only.
        </p>
      </Card>
    </div>
  );
}
