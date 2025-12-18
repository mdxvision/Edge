import { useState } from 'react';
import { clsx } from 'clsx';
import {
  ChevronDown,
  ChevronUp,
  Moon,
  Plane,
  Target,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Calendar,
  Mountain,
  Zap
} from 'lucide-react';
import Badge from '@/components/ui/Badge';

interface RestAnalysis {
  home_rest: number;
  away_rest: number;
  rest_differential: number;
  advantage: string;
  estimated_impact_points: number;
  edge_percentage: number;
  historical_ats: string;
  home_back_to_back: boolean;
  away_back_to_back: boolean;
  notes: string[];
}

interface TravelAnalysis {
  distance_miles: number;
  time_zones_crossed: number;
  direction: string;
  direction_label: string;
  altitude_change: number;
  home_altitude: number;
  estimated_impact_points: number;
  edge_percentage: number;
  favors: string;
  historical_ats: string;
  notes: string[];
}

interface MotivationFactor {
  type: string;
  team?: string;
  teams?: string;
  impact_points: number;
  reason: string;
  notes: string;
}

interface MotivationAnalysis {
  factors: MotivationFactor[];
  net_motivation_edge_home: number;
  edge_percentage: number;
  favors: string;
  confidence: number;
  factor_count: number;
}

interface CombinedAnalysis {
  rest_edge_home: number;
  travel_edge_home: number;
  motivation_edge_home: number;
  total_edge: number;
  favors: string;
  confidence: number;
  factors_summary: string[];
  recommendation: string;
}

interface SituationData {
  game_id?: number;
  matchup: string;
  home_team: string;
  away_team: string;
  sport: string;
  date?: string;
  rest: RestAnalysis;
  travel: TravelAnalysis;
  motivation: MotivationAnalysis;
  combined: CombinedAnalysis;
}

interface SituationAnalysisProps {
  data: SituationData;
  compact?: boolean;
  className?: string;
}

export default function SituationAnalysis({
  data,
  compact = false,
  className
}: SituationAnalysisProps) {
  const [expanded, setExpanded] = useState(false);

  const totalEdge = data.combined.total_edge;
  const isHomeEdge = totalEdge > 0;
  const isAwayEdge = totalEdge < 0;
  const isSignificant = Math.abs(totalEdge) >= 2;

  // Get edge badges for quick display
  const getEdgeBadges = () => {
    const badges: { label: string; variant: 'success' | 'danger' | 'warning' | 'primary' | 'neutral'; icon: any }[] = [];

    // Rest edge
    if (Math.abs(data.combined.rest_edge_home) >= 2) {
      const isHomeRest = data.combined.rest_edge_home > 0;
      badges.push({
        label: 'REST EDGE',
        variant: isHomeRest ? 'success' : 'danger',
        icon: Moon
      });
    }

    // Travel edge
    if (data.combined.travel_edge_home >= 2) {
      badges.push({
        label: 'TRAVEL EDGE',
        variant: 'success',
        icon: Plane
      });
    }

    // B2B
    if (data.rest.home_back_to_back || data.rest.away_back_to_back) {
      badges.push({
        label: data.rest.away_back_to_back ? 'AWAY B2B' : 'HOME B2B',
        variant: data.rest.away_back_to_back ? 'success' : 'danger',
        icon: Calendar
      });
    }

    // Altitude
    if (data.travel.home_altitude >= 5000) {
      badges.push({
        label: 'ALTITUDE',
        variant: 'warning',
        icon: Mountain
      });
    }

    // Motivation factors
    data.motivation.factors.forEach(factor => {
      if (factor.type === 'REVENGE') {
        badges.push({
          label: 'REVENGE',
          variant: 'warning',
          icon: Target
        });
      }
      if (factor.type === 'LOOKAHEAD') {
        badges.push({
          label: 'LOOKAHEAD',
          variant: 'danger',
          icon: AlertTriangle
        });
      }
      if (factor.type === 'LETDOWN') {
        badges.push({
          label: 'LETDOWN',
          variant: 'danger',
          icon: TrendingDown
        });
      }
      if (factor.type === 'RIVALRY') {
        badges.push({
          label: 'RIVALRY',
          variant: 'primary',
          icon: Zap
        });
      }
    });

    return badges;
  };

  const badges = getEdgeBadges();

  // Compact inline display
  if (compact) {
    if (badges.length === 0 && Math.abs(totalEdge) < 1.5) {
      return null; // Don't show if no significant factors
    }

    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className={clsx(
          'group flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all flex-wrap',
          'bg-surface-50 dark:bg-surface-800/50',
          'hover:bg-surface-100 dark:hover:bg-surface-800',
          'border',
          isSignificant ? 'border-warning-300 dark:border-warning-700' : 'border-surface-200 dark:border-surface-700',
          className
        )}
      >
        {badges.slice(0, 3).map((badge, idx) => (
          <span
            key={idx}
            className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold',
              badge.variant === 'success' && 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400',
              badge.variant === 'danger' && 'bg-danger-50 text-danger-700 dark:bg-danger-500/15 dark:text-danger-400',
              badge.variant === 'warning' && 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400',
              badge.variant === 'primary' && 'bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400',
              badge.variant === 'neutral' && 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400',
            )}
          >
            <badge.icon className="w-3 h-3" />
            {badge.label}
          </span>
        ))}
        {badges.length > 3 && (
          <span className="text-xs text-surface-500">+{badges.length - 3}</span>
        )}
        {isSignificant && (
          <span className={clsx(
            'text-xs font-bold',
            isHomeEdge ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
          )}>
            {totalEdge > 0 ? '+' : ''}{totalEdge.toFixed(1)}%
          </span>
        )}
      </button>
    );
  }

  return (
    <div className={clsx(
      'rounded-xl border overflow-hidden transition-all',
      'bg-white dark:bg-surface-900',
      isSignificant ? 'border-warning-300 dark:border-warning-700' : 'border-surface-200 dark:border-surface-800',
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
            isHomeEdge && 'bg-success-50 dark:bg-success-500/10',
            isAwayEdge && 'bg-danger-50 dark:bg-danger-500/10',
            !isHomeEdge && !isAwayEdge && 'bg-surface-100 dark:bg-surface-800'
          )}>
            <Target className={clsx(
              'w-5 h-5',
              isHomeEdge && 'text-success-600 dark:text-success-400',
              isAwayEdge && 'text-danger-600 dark:text-danger-400',
              !isHomeEdge && !isAwayEdge && 'text-surface-500'
            )} />
          </div>
          <div className="text-left">
            <span className="font-semibold text-surface-900 dark:text-white">
              Situational Analysis
            </span>
            <p className="text-sm text-surface-500 dark:text-surface-400">
              {data.matchup}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Total Edge */}
          <div className="text-right">
            <div className="flex items-center gap-1">
              {isHomeEdge ? (
                <TrendingUp className="w-4 h-4 text-success-500" />
              ) : isAwayEdge ? (
                <TrendingDown className="w-4 h-4 text-danger-500" />
              ) : null}
              <span className={clsx(
                'text-lg font-bold',
                isHomeEdge && 'text-success-600 dark:text-success-400',
                isAwayEdge && 'text-danger-600 dark:text-danger-400',
                !isHomeEdge && !isAwayEdge && 'text-surface-600 dark:text-surface-400'
              )}>
                {totalEdge > 0 ? '+' : ''}{totalEdge.toFixed(1)}%
              </span>
            </div>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              {data.combined.favors} Edge
            </p>
          </div>

          {expanded ? (
            <ChevronUp className="w-5 h-5 text-surface-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-surface-400" />
          )}
        </div>
      </button>

      {/* Badges Row */}
      {badges.length > 0 && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {badges.map((badge, idx) => (
            <Badge key={idx} variant={badge.variant} size="sm">
              <badge.icon className="w-3 h-3 mr-1" />
              {badge.label}
            </Badge>
          ))}
        </div>
      )}

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-surface-200 dark:border-surface-800">
          {/* Rest Analysis */}
          <div className="pt-4">
            <h4 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2 mb-3">
              <Moon className="w-4 h-4 text-primary-500" />
              Rest Analysis
            </h4>
            <div className="grid grid-cols-2 gap-4">
              <div className={clsx(
                'p-3 rounded-lg',
                data.rest.home_rest > data.rest.away_rest && 'bg-success-50 dark:bg-success-500/10',
                data.rest.home_rest < data.rest.away_rest && 'bg-surface-50 dark:bg-surface-800/50',
                data.rest.home_rest === data.rest.away_rest && 'bg-surface-50 dark:bg-surface-800/50'
              )}>
                <p className="text-xs text-surface-500 dark:text-surface-400">{data.home_team}</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white">
                  {data.rest.home_rest} days
                </p>
                {data.rest.home_back_to_back && (
                  <Badge variant="danger" size="sm">B2B</Badge>
                )}
              </div>
              <div className={clsx(
                'p-3 rounded-lg',
                data.rest.away_rest > data.rest.home_rest && 'bg-success-50 dark:bg-success-500/10',
                data.rest.away_rest < data.rest.home_rest && 'bg-surface-50 dark:bg-surface-800/50',
                data.rest.away_rest === data.rest.home_rest && 'bg-surface-50 dark:bg-surface-800/50'
              )}>
                <p className="text-xs text-surface-500 dark:text-surface-400">{data.away_team}</p>
                <p className="text-xl font-bold text-surface-900 dark:text-white">
                  {data.rest.away_rest} days
                </p>
                {data.rest.away_back_to_back && (
                  <Badge variant="danger" size="sm">B2B</Badge>
                )}
              </div>
            </div>
            <p className="mt-2 text-sm text-surface-600 dark:text-surface-400">
              {data.rest.advantage} | Impact: {data.rest.estimated_impact_points > 0 ? '+' : ''}{data.rest.estimated_impact_points} pts
            </p>
          </div>

          {/* Travel Analysis */}
          <div>
            <h4 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2 mb-3">
              <Plane className="w-4 h-4 text-primary-500" />
              Travel Analysis
            </h4>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-2 rounded-lg bg-surface-50 dark:bg-surface-800/50">
                <p className="text-lg font-bold text-surface-900 dark:text-white">
                  {data.travel.distance_miles.toLocaleString()}
                </p>
                <p className="text-xs text-surface-500">miles</p>
              </div>
              <div className="p-2 rounded-lg bg-surface-50 dark:bg-surface-800/50">
                <p className="text-lg font-bold text-surface-900 dark:text-white">
                  {data.travel.time_zones_crossed}
                </p>
                <p className="text-xs text-surface-500">time zones</p>
              </div>
              <div className="p-2 rounded-lg bg-surface-50 dark:bg-surface-800/50">
                <p className="text-lg font-bold text-surface-900 dark:text-white">
                  {data.travel.home_altitude.toLocaleString()}
                </p>
                <p className="text-xs text-surface-500">ft altitude</p>
              </div>
            </div>
            {data.travel.notes.length > 0 && (
              <ul className="mt-2 space-y-1">
                {data.travel.notes.map((note, idx) => (
                  <li key={idx} className="text-sm text-surface-600 dark:text-surface-400">
                    • {note}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Motivation Factors */}
          {data.motivation.factors.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-surface-900 dark:text-white flex items-center gap-2 mb-3">
                <Target className="w-4 h-4 text-primary-500" />
                Motivation Factors
              </h4>
              <div className="space-y-2">
                {data.motivation.factors.map((factor, idx) => (
                  <div
                    key={idx}
                    className={clsx(
                      'p-3 rounded-lg',
                      factor.type === 'REVENGE' && 'bg-warning-50 dark:bg-warning-500/10',
                      factor.type === 'LOOKAHEAD' && 'bg-danger-50 dark:bg-danger-500/10',
                      factor.type === 'LETDOWN' && 'bg-danger-50 dark:bg-danger-500/10',
                      factor.type === 'RIVALRY' && 'bg-primary-50 dark:bg-primary-500/10',
                      !['REVENGE', 'LOOKAHEAD', 'LETDOWN', 'RIVALRY'].includes(factor.type) && 'bg-surface-50 dark:bg-surface-800/50'
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className={clsx(
                        'text-sm font-semibold',
                        factor.type === 'REVENGE' && 'text-warning-700 dark:text-warning-300',
                        factor.type === 'LOOKAHEAD' && 'text-danger-700 dark:text-danger-300',
                        factor.type === 'LETDOWN' && 'text-danger-700 dark:text-danger-300',
                        factor.type === 'RIVALRY' && 'text-primary-700 dark:text-primary-300'
                      )}>
                        {factor.type}
                      </span>
                      {factor.impact_points !== 0 && (
                        <span className={clsx(
                          'text-sm font-bold',
                          factor.impact_points > 0 ? 'text-success-600' : 'text-danger-600'
                        )}>
                          {factor.impact_points > 0 ? '+' : ''}{factor.impact_points} pts
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-surface-600 dark:text-surface-400 mt-1">
                      {factor.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendation */}
          <div className={clsx(
            'p-4 rounded-lg',
            isSignificant && isHomeEdge && 'bg-success-50 dark:bg-success-500/10',
            isSignificant && isAwayEdge && 'bg-danger-50 dark:bg-danger-500/10',
            !isSignificant && 'bg-surface-50 dark:bg-surface-800/50'
          )}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Recommendation
              </span>
              <Badge
                variant={data.combined.confidence >= 0.7 ? 'success' : data.combined.confidence >= 0.5 ? 'warning' : 'neutral'}
                size="sm"
              >
                {Math.round(data.combined.confidence * 100)}% confidence
              </Badge>
            </div>
            <p className={clsx(
              'text-lg font-semibold mt-2',
              isSignificant && isHomeEdge && 'text-success-700 dark:text-success-300',
              isSignificant && isAwayEdge && 'text-danger-700 dark:text-danger-300',
              !isSignificant && 'text-surface-700 dark:text-surface-300'
            )}>
              {data.combined.recommendation}
            </p>
            {data.combined.factors_summary.length > 0 && (
              <ul className="mt-2 space-y-1">
                {data.combined.factors_summary.map((factor, idx) => (
                  <li key={idx} className="text-sm text-surface-600 dark:text-surface-400">
                    • {factor}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Simple badge for quick situation indicator
export function SituationBadge({
  type,
  team,
  onClick,
  className
}: {
  type: 'REST' | 'TRAVEL' | 'REVENGE' | 'LOOKAHEAD' | 'LETDOWN' | 'RIVALRY' | 'B2B' | 'ALTITUDE';
  team?: string;
  onClick?: () => void;
  className?: string;
}) {
  const config = {
    REST: { icon: Moon, variant: 'success' as const, label: 'REST EDGE' },
    TRAVEL: { icon: Plane, variant: 'success' as const, label: 'TRAVEL EDGE' },
    REVENGE: { icon: Target, variant: 'warning' as const, label: 'REVENGE' },
    LOOKAHEAD: { icon: AlertTriangle, variant: 'danger' as const, label: 'LOOKAHEAD' },
    LETDOWN: { icon: TrendingDown, variant: 'danger' as const, label: 'LETDOWN' },
    RIVALRY: { icon: Zap, variant: 'primary' as const, label: 'RIVALRY' },
    B2B: { icon: Calendar, variant: 'danger' as const, label: 'B2B' },
    ALTITUDE: { icon: Mountain, variant: 'warning' as const, label: 'ALTITUDE' },
  };

  const { icon: Icon, variant, label } = config[type];

  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors',
        variant === 'success' && 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400',
        variant === 'danger' && 'bg-danger-50 text-danger-700 dark:bg-danger-500/15 dark:text-danger-400',
        variant === 'warning' && 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400',
        variant === 'primary' && 'bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400',
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
    >
      <Icon className="w-3 h-3" />
      <span>{team ? `${team} ${label}` : label}</span>
    </button>
  );
}
