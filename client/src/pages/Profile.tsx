import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, Button, Input, Select, Badge } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { User, DollarSign, Shield, Save, Globe, CheckCircle2, XCircle, Send, Link2 } from 'lucide-react';

const CURRENCIES = [
  { value: 'USD', label: 'USD ($) - US Dollar' },
  { value: 'EUR', label: 'EUR (€) - Euro' },
  { value: 'GBP', label: 'GBP (£) - British Pound' },
  { value: 'CAD', label: 'CAD (C$) - Canadian Dollar' },
  { value: 'AUD', label: 'AUD (A$) - Australian Dollar' },
  { value: 'BTC', label: 'BTC (₿) - Bitcoin' },
  { value: 'ETH', label: 'ETH (Ξ) - Ethereum' },
];

export default function Profile() {
  const { client, updateClient, user } = useAuth();
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [formData, setFormData] = useState({
    name: client?.name || '',
    bankroll: client?.bankroll?.toString() || '10000',
    risk_profile: client?.risk_profile || 'balanced',
  });

  const [profileData, setProfileData] = useState({
    display_name: user?.display_name || '',
    preferred_currency: user?.preferred_currency || 'USD',
  });

  const [ageVerification, setAgeVerification] = useState({
    date_of_birth: '',
    confirm_age: false,
  });

  const { data: telegramStatus } = useQuery({
    queryKey: ['telegram-status'],
    queryFn: () => api.telegram.getStatus(),
  });

  const updateProfileMutation = useMutation({
    mutationFn: (data: { display_name?: string; preferred_currency?: string }) =>
      api.account.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    },
  });

  const verifyAgeMutation = useMutation({
    mutationFn: (data: { date_of_birth: string; confirm_age: boolean }) =>
      api.account.verifyAge(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user'] });
    },
  });

  const linkTelegramMutation = useMutation({
    mutationFn: () => api.telegram.generateLinkCode(),
  });

  const unlinkTelegramMutation = useMutation({
    mutationFn: () => api.telegram.unlink(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['telegram-status'] });
    },
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
      
      await updateProfileMutation.mutateAsync({
        display_name: profileData.display_name || undefined,
        preferred_currency: profileData.preferred_currency,
      });
      
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to update profile:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAgeVerification = async () => {
    if (!ageVerification.date_of_birth || !ageVerification.confirm_age) return;
    await verifyAgeMutation.mutateAsync(ageVerification);
  };

  const handleLinkTelegram = async () => {
    const result = await linkTelegramMutation.mutateAsync();
    if (result.deep_link) {
      window.open(result.deep_link, '_blank');
    }
  };

  const riskDescriptions = {
    conservative: 'Lower stakes with focus on high-probability bets. Typical stake: 0.5% of bankroll.',
    balanced: 'Moderate risk with a balance of value and safety. Typical stake: 1% of bankroll.',
    aggressive: 'Higher stakes targeting maximum edge opportunities. Typical stake: 2% of bankroll.',
  };

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
          Profile
        </h1>
        <p className="text-surface-500 mt-1">
          Your preferences. Your edge.
        </p>
      </div>

      {!user?.is_age_verified && (
        <Card className="border-warning-200 dark:border-warning-500/30 bg-warning-50/50 dark:bg-warning-500/10">
          <div className="flex items-center gap-3 mb-4">
            <Shield className="w-5 h-5 text-warning-600 dark:text-warning-400" />
            <h2 className="font-semibold text-warning-800 dark:text-warning-200">Age Verification Required</h2>
          </div>
          <p className="text-sm text-warning-700 dark:text-warning-300 mb-4">
            You must be 21 or older to use this platform. Verify your age to continue.
          </p>
          <div className="space-y-3">
            <Input
              type="date"
              label="Date of Birth"
              value={ageVerification.date_of_birth}
              onChange={(e) => setAgeVerification({ ...ageVerification, date_of_birth: e.target.value })}
              max={new Date(Date.now() - 21 * 365.25 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}
            />
            <label className="flex items-center gap-2 text-sm text-warning-700 dark:text-warning-300">
              <input
                type="checkbox"
                checked={ageVerification.confirm_age}
                onChange={(e) => setAgeVerification({ ...ageVerification, confirm_age: e.target.checked })}
                className="rounded border-warning-300"
              />
              I confirm that I am 21 years of age or older
            </label>
            <Button
              onClick={handleAgeVerification}
              disabled={!ageVerification.date_of_birth || !ageVerification.confirm_age || verifyAgeMutation.isPending}
            >
              {verifyAgeMutation.isPending ? 'Verifying...' : 'Verify'}
            </Button>
            {verifyAgeMutation.isError && (
              <p className="text-sm text-red-600">You must be 21 or older to use this platform.</p>
            )}
          </div>
        </Card>
      )}

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
                Your account details.
              </p>
            </div>
          </div>

          <div className="space-y-4">
            <Input
              label="Client Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Enter your name"
              required
            />
            
            <Input
              label="Display Name (shown on leaderboard)"
              value={profileData.display_name}
              onChange={(e) => setProfileData({ ...profileData, display_name: e.target.value })}
              placeholder="Choose a display name"
            />
            
            <div className="flex items-center gap-2 pt-2">
              {user?.is_age_verified ? (
                <Badge variant="success">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Age Verified
                </Badge>
              ) : (
                <Badge variant="warning">
                  <XCircle className="w-3 h-3 mr-1" />
                  Age Not Verified
                </Badge>
              )}
              {user?.is_verified && (
                <Badge variant="success">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  Email Verified
                </Badge>
              )}
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-500/10">
              <Globe className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Currency Preferences
              </h2>
              <p className="text-sm text-surface-500">
                Choose your display currency.
              </p>
            </div>
          </div>

          <Select
            label="Preferred Currency"
            value={profileData.preferred_currency}
            onChange={(e) => setProfileData({ ...profileData, preferred_currency: e.target.value })}
            options={CURRENCIES}
          />
          
          <p className="text-xs text-surface-500 mt-2">
            Amounts display in your preferred currency. Rates update hourly.
          </p>
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
                Your available capital.
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
            Stakes are calculated as a percentage of bankroll based on edge and risk.
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
                Determines stake sizing.
              </p>
            </div>
          </div>

          <Select
            label="Risk Tolerance"
            value={formData.risk_profile}
            onChange={(e) => setFormData({ ...formData, risk_profile: e.target.value as 'conservative' | 'balanced' | 'aggressive' })}
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
              Changes saved.
            </span>
          )}
        </div>
      </form>

      <Card>
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-blue-50 dark:bg-blue-500/10">
            <Send className="w-5 h-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h2 className="font-semibold text-surface-900 dark:text-white">
              Telegram Notifications
            </h2>
            <p className="text-sm text-surface-500">
              Instant alerts. Delivered seamlessly.
            </p>
          </div>
        </div>

        {telegramStatus?.linked ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge variant="success">
                <Link2 className="w-3 h-3 mr-1" />
                Connected
              </Badge>
              <span className="text-sm text-surface-600 dark:text-surface-400">
                @{telegramStatus.username}
              </span>
            </div>
            <Button
              variant="outline"
              onClick={() => unlinkTelegramMutation.mutate()}
              disabled={unlinkTelegramMutation.isPending}
            >
              {unlinkTelegramMutation.isPending ? 'Unlinking...' : 'Unlink Telegram'}
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-surface-600 dark:text-surface-400">
              Link Telegram for picks, results, and alerts.
            </p>
            <Button onClick={handleLinkTelegram} disabled={linkTelegramMutation.isPending}>
              <Send className="w-4 h-4" />
              {linkTelegramMutation.isPending ? 'Generating Link...' : 'Link Telegram'}
            </Button>
            {linkTelegramMutation.data?.deep_link && (
              <p className="text-sm text-surface-500">
                Tap 'Start' in the Telegram bot to connect.
              </p>
            )}
          </div>
        )}
      </Card>

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
