import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';
import { Bell, Webhook, MessageCircle, Mail, Smartphone, Clock } from 'lucide-react';

export default function Alerts() {
  const queryClient = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.alerts.list(),
  });

  const { data: alertTypes } = useQuery({
    queryKey: ['alert-types'],
    queryFn: () => api.alerts.getTypes(),
  });

  const { data: webhooks, isLoading: webhooksLoading } = useQuery({
    queryKey: ['webhooks'],
    queryFn: () => api.webhooks.list(),
  });

  const { data: telegramStatus } = useQuery({
    queryKey: ['telegram-status'],
    queryFn: () => api.telegram.getStatus(),
  });

  const createAlertMutation = useMutation({
    mutationFn: api.alerts.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setShowCreate(false);
    },
  });

  const toggleAlertMutation = useMutation({
    mutationFn: (alertId: number) => api.alerts.toggle(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const deleteAlertMutation = useMutation({
    mutationFn: (alertId: number) => api.alerts.delete(alertId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const linkTelegramMutation = useMutation({
    mutationFn: () => api.telegram.generateLinkCode(),
  });

  const handleCreateAlert = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createAlertMutation.mutate({
      name: formData.get('name') as string,
      alert_type: formData.get('alert_type') as string,
      sport: formData.get('sport') as string || undefined,
      min_edge: formData.get('min_edge') ? parseFloat(formData.get('min_edge') as string) / 100 : undefined,
      notify_email: formData.get('notify_email') === 'on',
      notify_push: formData.get('notify_push') === 'on',
      notify_telegram: formData.get('notify_telegram') === 'on',
    });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">Notifications</h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Get notified when edges appear.
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)} size="lg">
          {showCreate ? 'Cancel' : 'Set Alert'}
        </Button>
      </div>

      {/* Create Alert Form */}
      {showCreate && (
        <Card padding="lg">
          <h2 className="text-h2 text-surface-900 dark:text-white mb-6">New Alert</h2>
          <form onSubmit={handleCreateAlert} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Input name="name" placeholder="Alert Name" required />
              <Select name="alert_type" required>
                <option value="">Select Alert Type</option>
                {alertTypes && Object.entries(alertTypes).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </Select>
              <Select name="sport">
                <option value="">All Sports</option>
                {SPORTS.map(sport => (
                  <option key={sport} value={sport}>{sport.replace('_', ' ')}</option>
                ))}
              </Select>
              <Input name="min_edge" type="number" step="0.1" placeholder="Minimum Edge %" />
            </div>
            <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
              <p className="text-sm font-semibold text-surface-900 dark:text-white mb-4">Notification Methods</p>
              <div className="flex flex-wrap gap-6">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="notify_push"
                    defaultChecked
                    className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                  />
                  <Smartphone className="w-5 h-5 text-surface-500" />
                  <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Push Notification</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="notify_email"
                    className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                  />
                  <Mail className="w-5 h-5 text-surface-500" />
                  <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Email</span>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    name="notify_telegram"
                    className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                  />
                  <MessageCircle className="w-5 h-5 text-surface-500" />
                  <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Telegram</span>
                </label>
              </div>
            </div>
            <Button type="submit" disabled={createAlertMutation.isPending}>
              {createAlertMutation.isPending ? 'Setting up...' : 'Set Alert'}
            </Button>
          </form>
        </Card>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Alerts List */}
        <div className="lg:col-span-2">
          <Card padding="lg">
            <h2 className="text-h2 text-surface-900 dark:text-white mb-6">Your Alerts</h2>

            {alertsLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner text="Analyzing..." />
              </div>
            ) : alerts?.length === 0 ? (
              <EmptyState
                icon={Bell}
                title="No alerts set"
                description="Set alerts to stay informed."
                action={{
                  label: 'Set Your First Alert',
                  onClick: () => setShowCreate(true),
                }}
              />
            ) : (
              <div className="space-y-4">
                {alerts?.map(alert => (
                  <div
                    key={alert.id}
                    className={`border border-surface-200 dark:border-surface-700 rounded-xl p-5 transition-opacity ${
                      !alert.is_active ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-surface-900 dark:text-white">{alert.name}</span>
                          <Badge variant={alert.is_active ? 'success' : 'neutral'}>
                            {alert.is_active ? 'Active' : 'Paused'}
                          </Badge>
                        </div>
                        <p className="text-sm text-surface-500 dark:text-surface-400">
                          Type: {alert.alert_type}
                          {alert.sport && ` | Sport: ${alert.sport}`}
                          {alert.min_edge && ` | Min Edge: ${(alert.min_edge * 100).toFixed(1)}%`}
                        </p>
                        <div className="flex items-center gap-2 mt-3">
                          {alert.notify_push && <Badge variant="outline">Push</Badge>}
                          {alert.notify_email && <Badge variant="outline">Email</Badge>}
                          {alert.notify_telegram && <Badge variant="outline">Telegram</Badge>}
                        </div>
                        <div className="flex items-center gap-1.5 mt-3 text-xs text-surface-400">
                          <Clock className="w-3.5 h-3.5" />
                          <span>Triggered {alert.trigger_count} times | Last: {formatDate(alert.last_triggered)}</span>
                        </div>
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleAlertMutation.mutate(alert.id)}
                        >
                          {alert.is_active ? 'Pause' : 'Resume'}
                        </Button>
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => deleteAlertMutation.mutate(alert.id)}
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Telegram Integration */}
          <Card padding="lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-primary-50 dark:bg-primary-500/10">
                <MessageCircle className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              </div>
              <h2 className="text-h2 text-surface-900 dark:text-white">Telegram</h2>
            </div>
            {telegramStatus?.linked ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Badge variant="success">Connected</Badge>
                  <span className="text-sm text-surface-600 dark:text-surface-400">
                    @{telegramStatus.username}
                  </span>
                </div>
                <div className="space-y-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_recommendations}
                      className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                      readOnly
                    />
                    <span className="text-sm text-surface-700 dark:text-surface-300">Recommendations</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_results}
                      className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                      readOnly
                    />
                    <span className="text-sm text-surface-700 dark:text-surface-300">Bet Results</span>
                  </label>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_alerts}
                      className="w-5 h-5 rounded-lg border-surface-300 text-primary-600 focus:ring-primary-500 focus:ring-offset-0"
                      readOnly
                    />
                    <span className="text-sm text-surface-700 dark:text-surface-300">Alerts</span>
                  </label>
                </div>
              </div>
            ) : telegramStatus?.configured ? (
              <div className="space-y-4">
                <p className="text-sm text-surface-600 dark:text-surface-400">
                  Instant alerts. Delivered seamlessly.
                </p>
                {linkTelegramMutation.data ? (
                  <div className="space-y-3">
                    <p className="text-sm text-surface-700 dark:text-surface-300">Connect now:</p>
                    <a
                      href={linkTelegramMutation.data.deep_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block w-full"
                    >
                      <Button className="w-full">Open Telegram</Button>
                    </a>
                  </div>
                ) : (
                  <Button
                    onClick={() => linkTelegramMutation.mutate()}
                    disabled={linkTelegramMutation.isPending}
                    className="w-full"
                  >
                    {linkTelegramMutation.isPending ? 'Setting up...' : 'Link Telegram'}
                  </Button>
                )}
              </div>
            ) : (
              <p className="text-sm text-surface-500 dark:text-surface-400">
                Telegram bot not configured
              </p>
            )}
          </Card>

          {/* Webhooks */}
          <Card padding="lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-surface-100 dark:bg-surface-800">
                <Webhook className="w-5 h-5 text-surface-600 dark:text-surface-400" />
              </div>
              <h2 className="text-h2 text-surface-900 dark:text-white">Webhooks</h2>
            </div>
            {webhooksLoading ? (
              <div className="flex justify-center py-4">
                <LoadingSpinner size="sm" />
              </div>
            ) : webhooks?.length === 0 ? (
              <EmptyState
                icon={Webhook}
                title="No webhooks configured"
                description="Webhooks allow you to send alerts to external services"
                className="py-4"
              />
            ) : (
              <div className="space-y-3">
                {webhooks?.map(webhook => (
                  <div key={webhook.id} className="flex items-center justify-between p-3 bg-surface-50 dark:bg-surface-800 rounded-xl">
                    <span className="font-medium text-surface-900 dark:text-white">{webhook.name}</span>
                    <Badge variant={webhook.is_active ? 'success' : 'neutral'}>
                      {webhook.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
