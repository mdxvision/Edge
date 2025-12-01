import { useState } from 'react';
import { Card, Button, Input, Select } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { User, DollarSign, Shield, Save } from 'lucide-react';

export default function Profile() {
  const { client, updateClient } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    name: client?.name || '',
    bankroll: client?.bankroll?.toString() || '10000',
    risk_profile: client?.risk_profile || 'balanced',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setSuccess(false);

    try {
      await updateClient({
        name: formData.name,
        bankroll: parseFloat(formData.bankroll),
        risk_profile: formData.risk_profile as 'conservative' | 'balanced' | 'aggressive',
      });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const riskDescriptions = {
    conservative: 'Lower stakes with focus on high-probability bets. Typical stake: 0.5% of bankroll.',
    balanced: 'Moderate risk with a balance of value and safety. Typical stake: 1% of bankroll.',
    aggressive: 'Higher stakes targeting maximum edge opportunities. Typical stake: 2% of bankroll.',
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
          Profile Settings
        </h1>
        <p className="text-surface-500 mt-1">
          Manage your account and betting preferences
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-primary-50 dark:bg-primary-500/10">
              <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Personal Information
              </h2>
              <p className="text-sm text-surface-500">
                Your basic account details
              </p>
            </div>
          </div>

          <Input
            label="Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="Enter your name"
            required
          />
        </Card>

        <Card>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-success-50 dark:bg-success-500/10">
              <DollarSign className="w-5 h-5 text-success-600 dark:text-success-500" />
            </div>
            <div>
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Bankroll Management
              </h2>
              <p className="text-sm text-surface-500">
                Your available betting capital
              </p>
            </div>
          </div>

          <Input
            label="Current Bankroll ($)"
            type="number"
            min="100"
            step="100"
            value={formData.bankroll}
            onChange={(e) => setFormData({ ...formData, bankroll: e.target.value })}
            placeholder="10000"
            required
          />

          <p className="text-xs text-surface-500 mt-2">
            Stake recommendations are calculated as a percentage of your bankroll based on edge and risk profile.
          </p>
        </Card>

        <Card>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-warning-50 dark:bg-warning-500/10">
              <Shield className="w-5 h-5 text-warning-600 dark:text-warning-500" />
            </div>
            <div>
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Risk Profile
              </h2>
              <p className="text-sm text-surface-500">
                Determines stake sizing for recommendations
              </p>
            </div>
          </div>

          <Select
            label="Risk Tolerance"
            value={formData.risk_profile}
            onChange={(e) => setFormData({ ...formData, risk_profile: e.target.value })}
            options={[
              { value: 'conservative', label: 'Conservative' },
              { value: 'balanced', label: 'Balanced' },
              { value: 'aggressive', label: 'Aggressive' },
            ]}
          />

          <div className="mt-4 p-3 bg-surface-50 dark:bg-surface-800/50 rounded-lg">
            <p className="text-sm text-surface-600 dark:text-surface-400">
              {riskDescriptions[formData.risk_profile as keyof typeof riskDescriptions]}
            </p>
          </div>
        </Card>

        <div className="flex items-center gap-4">
          <Button type="submit" isLoading={isLoading} data-testid="save-button">
            <Save className="w-4 h-4" />
            Save Changes
          </Button>
          {success && (
            <span className="text-sm text-success-600 dark:text-success-500" data-testid="success-message">
              Profile updated successfully!
            </span>
          )}
        </div>
      </form>

      <Card className="border-warning-200 dark:border-warning-500/30 bg-warning-50/50 dark:bg-warning-500/5">
        <p className="text-sm text-warning-700 dark:text-warning-400">
          <strong>Disclaimer:</strong> This is a simulation platform for educational purposes only. 
          No real money is being wagered. The recommendations are based on mathematical models 
          and do not guarantee profits.
        </p>
      </Card>
    </div>
  );
}
