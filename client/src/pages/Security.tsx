import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { api } from '@/lib/api';
import { Monitor, Activity, Key, Smartphone, AlertTriangle } from 'lucide-react';

export default function Security() {
  const queryClient = useQueryClient();
  const [showSetup2FA, setShowSetup2FA] = useState(false);
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [setupData, setSetupData] = useState<{
    secret: string;
    qr_code: string;
    backup_codes: string[];
  } | null>(null);

  const { data: twoFAStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['2fa-status'],
    queryFn: () => api.security.get2FAStatus(),
  });

  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.security.getSessions(),
  });

  const { data: auditLogs, isLoading: logsLoading } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => api.security.getAuditLogs(20),
  });

  const setup2FAMutation = useMutation({
    mutationFn: () => api.security.setup2FA(),
    onSuccess: (data) => {
      setSetupData(data);
      setShowSetup2FA(true);
    },
  });

  const enable2FAMutation = useMutation({
    mutationFn: (code: string) => api.security.enable2FA(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa-status'] });
      setShowSetup2FA(false);
      setSetupData(null);
      setVerifyCode('');
    },
  });

  const disable2FAMutation = useMutation({
    mutationFn: (code: string) => api.security.disable2FA(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['2fa-status'] });
      setDisableCode('');
    },
  });

  const revokeSessionMutation = useMutation({
    mutationFn: (sessionId: number) => api.security.revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  const revokeAllMutation = useMutation({
    mutationFn: () => api.security.revokeAllSessions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] });
    },
  });

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const parseUserAgent = (ua: string | null) => {
    if (!ua) return 'Unknown Device';
    if (ua.includes('Chrome')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return 'Browser';
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-display text-surface-900 dark:text-white">Security</h1>
        <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
          Your account. Protected.
        </p>
      </div>

      {/* 2FA and Sessions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Two-Factor Authentication */}
        <Card padding="lg">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-xl bg-primary-50 dark:bg-primary-500/10">
              <Key className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <h2 className="text-h2 text-surface-900 dark:text-white">Two-Factor</h2>
          </div>

          {statusLoading ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner size="sm" text="Analyzing..." />
            </div>
          ) : twoFAStatus?.enabled ? (
            <div className="space-y-6">
              <div className="flex items-center gap-3">
                <Badge variant="success">Enabled</Badge>
                <span className="text-sm text-surface-500 dark:text-surface-400">
                  {twoFAStatus.backup_codes_remaining} backup codes remaining
                </span>
              </div>
              <p className="text-sm text-surface-600 dark:text-surface-400">
                Your account is protected with two-factor authentication.
              </p>
              <div className="pt-6 border-t border-surface-200 dark:border-surface-700">
                <p className="text-sm font-semibold text-surface-900 dark:text-white mb-3">Disable 2FA</p>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    placeholder="Enter 2FA code"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    maxLength={6}
                  />
                  <Button
                    variant="danger"
                    onClick={() => disable2FAMutation.mutate(disableCode)}
                    disabled={disableCode.length !== 6 || disable2FAMutation.isPending}
                  >
                    Disable
                  </Button>
                </div>
              </div>
            </div>
          ) : showSetup2FA && setupData ? (
            <div className="space-y-6">
              <p className="text-sm text-surface-600 dark:text-surface-400">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>
              <div className="flex justify-center p-4 bg-white rounded-xl">
                <img
                  src={`data:image/png;base64,${setupData.qr_code}`}
                  alt="2FA QR Code"
                  className="w-48 h-48"
                />
              </div>
              <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
                <p className="text-xs font-medium text-surface-500 dark:text-surface-400 mb-2">
                  Manual entry key:
                </p>
                <code className="text-sm bg-surface-100 dark:bg-surface-700 px-3 py-1.5 rounded-lg text-surface-900 dark:text-white font-mono">
                  {setupData.secret}
                </code>
              </div>
              <div className="p-4 bg-warning-50 dark:bg-warning-500/10 border border-warning-200 dark:border-warning-500/30 rounded-xl">
                <div className="flex items-center gap-2 mb-3">
                  <AlertTriangle className="w-5 h-5 text-warning-600 dark:text-warning-400" />
                  <p className="font-semibold text-warning-700 dark:text-warning-300">
                    Save your backup codes!
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {setupData.backup_codes.map((code, idx) => (
                    <code key={idx} className="text-sm bg-white dark:bg-surface-800 px-3 py-2 rounded-lg text-center text-surface-900 dark:text-white font-mono">
                      {code}
                    </code>
                  ))}
                </div>
              </div>
              <div className="flex gap-2">
                <Input
                  type="text"
                  placeholder="Enter 6-digit code to verify"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value)}
                  maxLength={6}
                />
                <Button
                  onClick={() => enable2FAMutation.mutate(verifyCode)}
                  disabled={verifyCode.length !== 6 || enable2FAMutation.isPending}
                >
                  Verify & Enable
                </Button>
              </div>
              <Button variant="outline" onClick={() => setShowSetup2FA(false)} className="w-full">
                Cancel
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-surface-600 dark:text-surface-400">
                Add an extra layer of security to your account. Two-factor authentication is required for all users.
              </p>
              <Button
                onClick={() => setup2FAMutation.mutate()}
                disabled={setup2FAMutation.isPending}
              >
                <Smartphone className="w-4 h-4" />
                {setup2FAMutation.isPending ? 'Turning on...' : 'Turn On'}
              </Button>
            </div>
          )}
        </Card>

        {/* Active Sessions */}
        <Card padding="lg">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-surface-100 dark:bg-surface-800">
                <Monitor className="w-5 h-5 text-surface-600 dark:text-surface-400" />
              </div>
              <h2 className="text-h2 text-surface-900 dark:text-white">Active Sessions</h2>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => revokeAllMutation.mutate()}
              disabled={revokeAllMutation.isPending}
            >
              Revoke All Others
            </Button>
          </div>

          {sessionsLoading ? (
            <div className="flex justify-center py-4">
              <LoadingSpinner size="sm" />
            </div>
          ) : sessions?.length === 0 ? (
            <EmptyState
              icon={Monitor}
              title="No active sessions"
              description="Your sessions will appear here"
              className="py-4"
            />
          ) : (
            <div className="space-y-3">
              {sessions?.map(session => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-4 border border-surface-200 dark:border-surface-700 rounded-xl"
                >
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-surface-900 dark:text-white">
                        {parseUserAgent(session.user_agent)}
                      </span>
                      {session.is_current && (
                        <Badge variant="success">Current</Badge>
                      )}
                    </div>
                    <p className="text-sm text-surface-500 dark:text-surface-400">
                      {session.ip_address || 'Unknown IP'} • {formatDate(session.created_at)}
                    </p>
                  </div>
                  {!session.is_current && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => revokeSessionMutation.mutate(session.id)}
                    >
                      Revoke
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Audit Logs */}
      <Card padding="lg">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-xl bg-surface-100 dark:bg-surface-800">
            <Activity className="w-5 h-5 text-surface-600 dark:text-surface-400" />
          </div>
          <h2 className="text-h2 text-surface-900 dark:text-white">Recent Security Activity</h2>
        </div>

        {logsLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner text="Analyzing..." />
          </div>
        ) : auditLogs?.length === 0 ? (
          <EmptyState
            icon={Activity}
            title="No recent activity"
            description="Your security activity will appear here"
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-surface-500 dark:text-surface-400 border-b border-surface-200 dark:border-surface-700">
                  <th className="pb-4 pr-4 font-medium">Action</th>
                  <th className="pb-4 pr-4 font-medium">IP Address</th>
                  <th className="pb-4 pr-4 font-medium">Status</th>
                  <th className="pb-4 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs?.map(log => (
                  <tr key={log.id} className="border-b border-surface-200 dark:border-surface-700 last:border-0">
                    <td className="py-4 pr-4">
                      <span className="font-medium text-surface-900 dark:text-white">
                        {log.action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                      {log.resource_type && (
                        <span className="text-sm text-surface-500 dark:text-surface-400 ml-2">
                          ({log.resource_type})
                        </span>
                      )}
                    </td>
                    <td className="py-4 pr-4 text-surface-600 dark:text-surface-400">
                      {log.ip_address || 'Unknown'}
                    </td>
                    <td className="py-4 pr-4">
                      <Badge variant={log.status === 'success' ? 'success' : 'danger'}>
                        {log.status}
                      </Badge>
                    </td>
                    <td className="py-4 text-surface-600 dark:text-surface-400">
                      {formatDate(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
