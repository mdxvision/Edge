import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';

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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Alerts & Notifications</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Set up custom alerts for betting opportunities</p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : 'Create Alert'}
        </Button>
      </div>

      {showCreate && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Create New Alert</h2>
          <form onSubmit={handleCreateAlert} className="space-y-4">
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
            <div className="border dark:border-gray-700 rounded-lg p-4">
              <p className="text-sm font-medium mb-3 dark:text-white">Notification Methods</p>
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" name="notify_push" defaultChecked className="rounded" />
                  <span className="text-sm dark:text-gray-300">Push Notification</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" name="notify_email" className="rounded" />
                  <span className="text-sm dark:text-gray-300">Email</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" name="notify_telegram" className="rounded" />
                  <span className="text-sm dark:text-gray-300">Telegram</span>
                </label>
              </div>
            </div>
            <Button type="submit" disabled={createAlertMutation.isPending}>
              {createAlertMutation.isPending ? 'Creating...' : 'Create Alert'}
            </Button>
          </form>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Your Alerts</h2>
            
            {alertsLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : alerts?.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400 mb-4">No alerts created yet</p>
                <Button onClick={() => setShowCreate(true)}>Create Your First Alert</Button>
              </div>
            ) : (
              <div className="space-y-3">
                {alerts?.map(alert => (
                  <div
                    key={alert.id}
                    className={`border dark:border-gray-700 rounded-lg p-4 ${
                      !alert.is_active ? 'opacity-50' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium dark:text-white">{alert.name}</span>
                          <Badge variant={alert.is_active ? 'success' : 'secondary'}>
                            {alert.is_active ? 'Active' : 'Paused'}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Type: {alert.alert_type} 
                          {alert.sport && ` | Sport: ${alert.sport}`}
                          {alert.min_edge && ` | Min Edge: ${(alert.min_edge * 100).toFixed(1)}%`}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          {alert.notify_push && <Badge variant="outline">Push</Badge>}
                          {alert.notify_email && <Badge variant="outline">Email</Badge>}
                          {alert.notify_telegram && <Badge variant="outline">Telegram</Badge>}
                        </div>
                        <p className="text-xs text-gray-400 mt-2">
                          Triggered {alert.trigger_count} times | Last: {formatDate(alert.last_triggered)}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleAlertMutation.mutate(alert.id)}
                        >
                          {alert.is_active ? 'Pause' : 'Resume'}
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
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

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Telegram Integration</h2>
            {telegramStatus?.linked ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="success">Connected</Badge>
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    @{telegramStatus.username}
                  </span>
                </div>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_recommendations}
                      className="rounded"
                      readOnly
                    />
                    <span className="text-sm dark:text-gray-300">Recommendations</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_results}
                      className="rounded"
                      readOnly
                    />
                    <span className="text-sm dark:text-gray-300">Bet Results</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={telegramStatus.notify_alerts}
                      className="rounded"
                      readOnly
                    />
                    <span className="text-sm dark:text-gray-300">Alerts</span>
                  </label>
                </div>
              </div>
            ) : telegramStatus?.configured ? (
              <div className="space-y-3">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Get instant notifications via Telegram
                </p>
                {linkTelegramMutation.data ? (
                  <div className="space-y-2">
                    <p className="text-sm dark:text-gray-300">Click to connect:</p>
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
                  >
                    {linkTelegramMutation.isPending ? 'Generating...' : 'Link Telegram'}
                  </Button>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Telegram bot not configured
              </p>
            )}
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Webhooks</h2>
            {webhooksLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : webhooks?.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                No webhooks configured. Webhooks allow you to send alerts to external services.
              </p>
            ) : (
              <div className="space-y-2">
                {webhooks?.map(webhook => (
                  <div key={webhook.id} className="text-sm">
                    <span className="font-medium dark:text-white">{webhook.name}</span>
                    <Badge variant={webhook.is_active ? 'success' : 'secondary'} className="ml-2">
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
