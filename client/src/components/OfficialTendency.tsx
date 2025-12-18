import { useState } from 'react';
import { clsx } from 'clsx';
import { ChevronDown, ChevronUp, User, TrendingUp, TrendingDown, AlertCircle } from 'lucide-react';
import Badge from '@/components/ui/Badge';

interface OfficialTendency {
  direction: 'over' | 'under' | 'neutral';
  strength: number;
  confidence: 'high' | 'medium' | 'low';
  sample_size: number;
}

interface OfficialData {
  id: number;
  name: string;
  sport: string;
  years_experience: number;
  games_officiated: number;
  over_percentage: number;
  over_wins: number;
  under_wins: number;
  avg_total_score?: number;
  tendency: OfficialTendency;
  tendency_label: string;
  // Sport-specific
  avg_fouls_per_game?: number;
  avg_penalties_per_game?: number;
  strike_zone_runs_per_9?: number;
  home_team_win_pct?: number;
}

interface OfficialTendencyProps {
  official: OfficialData;
  compact?: boolean;
  showImpact?: boolean;
  className?: string;
}

export default function OfficialTendency({
  official,
  compact = false,
  showImpact = true,
  className
}: OfficialTendencyProps) {
  const [expanded, setExpanded] = useState(false);

  const tendency = official.tendency;
  const isOver = tendency.direction === 'over';
  const isUnder = tendency.direction === 'under';
  const isNeutral = tendency.direction === 'neutral';

  // Get impact badge
  const getImpactBadge = () => {
    if (isOver && official.over_percentage >= 55) {
      return { label: 'LEAN OVER', variant: 'success' as const };
    }
    if (isUnder && official.over_percentage <= 45) {
      return { label: 'LEAN UNDER', variant: 'primary' as const };
    }
    return { label: 'NEUTRAL', variant: 'neutral' as const };
  };

  const impact = getImpactBadge();

  // Compact inline badge for game cards
  if (compact) {
    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className={clsx(
          'group flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all',
          'bg-surface-50 dark:bg-surface-800/50',
          'hover:bg-surface-100 dark:hover:bg-surface-800',
          'border border-surface-200 dark:border-surface-700',
          className
        )}
      >
        <User className="w-4 h-4 text-surface-500" />
        <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
          {official.name}
        </span>
        <Badge variant={impact.variant} size="sm">
          {impact.label}
        </Badge>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-surface-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-surface-400" />
        )}
      </button>
    );
  }

  return (
    <div className={clsx(
      'rounded-xl border overflow-hidden transition-all',
      'bg-white dark:bg-surface-900',
      'border-surface-200 dark:border-surface-800',
      className
    )}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            isOver && 'bg-success-50 dark:bg-success-500/10',
            isUnder && 'bg-primary-50 dark:bg-primary-500/10',
            isNeutral && 'bg-surface-100 dark:bg-surface-800'
          )}>
            <User className={clsx(
              'w-5 h-5',
              isOver && 'text-success-600 dark:text-success-400',
              isUnder && 'text-primary-600 dark:text-primary-400',
              isNeutral && 'text-surface-500'
            )} />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-surface-900 dark:text-white">
                {official.name}
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400">
                {official.sport}
              </span>
            </div>
            <p className="text-sm text-surface-500 dark:text-surface-400">
              {official.years_experience} years exp. | {official.games_officiated} games
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* O/U Stats */}
          <div className="text-right">
            <div className="flex items-center gap-1">
              {isOver ? (
                <TrendingUp className="w-4 h-4 text-success-500" />
              ) : isUnder ? (
                <TrendingDown className="w-4 h-4 text-primary-500" />
              ) : null}
              <span className={clsx(
                'text-lg font-bold',
                isOver && 'text-success-600 dark:text-success-400',
                isUnder && 'text-primary-600 dark:text-primary-400',
                isNeutral && 'text-surface-600 dark:text-surface-400'
              )}>
                {official.over_percentage.toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              Over Rate
            </p>
          </div>

          {showImpact && (
            <Badge variant={impact.variant}>
              {impact.label}
            </Badge>
          )}

          {expanded ? (
            <ChevronUp className="w-5 h-5 text-surface-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-surface-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-surface-200 dark:border-surface-800">
          {/* O/U Record */}
          <div className="pt-4 grid grid-cols-2 gap-4">
            <div className={clsx(
              'p-3 rounded-lg',
              'bg-success-50 dark:bg-success-500/10'
            )}>
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-success-600 dark:text-success-400" />
                <span className="text-sm font-medium text-success-700 dark:text-success-300">
                  Overs
                </span>
              </div>
              <p className="text-2xl font-bold text-success-600 dark:text-success-400">
                {official.over_wins}
              </p>
            </div>

            <div className={clsx(
              'p-3 rounded-lg',
              'bg-primary-50 dark:bg-primary-500/10'
            )}>
              <div className="flex items-center gap-2 mb-1">
                <TrendingDown className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                <span className="text-sm font-medium text-primary-700 dark:text-primary-300">
                  Unders
                </span>
              </div>
              <p className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                {official.under_wins}
              </p>
            </div>
          </div>

          {/* Tendency Description */}
          {official.tendency_label && (
            <div className={clsx(
              'p-3 rounded-lg flex items-start gap-2',
              isOver && 'bg-success-50 dark:bg-success-500/10',
              isUnder && 'bg-primary-50 dark:bg-primary-500/10',
              isNeutral && 'bg-surface-50 dark:bg-surface-800/50'
            )}>
              <AlertCircle className={clsx(
                'w-4 h-4 mt-0.5',
                isOver && 'text-success-600 dark:text-success-400',
                isUnder && 'text-primary-600 dark:text-primary-400',
                isNeutral && 'text-surface-500'
              )} />
              <p className={clsx(
                'text-sm',
                isOver && 'text-success-700 dark:text-success-300',
                isUnder && 'text-primary-700 dark:text-primary-300',
                isNeutral && 'text-surface-600 dark:text-surface-400'
              )}>
                {official.tendency_label}
              </p>
            </div>
          )}

          {/* Sport-specific stats */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            {official.avg_total_score && (
              <div>
                <span className="text-surface-500 dark:text-surface-400">Avg Total:</span>
                <span className="ml-2 font-semibold text-surface-900 dark:text-white">
                  {official.avg_total_score.toFixed(1)}
                </span>
              </div>
            )}

            {official.home_team_win_pct && (
              <div>
                <span className="text-surface-500 dark:text-surface-400">Home Win %:</span>
                <span className="ml-2 font-semibold text-surface-900 dark:text-white">
                  {official.home_team_win_pct.toFixed(1)}%
                </span>
              </div>
            )}

            {official.avg_fouls_per_game && (
              <div>
                <span className="text-surface-500 dark:text-surface-400">Fouls/Game:</span>
                <span className="ml-2 font-semibold text-surface-900 dark:text-white">
                  {official.avg_fouls_per_game.toFixed(1)}
                </span>
              </div>
            )}

            {official.avg_penalties_per_game && (
              <div>
                <span className="text-surface-500 dark:text-surface-400">Penalties/Game:</span>
                <span className="ml-2 font-semibold text-surface-900 dark:text-white">
                  {official.avg_penalties_per_game.toFixed(1)}
                </span>
              </div>
            )}

            {official.strike_zone_runs_per_9 && (
              <div>
                <span className="text-surface-500 dark:text-surface-400">Runs/9:</span>
                <span className="ml-2 font-semibold text-surface-900 dark:text-white">
                  {official.strike_zone_runs_per_9.toFixed(2)}
                </span>
              </div>
            )}
          </div>

          {/* Confidence */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-surface-500 dark:text-surface-400">
              Confidence:
            </span>
            <Badge
              variant={
                tendency.confidence === 'high' ? 'success' :
                tendency.confidence === 'medium' ? 'warning' : 'neutral'
              }
              size="sm"
            >
              {tendency.confidence.toUpperCase()} ({tendency.sample_size} games)
            </Badge>
          </div>
        </div>
      )}
    </div>
  );
}

// Simple badge for inline display
export function OfficialBadge({
  name,
  overPct,
  onClick,
  className
}: {
  name: string;
  overPct: number;
  onClick?: () => void;
  className?: string;
}) {
  const isOver = overPct >= 55;
  const isUnder = overPct <= 45;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors',
        isOver && 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400',
        isUnder && 'bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400',
        !isOver && !isUnder && 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
    >
      <User className="w-3 h-3" />
      <span>{name}: {overPct.toFixed(0)}% O</span>
    </button>
  );
}
