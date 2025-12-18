import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  Star,
  TrendingUp,
  ArrowRight,
  Sparkles,
  RefreshCw,
  Target,
  Check
} from 'lucide-react';
import Card from '@/components/ui/Card';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import PickLoggerModal from '@/components/PickLoggerModal';

interface TopPick {
  rank: number;
  game_id: number;
  game: string;
  sport: string;
  side: string;
  edge: string;
  edge_value: number;
  confidence: number;
  confidence_label: string;
  star_rating: number;
  recommendation: string;
  unit_size: string;
}

interface TopPicksSummary {
  total_expected_edge: string;
  average_confidence: string;
  picks_available: number;
}

interface TopPicksProps {
  limit?: number;
  sport?: string;
  showHeader?: boolean;
}

const RECOMMENDATION_COLORS: Record<string, string> = {
  'STRONG BET': 'bg-success-500 text-white',
  'BET': 'bg-success-400 text-white',
  'LEAN': 'bg-primary-500 text-white',
};

export default function TopPicks({ limit = 5, sport, showHeader = true }: TopPicksProps) {
  const [picks, setPicks] = useState<TopPick[]>([]);
  const [summary, setSummary] = useState<TopPicksSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pick logger state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPick, setSelectedPick] = useState<{
    sport: string;
    home_team: string;
    away_team: string;
    pick: string;
    pick_type: 'spread' | 'moneyline' | 'total';
    line_value?: number;
    odds: number;
    game_time: string;
    game_id: string;
  } | null>(null);
  const [loggedPicks, setLoggedPicks] = useState<Set<string>>(new Set());

  // Fetch logged picks
  const fetchLoggedPicks = useCallback(async () => {
    try {
      const response = await fetch('/tracker/picks');
      if (response.ok) {
        const data = await response.json();
        const picksData = data.picks || [];
        const loggedKeys = new Set<string>();
        picksData.forEach((p: { game_id: string; pick_type: string; pick: string }) => {
          const key = `${p.game_id}_${p.pick_type}_${p.pick}`;
          loggedKeys.add(key);
        });
        setLoggedPicks(loggedKeys);
      }
    } catch (err) {
      console.error('Failed to fetch logged picks:', err);
    }
  }, []);

  useEffect(() => {
    fetchLoggedPicks();
  }, [fetchLoggedPicks]);

  const parseGameString = (game: string): { home_team: string; away_team: string } => {
    // Format: "Away Team @ Home Team"
    const parts = game.split(' @ ');
    if (parts.length === 2) {
      return { away_team: parts[0].trim(), home_team: parts[1].trim() };
    }
    // Fallback: "Home Team vs Away Team"
    const vsParts = game.split(' vs ');
    if (vsParts.length === 2) {
      return { home_team: vsParts[0].trim(), away_team: vsParts[1].trim() };
    }
    return { home_team: game, away_team: '' };
  };

  const parsePickSide = (side: string): { pick_type: 'spread' | 'moneyline' | 'total'; line_value?: number } => {
    const lowerSide = side.toLowerCase();
    // Check for over/under
    if (lowerSide.includes('over') || lowerSide.startsWith('o ')) {
      const match = side.match(/[\d.]+/);
      return { pick_type: 'total', line_value: match ? parseFloat(match[0]) : undefined };
    }
    if (lowerSide.includes('under') || lowerSide.startsWith('u ')) {
      const match = side.match(/[\d.]+/);
      return { pick_type: 'total', line_value: match ? parseFloat(match[0]) : undefined };
    }
    // Check for moneyline
    if (lowerSide.includes('ml') || lowerSide.includes('moneyline')) {
      return { pick_type: 'moneyline' };
    }
    // Default to spread - try to extract the number
    const match = side.match(/[+-]?[\d.]+/);
    return { pick_type: 'spread', line_value: match ? parseFloat(match[0]) : undefined };
  };

  const handleLogClick = (pick: TopPick) => {
    const { home_team, away_team } = parseGameString(pick.game);
    const { pick_type, line_value } = parsePickSide(pick.side);

    setSelectedPick({
      sport: pick.sport,
      home_team,
      away_team,
      pick: pick.side,
      pick_type,
      line_value,
      odds: -110, // Default odds
      game_time: new Date().toISOString(), // Use current time as fallback
      game_id: `pick_${pick.game_id}`,
    });
    setIsModalOpen(true);
  };

  const handlePickLogged = (pickKey: string) => {
    setLoggedPicks(prev => new Set([...prev, pickKey]));
  };

  const isPickLogged = (pick: TopPick) => {
    const { pick_type } = parsePickSide(pick.side);
    const key = `pick_${pick.game_id}_${pick_type}_${pick.side}`;
    return loggedPicks.has(key);
  };

  const fetchPicks = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (limit) params.append('limit', String(limit));
      if (sport) params.append('sport', sport);
      const response = await fetch(`/api/predictions/top-picks?${params}`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setPicks(data.top_picks || []);
      setSummary(data.summary || null);
    } catch (err) {
      console.error('Failed to fetch top picks:', err);
      setError('Unable to load picks');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchPicks();
  }, [limit, sport]);

  if (isLoading) {
    return (
      <Card padding="lg">
        <div className="flex items-center justify-center py-8">
          <LoadingSpinner size="md" text="Loading top picks..." />
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card padding="lg">
        <div className="text-center py-8">
          <p className="text-surface-500 dark:text-surface-400 mb-4">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchPicks}>
            <RefreshCw className="w-4 h-4" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  if (picks.length === 0) {
    return (
      <Card padding="lg">
        <div className="text-center py-8">
          <Sparkles className="w-10 h-10 text-surface-300 dark:text-surface-600 mx-auto mb-3" />
          <p className="text-surface-500 dark:text-surface-400">No top picks available today</p>
          <p className="text-sm text-surface-400 dark:text-surface-500 mt-1">
            Check back later for new recommendations
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none">
      {showHeader && (
        <div className="p-5 border-b border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-warning-400 to-warning-500 text-white">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-surface-900 dark:text-white">
                  Today's Top Picks
                </h3>
                {summary && (
                  <p className="text-sm text-surface-500 dark:text-surface-400">
                    {summary.picks_available} picks • {summary.total_expected_edge} total edge
                  </p>
                )}
              </div>
            </div>
            <Link to="/recommendations">
              <Button variant="outline" size="sm">
                View All
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      )}

      <div className="divide-y divide-surface-100 dark:divide-surface-800">
        {picks.map((pick, index) => {
          const stars = Array(5).fill(0).map((_, i) => i < pick.star_rating);
          const recColor = RECOMMENDATION_COLORS[pick.recommendation] || 'bg-surface-400 text-white';

          return (
            <div
              key={pick.game_id}
              className="p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
            >
              <div className="flex items-start gap-4">
                {/* Rank */}
                <div className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0',
                  index === 0 ? 'bg-warning-100 text-warning-700 dark:bg-warning-500/20 dark:text-warning-400' :
                  index === 1 ? 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300' :
                  'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
                )}>
                  {pick.rank}
                </div>

                {/* Pick Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <Badge variant="primary" className="text-xs">{pick.sport}</Badge>
                    <span className={clsx('px-2 py-0.5 rounded-full text-xs font-bold', recColor)}>
                      {pick.recommendation}
                    </span>
                  </div>
                  <p className="font-semibold text-surface-900 dark:text-white">
                    {pick.side}
                  </p>
                  <p className="text-sm text-surface-500 dark:text-surface-400 truncate">
                    {pick.game}
                  </p>
                </div>

                {/* Stats */}
                <div className="text-right shrink-0">
                  <p className={clsx(
                    'text-xl font-bold',
                    pick.edge_value >= 4 ? 'text-success-500' :
                    pick.edge_value >= 2 ? 'text-primary-500' :
                    'text-warning-500'
                  )}>
                    {pick.edge}
                  </p>
                  <div className="flex items-center justify-end gap-0.5 mt-1">
                    {stars.map((filled, i) => (
                      <Star
                        key={i}
                        className={clsx(
                          'w-3 h-3',
                          filled ? 'fill-warning-400 text-warning-400' : 'text-surface-300 dark:text-surface-600'
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Log to Tracker Button */}
              <div className="mt-3 pt-3 border-t border-surface-100 dark:border-surface-800">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!isPickLogged(pick)) {
                      handleLogClick(pick);
                    }
                  }}
                  disabled={isPickLogged(pick)}
                  className={clsx(
                    'w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                    isPickLogged(pick)
                      ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                      : 'bg-primary-500/10 text-primary-500 hover:bg-primary-500/20 dark:bg-primary-500/20 dark:text-primary-400 dark:hover:bg-primary-500/30'
                  )}
                >
                  {isPickLogged(pick) ? (
                    <>
                      <Check className="w-4 h-4" />
                      Logged
                    </>
                  ) : (
                    <>
                      <Target className="w-4 h-4" />
                      Log to Tracker
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Summary Footer */}
      {summary && (
        <div className="p-4 bg-gradient-to-r from-primary-50 to-success-50 dark:from-primary-500/10 dark:to-success-500/10 border-t border-surface-200 dark:border-surface-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-success-500" />
              <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Your Edge Today
              </span>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-success-600 dark:text-success-400">
                {summary.total_expected_edge}
              </span>
              <span className="text-sm text-surface-500 dark:text-surface-400 ml-2">
                @ {summary.average_confidence} avg confidence
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Pick Logger Modal */}
      {selectedPick && (
        <PickLoggerModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedPick(null);
          }}
          onSuccess={handlePickLogged}
          pickData={selectedPick}
        />
      )}
    </Card>
  );
}
