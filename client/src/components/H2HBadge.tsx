/**
 * H2H Badge Component
 * Displays compact head-to-head matchup history for game cards
 */

import { useState, useEffect } from 'react';
import { Users, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp } from 'lucide-react';
import api from '@/lib/api';
import { clsx } from 'clsx';

interface H2HSummary {
  has_history: boolean;
  games_played?: number;
  series_record?: string;
  team1_win_pct?: number;
  avg_total?: number;
  trend?: string;
  ats_trend?: string;
  ou_trend?: string;
  last_meeting?: {
    date: string;
    winner: string;
    score: string;
    is_playoff: boolean;
  };
  message?: string;
}

interface H2HBadgeProps {
  sport: string;
  team1: string;
  team2: string;
  compact?: boolean;
  showDetails?: boolean;
}

export default function H2HBadge({
  sport,
  team1,
  team2,
  compact = true,
  showDetails = false
}: H2HBadgeProps) {
  const [h2hData, setH2hData] = useState<H2HSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchH2H = async () => {
      if (!team1 || !team2 || !sport) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        const data = await api.h2h.getSummary(sport, team1, team2);
        setH2hData(data);
      } catch (err) {
        console.error('Failed to fetch H2H data:', err);
        setError('No H2H data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchH2H();
  }, [sport, team1, team2]);

  if (isLoading) {
    return (
      <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-surface-100 dark:bg-surface-800 text-surface-400 dark:text-surface-500">
        <Users className="w-3 h-3 animate-pulse" />
        <span>Loading H2H...</span>
      </div>
    );
  }

  if (error || !h2hData?.has_history) {
    return (
      <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-surface-100 dark:bg-surface-800 text-surface-400 dark:text-surface-500">
        <Users className="w-3 h-3" />
        <span>No H2H history</span>
      </div>
    );
  }

  // Determine trend icon
  const getTrendIcon = () => {
    const winPct = h2hData.team1_win_pct || 50;
    if (winPct > 55) return <TrendingUp className="w-3 h-3 text-success-500" />;
    if (winPct < 45) return <TrendingDown className="w-3 h-3 text-danger-500" />;
    return <Minus className="w-3 h-3 text-surface-400" />;
  };

  // Get color based on dominance
  const getBadgeColor = () => {
    const winPct = h2hData.team1_win_pct || 50;
    if (winPct >= 70) return 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-400';
    if (winPct >= 60) return 'bg-success-50 dark:bg-success-900/20 text-success-600 dark:text-success-400';
    if (winPct <= 30) return 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400';
    if (winPct <= 40) return 'bg-danger-50 dark:bg-danger-900/20 text-danger-600 dark:text-danger-400';
    return 'bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400';
  };

  if (compact && !showDetails) {
    return (
      <div
        className={clsx(
          'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium cursor-pointer transition-colors',
          getBadgeColor()
        )}
        onClick={() => setExpanded(!expanded)}
        title={`${h2hData.trend || ''} | ${h2hData.ats_trend || ''}`}
      >
        <Users className="w-3 h-3" />
        <span>H2H: {h2hData.series_record}</span>
        {getTrendIcon()}
        {showDetails && (
          expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
        )}
      </div>
    );
  }

  // Expanded view
  return (
    <div className="rounded-lg bg-surface-50 dark:bg-surface-800/50 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-primary-500" />
          <span className="text-sm font-medium text-surface-900 dark:text-white">
            Head-to-Head
          </span>
        </div>
        <span className="text-xs text-surface-500 dark:text-surface-400">
          Last {h2hData.games_played} games
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        {/* Series Record */}
        <div className="space-y-1">
          <span className="text-surface-500 dark:text-surface-400">Series</span>
          <div className="flex items-center gap-1">
            <span className={clsx(
              'font-semibold',
              (h2hData.team1_win_pct || 50) > 50
                ? 'text-success-600 dark:text-success-400'
                : (h2hData.team1_win_pct || 50) < 50
                  ? 'text-danger-600 dark:text-danger-400'
                  : 'text-surface-900 dark:text-white'
            )}>
              {h2hData.series_record}
            </span>
            {getTrendIcon()}
          </div>
        </div>

        {/* Avg Total */}
        <div className="space-y-1">
          <span className="text-surface-500 dark:text-surface-400">Avg Total</span>
          <span className="font-semibold text-surface-900 dark:text-white">
            {h2hData.avg_total?.toFixed(1)}
          </span>
        </div>

        {/* ATS Trend */}
        {h2hData.ats_trend && (
          <div className="col-span-2 space-y-1">
            <span className="text-surface-500 dark:text-surface-400">ATS Trend</span>
            <span className="font-medium text-surface-900 dark:text-white">
              {h2hData.ats_trend}
            </span>
          </div>
        )}

        {/* O/U Trend */}
        {h2hData.ou_trend && (
          <div className="col-span-2 space-y-1">
            <span className="text-surface-500 dark:text-surface-400">O/U Trend</span>
            <span className="font-medium text-surface-900 dark:text-white">
              {h2hData.ou_trend}
            </span>
          </div>
        )}
      </div>

      {/* Last Meeting */}
      {h2hData.last_meeting && (
        <div className="pt-2 border-t border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between text-xs">
            <span className="text-surface-500 dark:text-surface-400">Last Meeting</span>
            <span className="text-surface-600 dark:text-surface-300">
              {h2hData.last_meeting.winner} won {h2hData.last_meeting.score}
              <span className="text-surface-400 dark:text-surface-500 ml-1">
                ({new Date(h2hData.last_meeting.date).toLocaleDateString()})
              </span>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
