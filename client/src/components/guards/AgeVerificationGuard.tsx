import type { ReactNode } from 'react';
import { useAuth } from '@/context/AuthContext';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { ShieldAlert, Calendar, CheckCircle } from 'lucide-react';

interface AgeVerificationGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export default function AgeVerificationGuard({ children, fallback }: AgeVerificationGuardProps) {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  if (user.is_age_verified) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  return <AgeVerificationRequired />;
}

function AgeVerificationRequired() {
  return (
    <div className="flex items-center justify-center min-h-[400px] p-6">
      <Card className="max-w-md w-full p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-warning-100 dark:bg-warning-500/20 flex items-center justify-center">
          <ShieldAlert className="w-8 h-8 text-warning-600 dark:text-warning-400" />
        </div>

        <h2 className="text-xl font-bold text-surface-900 dark:text-white mb-2">
          Age Verification Required
        </h2>

        <p className="text-surface-600 dark:text-surface-400 mb-6">
          You must verify that you are 21 years of age or older to access betting features.
          This is required by our terms of service.
        </p>

        <div className="bg-surface-50 dark:bg-surface-800 rounded-lg p-4 mb-6 text-left">
          <h3 className="font-medium text-surface-900 dark:text-white mb-3 flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            Why we require this
          </h3>
          <ul className="space-y-2 text-sm text-surface-600 dark:text-surface-400">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Compliance with gambling regulations</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Protection of minors from gambling content</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Responsible gambling practices</span>
            </li>
          </ul>
        </div>

        <Button
          onClick={() => window.location.href = '/profile?tab=verification'}
          className="w-full"
        >
          Verify Your Age
        </Button>

        <p className="text-xs text-surface-500 mt-4">
          This is a one-time verification. Your information is kept secure.
        </p>
      </Card>
    </div>
  );
}

interface TwoFARequiredGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
}

export function TwoFARequiredGuard({ children, fallback }: TwoFARequiredGuardProps) {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  if (user.totp_enabled) {
    return <>{children}</>;
  }

  if (fallback) {
    return <>{fallback}</>;
  }

  return <TwoFARequired />;
}

function TwoFARequired() {
  return (
    <div className="flex items-center justify-center min-h-[400px] p-6">
      <Card className="max-w-md w-full p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-primary-100 dark:bg-primary-500/20 flex items-center justify-center">
          <ShieldAlert className="w-8 h-8 text-primary-600 dark:text-primary-400" />
        </div>

        <h2 className="text-xl font-bold text-surface-900 dark:text-white mb-2">
          Two-Factor Authentication Required
        </h2>

        <p className="text-surface-600 dark:text-surface-400 mb-6">
          For your security, two-factor authentication must be enabled to access this feature.
        </p>

        <div className="bg-surface-50 dark:bg-surface-800 rounded-lg p-4 mb-6 text-left">
          <h3 className="font-medium text-surface-900 dark:text-white mb-3">
            Benefits of 2FA
          </h3>
          <ul className="space-y-2 text-sm text-surface-600 dark:text-surface-400">
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Protects your account from unauthorized access</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Secures your betting history and data</span>
            </li>
            <li className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-success-500 mt-0.5 flex-shrink-0" />
              <span>Required for sensitive account actions</span>
            </li>
          </ul>
        </div>

        <Button
          onClick={() => window.location.href = '/security'}
          className="w-full"
        >
          Enable Two-Factor Authentication
        </Button>
      </Card>
    </div>
  );
}
