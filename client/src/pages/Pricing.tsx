import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, Button, Badge } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { Check, X, Zap, Crown, Rocket, CreditCard, ExternalLink } from 'lucide-react';

interface Plan {
  tier: string;
  features: string[];
  price_monthly?: number;
  price_yearly?: number;
  stripe_price_id_monthly?: string;
  stripe_price_id_yearly?: string;
}

const FEATURE_LABELS: Record<string, string> = {
  basic_odds: 'Basic odds display',
  limited_predictions_5_per_day: '5 predictions per day',
  single_sport: 'Single sport access',
  all_odds: 'All sportsbook odds',
  unlimited_predictions: 'Unlimited predictions',
  all_sports: 'All 15 sports',
  paper_trading: 'Paper trading simulator',
  situational_trends: 'Situational trends',
  power_ratings: 'Power ratings',
  coach_dna: 'Coach DNA analysis',
  line_movement: 'Line movement tracking',
  everything_in_premium: 'Everything in Premium',
  api_access: 'API access (50K req/mo)',
  custom_alerts: 'Custom alerts',
  priority_support: 'Priority support',
  white_label_reports: 'White-label reports',
  advanced_analytics: 'Advanced analytics',
  webhook_integrations: 'Webhook integrations',
};

const TIER_ICONS: Record<string, React.ReactNode> = {
  free: <Zap className="w-6 h-6" />,
  premium: <Crown className="w-6 h-6" />,
  pro: <Rocket className="w-6 h-6" />,
};

const TIER_COLORS: Record<string, string> = {
  free: 'text-surface-600 dark:text-surface-400',
  premium: 'text-primary-600 dark:text-primary-400',
  pro: 'text-warning-600 dark:text-warning-400',
};

export default function Pricing() {
  const { user } = useAuth();
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');

  const { data: plansData, isLoading } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => api.billing.getPlans(),
  });

  const { data: subscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.billing.getSubscription(),
    enabled: !!user,
  });

  const checkoutMutation = useMutation({
    mutationFn: (priceId: string) => api.billing.createCheckout(priceId, billingPeriod),
    onSuccess: (data) => {
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    },
  });

  const portalMutation = useMutation({
    mutationFn: () => api.billing.createPortal(),
    onSuccess: (data) => {
      if (data.portal_url) {
        window.open(data.portal_url, '_blank');
      }
    },
  });

  const plans: Plan[] = plansData?.plans || [];
  const currentTier = subscription?.tier || 'free';

  const getYearlySavings = (monthly: number, yearly: number) => {
    const monthlyTotal = monthly * 12;
    const savings = monthlyTotal - yearly;
    return Math.round((savings / monthlyTotal) * 100);
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8 max-w-6xl mx-auto">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-surface-900 dark:text-white">
          Choose Your Edge
        </h1>
        <p className="text-surface-500 mt-2">
          Unlock powerful features to maximize your betting intelligence.
        </p>
      </div>

      {/* Billing Period Toggle */}
      <div className="flex justify-center">
        <div className="bg-surface-100 dark:bg-surface-800 rounded-lg p-1 inline-flex">
          <button
            onClick={() => setBillingPeriod('monthly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'monthly'
                ? 'bg-white dark:bg-surface-700 text-surface-900 dark:text-white shadow-sm'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingPeriod('yearly')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              billingPeriod === 'yearly'
                ? 'bg-white dark:bg-surface-700 text-surface-900 dark:text-white shadow-sm'
                : 'text-surface-600 dark:text-surface-400'
            }`}
          >
            Yearly
            <Badge variant="success" className="ml-2 text-xs">
              Save 17%
            </Badge>
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="grid md:grid-cols-3 gap-6">
        {plans.map((plan) => {
          const isCurrentPlan = currentTier === plan.tier;
          const isPopular = plan.tier === 'premium';
          const priceId = billingPeriod === 'monthly'
            ? plan.stripe_price_id_monthly
            : plan.stripe_price_id_yearly;
          const price = billingPeriod === 'monthly'
            ? plan.price_monthly
            : plan.price_yearly;

          return (
            <Card
              key={plan.tier}
              className={`relative ${
                isPopular
                  ? 'border-2 border-primary-500 dark:border-primary-400'
                  : ''
              }`}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge variant="primary">Most Popular</Badge>
                </div>
              )}

              <div className="text-center mb-6">
                <div className={`inline-flex p-3 rounded-full ${
                  plan.tier === 'free'
                    ? 'bg-surface-100 dark:bg-surface-800'
                    : plan.tier === 'premium'
                    ? 'bg-primary-50 dark:bg-primary-500/10'
                    : 'bg-warning-50 dark:bg-warning-500/10'
                }`}>
                  <span className={TIER_COLORS[plan.tier]}>
                    {TIER_ICONS[plan.tier]}
                  </span>
                </div>

                <h2 className="text-xl font-bold text-surface-900 dark:text-white mt-4 capitalize">
                  {plan.tier}
                </h2>

                <div className="mt-4">
                  {plan.tier === 'free' ? (
                    <div className="text-3xl font-bold text-surface-900 dark:text-white">
                      $0
                      <span className="text-base font-normal text-surface-500">/mo</span>
                    </div>
                  ) : (
                    <>
                      <div className="text-3xl font-bold text-surface-900 dark:text-white">
                        ${billingPeriod === 'monthly' ? price : Math.round((price || 0) / 12)}
                        <span className="text-base font-normal text-surface-500">/mo</span>
                      </div>
                      {billingPeriod === 'yearly' && plan.price_monthly && plan.price_yearly && (
                        <p className="text-sm text-success-600 dark:text-success-400 mt-1">
                          Save {getYearlySavings(plan.price_monthly, plan.price_yearly)}% with annual billing
                        </p>
                      )}
                    </>
                  )}
                </div>
              </div>

              <ul className="space-y-3 mb-6">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <Check className="w-5 h-5 text-success-500 flex-shrink-0 mt-0.5" />
                    <span className="text-sm text-surface-600 dark:text-surface-300">
                      {FEATURE_LABELS[feature] || feature.replace(/_/g, ' ')}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="mt-auto">
                {isCurrentPlan ? (
                  <Button variant="outline" className="w-full" disabled>
                    Current Plan
                  </Button>
                ) : plan.tier === 'free' ? (
                  <Button variant="outline" className="w-full" disabled>
                    Free Forever
                  </Button>
                ) : (
                  <Button
                    className="w-full"
                    variant={isPopular ? 'primary' : 'outline'}
                    onClick={() => priceId && checkoutMutation.mutate(priceId)}
                    isLoading={checkoutMutation.isPending}
                    disabled={!priceId || !user}
                  >
                    <CreditCard className="w-4 h-4" />
                    {user ? 'Get Started' : 'Sign In to Subscribe'}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      {/* Manage Subscription */}
      {subscription && subscription.tier !== 'free' && (
        <Card className="max-w-md mx-auto text-center">
          <h3 className="font-semibold text-surface-900 dark:text-white mb-2">
            Manage Your Subscription
          </h3>
          <p className="text-sm text-surface-500 mb-4">
            Update payment method, view invoices, or cancel your subscription.
          </p>
          <Button
            variant="outline"
            onClick={() => portalMutation.mutate()}
            isLoading={portalMutation.isPending}
          >
            <ExternalLink className="w-4 h-4" />
            Open Billing Portal
          </Button>
        </Card>
      )}

      {/* Feature Comparison */}
      <div className="mt-12">
        <h2 className="text-2xl font-bold text-center text-surface-900 dark:text-white mb-6">
          Compare Plans
        </h2>

        <Card className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-200 dark:border-surface-700">
                <th className="text-left py-3 px-4 font-medium text-surface-600 dark:text-surface-400">
                  Feature
                </th>
                <th className="text-center py-3 px-4 font-medium text-surface-600 dark:text-surface-400">
                  Free
                </th>
                <th className="text-center py-3 px-4 font-medium text-primary-600 dark:text-primary-400">
                  Premium
                </th>
                <th className="text-center py-3 px-4 font-medium text-warning-600 dark:text-warning-400">
                  Pro
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Sports Coverage</td>
                <td className="text-center py-3 px-4">1</td>
                <td className="text-center py-3 px-4">15</td>
                <td className="text-center py-3 px-4">15</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Daily Predictions</td>
                <td className="text-center py-3 px-4">5</td>
                <td className="text-center py-3 px-4">Unlimited</td>
                <td className="text-center py-3 px-4">Unlimited</td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Paper Trading</td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Power Ratings</td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Coach DNA Analysis</td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">API Access</td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
              </tr>
              <tr>
                <td className="py-3 px-4 text-surface-700 dark:text-surface-300">Priority Support</td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><X className="w-5 h-5 mx-auto text-surface-400" /></td>
                <td className="text-center py-3 px-4"><Check className="w-5 h-5 mx-auto text-success-500" /></td>
              </tr>
            </tbody>
          </table>
        </Card>
      </div>

      {/* FAQ */}
      <div className="mt-12 max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-center text-surface-900 dark:text-white mb-6">
          Frequently Asked Questions
        </h2>

        <div className="space-y-4">
          <Card>
            <h3 className="font-semibold text-surface-900 dark:text-white">
              Can I cancel anytime?
            </h3>
            <p className="text-sm text-surface-600 dark:text-surface-400 mt-2">
              Yes! You can cancel your subscription at any time. Your access will continue until the end of your billing period.
            </p>
          </Card>

          <Card>
            <h3 className="font-semibold text-surface-900 dark:text-white">
              What payment methods do you accept?
            </h3>
            <p className="text-sm text-surface-600 dark:text-surface-400 mt-2">
              We accept all major credit cards (Visa, Mastercard, American Express) through our secure Stripe integration.
            </p>
          </Card>

          <Card>
            <h3 className="font-semibold text-surface-900 dark:text-white">
              Is my payment information secure?
            </h3>
            <p className="text-sm text-surface-600 dark:text-surface-400 mt-2">
              Absolutely. We use Stripe for payment processing and never store your card details on our servers.
            </p>
          </Card>

          <Card>
            <h3 className="font-semibold text-surface-900 dark:text-white">
              Can I upgrade or downgrade my plan?
            </h3>
            <p className="text-sm text-surface-600 dark:text-surface-400 mt-2">
              Yes, you can change your plan anytime through the billing portal. Changes take effect immediately.
            </p>
          </Card>
        </div>
      </div>

      {/* Disclaimer */}
      <Card className="border-warning-200 dark:border-warning-500/30 bg-warning-50/50 dark:bg-warning-500/5 max-w-2xl mx-auto">
        <p className="text-sm text-warning-700 dark:text-warning-400 text-center">
          <strong>Disclaimer:</strong> EdgeBet is a simulation platform for educational purposes only.
          No real money wagering. Predictions are mathematical models and do not guarantee profits.
        </p>
      </Card>
    </div>
  );
}
