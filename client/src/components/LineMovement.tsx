import { useState } from 'react';
import { clsx } from 'clsx';
import {
  ChevronDown,
  ChevronUp,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  ArrowLeftRight,
  Target,
  Clock
} from 'lucide-react';
import Badge from '@/components/ui/Badge';

interface LineAlert {
  type: 'REVERSE_LINE_MOVEMENT' | 'STEAM_MOVE' | 'SHARP_BOOK_LEAD';
  message: string;
  implication: string;
  confidence: number;
}

interface LineMovementData {
  game_id: number;
  market: string;
  opening_line: number | null;
  current_line: number | null;
  movement: string;
  direction: string | null;
  alerts: LineAlert[];
  alert_count: number;
  recommendation: string;
}

interface LineMovementProps {
  data: LineMovementData;
  matchup?: string;
  compact?: boolean;
  className?: string;
}

export default function LineMovement({
  data,
  matchup,
  compact = false,
  className
}: LineMovementProps) {
  const [expanded, setExpanded] = useState(false);

  const hasAlerts = data.alert_count > 0;
  const hasSteam = data.alerts.some(a => a.type === 'STEAM_MOVE');
  const hasRLM = data.alerts.some(a => a.type === 'REVERSE_LINE_MOVEMENT');
  const hasSharp = data.alerts.some(a => a.type === 'SHARP_BOOK_LEAD');

  // Parse movement value
  const movementValue = parseFloat(data.movement) || 0;
  const isPositiveMove = movementValue > 0;
  const isNegativeMove = movementValue < 0;
  const isSignificantMove = Math.abs(movementValue) >= 1;

  // Get alert icon and color
  const getAlertStyle = () => {
    if (hasSteam) return { icon: Zap, color: 'danger', label: 'STEAM' };
    if (hasRLM) return { icon: ArrowLeftRight, color: 'warning', label: 'RLM' };
    if (hasSharp) return { icon: Target, color: 'primary', label: 'SHARP' };
    return null;
  };

  const alertStyle = getAlertStyle();

  // Compact badge for game cards
  if (compact) {
    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className={clsx(
          'group flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all',
          'bg-surface-50 dark:bg-surface-800/50',
          'hover:bg-surface-100 dark:hover:bg-surface-800',
          'border',
          hasAlerts ? 'border-warning-300 dark:border-warning-700' : 'border-surface-200 dark:border-surface-700',
          className
        )}
      >
        {/* Movement indicator */}
        {isPositiveMove ? (
          <TrendingUp className={clsx(
            'w-4 h-4',
            isSignificantMove ? 'text-success-500' : 'text-surface-400'
          )} />
        ) : isNegativeMove ? (
          <TrendingDown className={clsx(
            'w-4 h-4',
            isSignificantMove ? 'text-danger-500' : 'text-surface-400'
          )} />
        ) : (
          <Minus className="w-4 h-4 text-surface-400" />
        )}

        {/* Line display */}
        <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
          {data.opening_line != null ? formatLine(data.opening_line, data.market) : '?'}
          <span className="mx-1 text-surface-400">→</span>
          {data.current_line != null ? formatLine(data.current_line, data.market) : '?'}
        </span>

        {/* Movement amount */}
        <span className={clsx(
          'text-xs font-semibold',
          isPositiveMove && isSignificantMove && 'text-success-600 dark:text-success-400',
          isNegativeMove && isSignificantMove && 'text-danger-600 dark:text-danger-400',
          !isSignificantMove && 'text-surface-500'
        )}>
          ({data.movement})
        </span>

        {/* Alert badges */}
        {alertStyle && (
          <Badge variant={alertStyle.color as any} size="sm">
            <alertStyle.icon className="w-3 h-3 mr-1" />
            {alertStyle.label}
          </Badge>
        )}

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
      hasAlerts ? 'border-warning-300 dark:border-warning-700' : 'border-surface-200 dark:border-surface-800',
      className
    )}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {/* Movement Icon */}
          <div className={clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            isPositiveMove && 'bg-success-50 dark:bg-success-500/10',
            isNegativeMove && 'bg-danger-50 dark:bg-danger-500/10',
            !isPositiveMove && !isNegativeMove && 'bg-surface-100 dark:bg-surface-800'
          )}>
            {isPositiveMove ? (
              <TrendingUp className="w-5 h-5 text-success-600 dark:text-success-400" />
            ) : isNegativeMove ? (
              <TrendingDown className="w-5 h-5 text-danger-600 dark:text-danger-400" />
            ) : (
              <Minus className="w-5 h-5 text-surface-500" />
            )}
          </div>

          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-surface-900 dark:text-white">
                Line Movement
              </span>
              {matchup && (
                <span className="text-sm text-surface-500 dark:text-surface-400">
                  {matchup}
                </span>
              )}
            </div>
            <p className="text-sm text-surface-500 dark:text-surface-400">
              {data.market === 'spread' ? 'Spread' : data.market === 'total' ? 'Total' : data.market}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Visual line movement */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-surface-500 dark:text-surface-400">
              {data.opening_line != null ? formatLine(data.opening_line, data.market) : '-'}
            </span>
            <div className={clsx(
              'w-8 h-0.5 rounded',
              isPositiveMove && 'bg-success-400',
              isNegativeMove && 'bg-danger-400',
              !isPositiveMove && !isNegativeMove && 'bg-surface-300 dark:bg-surface-600'
            )} />
            <span className={clsx(
              'text-lg font-bold',
              isPositiveMove && isSignificantMove && 'text-success-600 dark:text-success-400',
              isNegativeMove && isSignificantMove && 'text-danger-600 dark:text-danger-400',
              !isSignificantMove && 'text-surface-700 dark:text-surface-300'
            )}>
              {data.current_line != null ? formatLine(data.current_line, data.market) : '-'}
            </span>
          </div>

          {/* Alert count */}
          {hasAlerts && (
            <div className="flex gap-1">
              {hasSteam && (
                <Badge variant="danger" size="sm">
                  <Zap className="w-3 h-3" />
                </Badge>
              )}
              {hasRLM && (
                <Badge variant="warning" size="sm">
                  <ArrowLeftRight className="w-3 h-3" />
                </Badge>
              )}
              {hasSharp && (
                <Badge variant="primary" size="sm">
                  <Target className="w-3 h-3" />
                </Badge>
              )}
            </div>
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
          {/* Movement Timeline */}
          <div className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Movement: {data.movement}
              </span>
              {data.direction && (
                <span className="text-xs text-surface-500 dark:text-surface-400">
                  {formatDirection(data.direction)}
                </span>
              )}
            </div>

            {/* Visual timeline */}
            <div className="relative h-8 bg-surface-100 dark:bg-surface-800 rounded-lg overflow-hidden">
              <div className="absolute inset-y-0 left-1/2 w-0.5 bg-surface-300 dark:bg-surface-600" />
              {data.opening_line != null && data.current_line != null && (
                <>
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-surface-400"
                    style={{ left: '20%' }}
                    title={`Opening: ${formatLine(data.opening_line, data.market)}`}
                  />
                  <div
                    className={clsx(
                      'absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full',
                      isPositiveMove ? 'bg-success-500' : isNegativeMove ? 'bg-danger-500' : 'bg-primary-500'
                    )}
                    style={{ left: '75%' }}
                    title={`Current: ${formatLine(data.current_line, data.market)}`}
                  />
                </>
              )}
            </div>
            <div className="flex justify-between text-xs text-surface-500 dark:text-surface-400 mt-1">
              <span>Opening</span>
              <span>Current</span>
            </div>
          </div>

          {/* Alerts */}
          {data.alerts.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Alerts
              </h4>
              {data.alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className={clsx(
                    'p-3 rounded-lg',
                    alert.type === 'STEAM_MOVE' && 'bg-danger-50 dark:bg-danger-500/10',
                    alert.type === 'REVERSE_LINE_MOVEMENT' && 'bg-warning-50 dark:bg-warning-500/10',
                    alert.type === 'SHARP_BOOK_LEAD' && 'bg-primary-50 dark:bg-primary-500/10'
                  )}
                >
                  <div className="flex items-start gap-2">
                    {alert.type === 'STEAM_MOVE' && <Zap className="w-4 h-4 text-danger-500 mt-0.5" />}
                    {alert.type === 'REVERSE_LINE_MOVEMENT' && <ArrowLeftRight className="w-4 h-4 text-warning-500 mt-0.5" />}
                    {alert.type === 'SHARP_BOOK_LEAD' && <Target className="w-4 h-4 text-primary-500 mt-0.5" />}
                    <div className="flex-1">
                      <p className={clsx(
                        'text-sm font-medium',
                        alert.type === 'STEAM_MOVE' && 'text-danger-700 dark:text-danger-300',
                        alert.type === 'REVERSE_LINE_MOVEMENT' && 'text-warning-700 dark:text-warning-300',
                        alert.type === 'SHARP_BOOK_LEAD' && 'text-primary-700 dark:text-primary-300'
                      )}>
                        {formatAlertType(alert.type)}
                      </p>
                      <p className="text-xs text-surface-600 dark:text-surface-400 mt-0.5">
                        {alert.message}
                      </p>
                      {alert.implication && (
                        <p className="text-xs font-medium mt-1 text-surface-700 dark:text-surface-300">
                          {alert.implication}
                        </p>
                      )}
                    </div>
                    <Badge
                      variant={alert.confidence >= 0.7 ? 'success' : alert.confidence >= 0.5 ? 'warning' : 'neutral'}
                      size="sm"
                    >
                      {Math.round(alert.confidence * 100)}%
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Recommendation */}
          {data.recommendation && (
            <div className={clsx(
              'p-3 rounded-lg',
              hasAlerts ? 'bg-warning-50 dark:bg-warning-500/10' : 'bg-surface-50 dark:bg-surface-800/50'
            )}>
              <div className="flex items-center gap-2">
                <Clock className={clsx(
                  'w-4 h-4',
                  hasAlerts ? 'text-warning-600 dark:text-warning-400' : 'text-surface-500'
                )} />
                <span className={clsx(
                  'text-sm font-medium',
                  hasAlerts ? 'text-warning-700 dark:text-warning-300' : 'text-surface-700 dark:text-surface-300'
                )}>
                  {data.recommendation}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Helper functions
function formatLine(value: number, market: string): string {
  if (market === 'spread') {
    return value > 0 ? `+${value}` : value.toString();
  }
  if (market === 'total') {
    return `O/U ${value}`;
  }
  return value.toString();
}

function formatDirection(direction: string): string {
  const map: Record<string, string> = {
    'toward_favorite': 'Toward Favorite',
    'toward_underdog': 'Toward Underdog',
    'toward_over': 'Toward Over',
    'toward_under': 'Toward Under',
    'stable': 'Stable'
  };
  return map[direction] || direction;
}

function formatAlertType(type: string): string {
  const map: Record<string, string> = {
    'STEAM_MOVE': 'Steam Move Detected',
    'REVERSE_LINE_MOVEMENT': 'Reverse Line Movement',
    'SHARP_BOOK_LEAD': 'Sharp Book Lead'
  };
  return map[type] || type;
}

// Simple badge for quick display
export function LineMovementBadge({
  movement,
  hasAlert,
  alertType,
  onClick,
  className
}: {
  movement: string;
  hasAlert?: boolean;
  alertType?: 'steam' | 'rlm' | 'sharp';
  onClick?: () => void;
  className?: string;
}) {
  const value = parseFloat(movement) || 0;
  const isPositive = value > 0;
  const isNegative = value < 0;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors',
        isPositive && 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400',
        isNegative && 'bg-danger-50 text-danger-700 dark:bg-danger-500/15 dark:text-danger-400',
        !isPositive && !isNegative && 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
    >
      {isPositive ? (
        <TrendingUp className="w-3 h-3" />
      ) : isNegative ? (
        <TrendingDown className="w-3 h-3" />
      ) : (
        <Minus className="w-3 h-3" />
      )}
      <span>{movement}</span>
      {hasAlert && alertType === 'steam' && <Zap className="w-3 h-3 text-danger-500" />}
      {hasAlert && alertType === 'rlm' && <ArrowLeftRight className="w-3 h-3 text-warning-500" />}
      {hasAlert && alertType === 'sharp' && <Target className="w-3 h-3 text-primary-500" />}
    </button>
  );
}
