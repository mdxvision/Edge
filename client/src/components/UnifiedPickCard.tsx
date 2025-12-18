import { useState } from 'react';
import { clsx } from 'clsx';
import {
  ChevronDown,
  ChevronUp,
  Star,
  TrendingUp,
  Target,
  Zap,
  Info,
  CheckCircle2,
  XCircle,
  AlertTriangle
} from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';

interface Prediction {
  side: string;
  raw_edge: string;
  raw_edge_value: number;
  confidence: number;
  confidence_label: string;
  recommendation: string;
  unit_size: string;
  star_rating: number;
}

interface Analysis {
  confirming_factors: number;
  conflicting_factors: number;
  alignment_score: number;
}

interface UnifiedPickCardProps {
  gameId: number;
  game: string;
  sport: string;
  gameTime?: string;
  factors: Record<string, {
    edge: number;
    direction: string;
    signal: string;
    weight: number;
    weighted_contribution: string;
  }>;
  analysis: Analysis;
  prediction: Prediction;
  explanation: string;
  onTrackBet?: () => void;
  compact?: boolean;
}

const RECOMMENDATION_STYLES: Record<string, { bg: string; text: string; icon: typeof CheckCircle2 }> = {
  'STRONG BET': { bg: 'bg-success-500', text: 'text-white', icon: CheckCircle2 },
  'BET': { bg: 'bg-success-400', text: 'text-white', icon: CheckCircle2 },
  'LEAN': { bg: 'bg-primary-500', text: 'text-white', icon: TrendingUp },
  'MONITOR': { bg: 'bg-warning-500', text: 'text-white', icon: AlertTriangle },
  'AVOID': { bg: 'bg-surface-400', text: 'text-white', icon: XCircle },
};

export default function UnifiedPickCard({
  game,
  sport,
  gameTime,
  factors,
  analysis,
  prediction,
  explanation,
  onTrackBet,
  compact = false,
}: UnifiedPickCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const recStyle = RECOMMENDATION_STYLES[prediction.recommendation] || RECOMMENDATION_STYLES['AVOID'];
  const RecIcon = recStyle.icon;

  // Generate star display
  const stars = Array(5).fill(0).map((_, i) => i < prediction.star_rating);

  // Edge color based on value
  const edgeValue = prediction.raw_edge_value || 0;
  const edgeColor = edgeValue >= 4 ? 'text-success-500' :
                    edgeValue >= 2 ? 'text-primary-500' :
                    edgeValue >= 1 ? 'text-warning-500' : 'text-surface-500';

  // Sort factors by weight for display
  const sortedFactors = Object.entries(factors)
    .map(([key, value]) => ({
      name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
      ...value
    }))
    .sort((a, b) => (b.weight || 0) - (a.weight || 0));

  if (compact) {
    return (
      <Card padding="md" className="hover:shadow-lg transition-shadow">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant="primary">{sport}</Badge>
              <span className={clsx('px-2 py-0.5 rounded-full text-xs font-bold', recStyle.bg, recStyle.text)}>
                {prediction.recommendation}
              </span>
            </div>
            <p className="font-semibold text-surface-900 dark:text-white truncate">{prediction.side}</p>
            <p className="text-sm text-surface-500 dark:text-surface-400">{game}</p>
          </div>
          <div className="text-right ml-4">
            <p className={clsx('text-2xl font-bold', edgeColor)}>
              {prediction.raw_edge}
            </p>
            <div className="flex items-center justify-end gap-0.5 mt-1">
              {stars.map((filled, i) => (
                <Star
                  key={i}
                  className={clsx(
                    'w-3.5 h-3.5',
                    filled ? 'fill-warning-400 text-warning-400' : 'text-surface-300 dark:text-surface-600'
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header */}
      <div className="p-5 md:p-6">
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
          {/* Left side: Game info */}
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <Badge variant="primary">{sport}</Badge>
              <span className={clsx(
                'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold',
                recStyle.bg, recStyle.text
              )}>
                <RecIcon className="w-4 h-4" />
                {prediction.recommendation}
              </span>
              {gameTime && (
                <span className="text-sm text-surface-500 dark:text-surface-400">
                  {new Date(gameTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>

            <h3 className="text-xl font-bold text-surface-900 dark:text-white mb-1">
              {prediction.side}
            </h3>
            <p className="text-surface-500 dark:text-surface-400">
              {game}
            </p>
          </div>

          {/* Right side: Stats */}
          <div className="flex items-center gap-6 lg:gap-8">
            {/* Edge */}
            <div className="text-center">
              <p className="text-xs font-medium text-surface-500 dark:text-surface-400 uppercase tracking-wider mb-1">
                Edge
              </p>
              <p className={clsx('text-3xl font-bold', edgeColor)}>
                {prediction.raw_edge}
              </p>
            </div>

            {/* Confidence */}
            <div className="text-center">
              <p className="text-xs font-medium text-surface-500 dark:text-surface-400 uppercase tracking-wider mb-1">
                Confidence
              </p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                {Math.round(prediction.confidence * 100)}%
              </p>
              <p className="text-xs text-surface-500 dark:text-surface-400">
                {prediction.confidence_label}
              </p>
            </div>

            {/* Stars */}
            <div className="text-center">
              <p className="text-xs font-medium text-surface-500 dark:text-surface-400 uppercase tracking-wider mb-1">
                Rating
              </p>
              <div className="flex items-center gap-0.5">
                {stars.map((filled, i) => (
                  <Star
                    key={i}
                    className={clsx(
                      'w-5 h-5',
                      filled ? 'fill-warning-400 text-warning-400' : 'text-surface-300 dark:text-surface-600'
                    )}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Explanation */}
        <div className="mt-4 p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
          <div className="flex items-start gap-3">
            <Zap className="w-5 h-5 text-primary-500 dark:text-primary-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-surface-900 dark:text-white mb-1">Why This Pick</p>
              <p className="text-sm text-surface-600 dark:text-surface-400">
                {explanation}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {onTrackBet && (
            <Button onClick={onTrackBet} size="md">
              <Target className="w-4 h-4" />
              Track This Bet
            </Button>
          )}
          <Button
            variant="outline"
            size="md"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            <Info className="w-4 h-4" />
            {isExpanded ? 'Hide' : 'Show'} Factor Breakdown
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
      </div>

      {/* Expanded Factor Breakdown */}
      {isExpanded && (
        <div className="border-t border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/30 p-5 md:p-6">
          <h4 className="text-sm font-semibold text-surface-900 dark:text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Factor Analysis
            <span className="text-surface-500 dark:text-surface-400 font-normal">
              ({analysis.confirming_factors} confirming, {analysis.conflicting_factors} conflicting)
            </span>
          </h4>

          <div className="space-y-3">
            {sortedFactors.map((factor) => (
              <div
                key={factor.name}
                className="flex items-center justify-between p-3 bg-white dark:bg-surface-800 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-surface-900 dark:text-white">
                      {factor.name}
                    </span>
                    <span className="text-xs text-surface-500 dark:text-surface-400">
                      ({(factor.weight * 100).toFixed(0)}% weight)
                    </span>
                  </div>
                  <p className="text-sm text-surface-500 dark:text-surface-400 truncate">
                    {factor.signal}
                  </p>
                </div>
                <div className="flex items-center gap-3 ml-4">
                  <Badge
                    variant={factor.direction === 'home' || factor.direction === 'over' ? 'success' :
                             factor.direction === 'away' || factor.direction === 'under' ? 'danger' :
                             'neutral'}
                  >
                    {factor.direction}
                  </Badge>
                  <span className={clsx(
                    'font-bold',
                    factor.edge > 2 ? 'text-success-600 dark:text-success-400' :
                    factor.edge > 0.5 ? 'text-primary-600 dark:text-primary-400' :
                    'text-surface-500'
                  )}>
                    +{factor.edge.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Alignment Score */}
          <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-surface-500 dark:text-surface-400">
                Signal Alignment
              </span>
              <div className="flex items-center gap-2">
                <div className="w-32 h-2 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                  <div
                    className={clsx(
                      'h-full rounded-full',
                      analysis.alignment_score >= 0.7 ? 'bg-success-500' :
                      analysis.alignment_score >= 0.5 ? 'bg-warning-500' :
                      'bg-danger-500'
                    )}
                    style={{ width: `${analysis.alignment_score * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-surface-900 dark:text-white">
                  {Math.round(analysis.alignment_score * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* Bet Sizing */}
          <div className="mt-4 p-3 bg-primary-50 dark:bg-primary-500/10 rounded-lg">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                Suggested Bet Size
              </span>
              <span className="text-lg font-bold text-primary-600 dark:text-primary-400">
                {prediction.unit_size}
              </span>
            </div>
          </div>
        </div>
      )}
    </Card>
  );
}
