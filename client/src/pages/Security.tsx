import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import { api } from '@/lib/api';

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
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Security Settings</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">Manage your account security</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Two-Factor Authentication</h2>
          
          {statusLoading ? (
            <p className="text-gray-500">Loading...</p>
          ) : twoFAStatus?.enabled ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge variant="success">Enabled</Badge>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {twoFAStatus.backup_codes_remaining} backup codes remaining
                </span>
              </div>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Your account is protected with two-factor authentication.
              </p>
              <div className="border-t dark:border-gray-700 pt-4">
                <p className="text-sm font-medium mb-2 dark:text-white">Disable 2FA</p>
                <div className="flex gap-2">
                  <Input
                    type="text"
                    placeholder="Enter 2FA code"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    maxLength={6}
                  />
                  <Button
                    variant="destructive"
                    onClick={() => disable2FAMutation.mutate(disableCode)}
                    disabled={disableCode.length !== 6 || disable2FAMutation.isPending}
                  >
                    Disable
                  </Button>
                </div>
              </div>
            </div>
          ) : showSetup2FA && setupData ? (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
              </p>
              <div className="flex justify-center p-4 bg-white rounded-lg">
                <img
                  src={`data:image/png;base64,${setupData.qr_code}`}
                  alt="2FA QR Code"
                  className="w-48 h-48"
                />
              </div>
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <p className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-2">
                  Manual entry key:
                </p>
                <code className="text-sm bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded dark:text-white">
                  {setupData.secret}
                </code>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200 mb-2">
                  Save your backup codes!
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {setupData.backup_codes.map((code, idx) => (
                    <code key={idx} className="text-sm bg-white dark:bg-gray-800 px-2 py-1 rounded text-center dark:text-white">
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
              <Button variant="outline" onClick={() => setShowSetup2FA(false)}>
                Cancel
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Add an extra layer of security to your account. Two-factor authentication is required for all users.
              </p>
              <Button
                onClick={() => setup2FAMutation.mutate()}
                disabled={setup2FAMutation.isPending}
              >
                {setup2FAMutation.isPending ? 'Setting up...' : 'Set Up 2FA'}
              </Button>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold dark:text-white">Active Sessions</h2>
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
            <p className="text-gray-500">Loading...</p>
          ) : sessions?.length === 0 ? (
            <p className="text-gray-500 dark:text-gray-400">No active sessions</p>
          ) : (
            <div className="space-y-3">
              {sessions?.map(session => (
                <div
                  key={session.id}
                  className="flex items-center justify-between p-3 border dark:border-gray-700 rounded-lg"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium dark:text-white">
                        {parseUserAgent(session.user_agent)}
                      </span>
                      {session.is_current && (
                        <Badge variant="success">Current</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
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

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4 dark:text-white">Recent Security Activity</h2>
        
        {logsLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : auditLogs?.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400">No recent activity</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <th className="pb-2 pr-4">Action</th>
                  <th className="pb-2 pr-4">IP Address</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs?.map(log => (
                  <tr key={log.id} className="border-b dark:border-gray-700 last:border-0">
                    <td className="py-3 pr-4">
                      <span className="font-medium dark:text-white">
                        {log.action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                      {log.resource_type && (
                        <span className="text-sm text-gray-500 dark:text-gray-400 ml-2">
                          ({log.resource_type})
                        </span>
                      )}
                    </td>
                    <td className="py-3 pr-4 text-gray-600 dark:text-gray-300">
                      {log.ip_address || 'Unknown'}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant={log.status === 'success' ? 'success' : 'destructive'}>
                        {log.status}
                      </Badge>
                    </td>
                    <td className="py-3 text-gray-600 dark:text-gray-300">
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
