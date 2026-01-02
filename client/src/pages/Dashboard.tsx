import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Badge, Button } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import ErrorMessage from '@/components/ui/ErrorMessage';
import TopPicks from '@/components/TopPicks';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import type { Recommendation, Game } from '@/types';
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Target,
  ChevronRight,
  Trophy,
  Clock,
  Percent,
  Sparkles,
  Zap
} from 'lucide-react';

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function Dashboard() {
  const { client } = useAuth();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [games, setGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    if (!client) return;
    setIsLoading(true);
    setError(null);
    try {
      // Fetch recommendations
      const recs = await api.recommendations.latest(client.id, 5);
      setRecommendations(recs);

      // Fetch live games from multiple sport APIs
      const allGames: Game[] = [];

      try {
        const nflData = await api.nfl.getGames();
        if (nflData?.games) {
          allGames.push(...nflData.games.slice(0, 3).map((g: any) => ({
            id: g.id || g.game_id,
            sport: 'NFL',
            home_team_name: g.home_team?.name,
            away_team_name: g.away_team?.name,
            start_time: g.game_date || g.date,
            league: 'NFL Week 18',
          })));
        }
      } catch (e) { console.log('NFL fetch error:', e); }

      try {
        const nbaData = await api.nba.getTodaysGames();
        if (nbaData?.games) {
          allGames.push(...nbaData.games.slice(0, 3).map((g: any) => ({
            id: g.game_id,
            sport: 'NBA',
            home_team_name: g.home_team?.name,
            away_team_name: g.away_team?.name,
            start_time: g.game_date || g.date,
            league: 'NBA',
          })));
        }
      } catch (e) { console.log('NBA fetch error:', e); }

      try {
        const cfbData = await api.cfb.getTodaysGames();
        if (cfbData?.games) {
          allGames.push(...cfbData.games.slice(0, 3).map((g: any) => ({
            id: g.game_id,
            sport: 'CFB',
            home_team_name: g.home_team?.name,
            away_team_name: g.away_team?.name,
            start_time: g.date,
            league: 'Bowl Games',
          })));
        }
      } catch (e) { console.log('CFB fetch error:', e); }

      try {
        const nhlData = await api.nhl.getTodaysGames();
        if (nhlData?.games) {
          allGames.push(...nhlData.games.slice(0, 3).map((g: any) => ({
            id: g.game_id,
            sport: 'NHL',
            home_team_name: g.home_team?.name,
            away_team_name: g.away_team?.name,
            start_time: g.date,
            league: 'NHL',
          })));
        }
      } catch (e) { console.log('NHL fetch error:', e); }

      // Sort by start time and take first 5
      allGames.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
      setGames(allGames.slice(0, 5));
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Couldn\'t load this. Try again.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [client]);

  // Calculate stats
  const highEdgePicks = recommendations.filter(r => r.edge > 0.05).length;
  const avgEdge = recommendations.length > 0
    ? (recommendations.reduce((acc, r) => acc + r.edge, 0) / recommendations.length * 100)
    : 0;
  const totalPotential = recommendations.reduce((acc, r) => acc + r.expected_value, 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text="Analyzing..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <ErrorMessage
          message={error}
          variant="fullpage"
          onRetry={fetchData}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero Greeting Section */}
      <div className="pt-2">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {getGreeting()}, {client?.name?.split(' ')[0] || 'there'}.
        </h1>
        <p className="text-lg text-gray-600 dark:text-slate-300 mt-2">
          {highEdgePicks > 0 ? (
            <>
              <span className="text-emerald-600 dark:text-emerald-400 font-semibold">{highEdgePicks} curated picks</span>. Ready when you are.
            </>
          ) : recommendations.length > 0 ? (
            'Your edge is working.'
          ) : (
            'Picks refresh at 6 AM ET.'
          )}
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="md" data-testid="stats-card">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10">
              <DollarSign className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-slate-400">Bankroll</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${client?.bankroll?.toLocaleString() || '0'}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md" data-testid="stats-card">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-500/10">
              <Target className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-slate-400">Curated Picks</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {recommendations.length}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md" data-testid="stats-card">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10">
              <Percent className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-slate-400">Precision Rate</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {avgEdge > 0 ? `+${avgEdge.toFixed(1)}%` : '0%'}
              </p>
            </div>
          </div>
        </Card>

        <Card padding="md" data-testid="stats-card">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-500/10">
              <Sparkles className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-slate-400">Projected Edge</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                ${totalPotential.toFixed(0)}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Featured: Top Picks Widget */}
      <div className="grid grid-cols-1 gap-6">
        <TopPicks limit={5} showHeader={true} />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Legacy Recommendations */}
        <Card padding="none">
          <div className="p-4 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-500/10">
                <Zap className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Quick Picks
                </h2>
                <p className="text-sm text-gray-600 dark:text-slate-400 mt-0.5">
                  Curated for your profile
                </p>
              </div>
            </div>
            <Link to="/recommendations">
              <Button variant="ghost" size="sm">
                See All <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>

          <div className="divide-y divide-gray-100 dark:divide-slate-700">
            {recommendations.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  icon={Target}
                  title="No picks yet"
                  description="Picks refresh at 6 AM ET."
                  action={{
                    label: 'Generate Picks',
                    onClick: () => window.location.href = '/recommendations',
                  }}
                />
              </div>
            ) : (
              recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors duration-200"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-gray-900 dark:text-white truncate">
                        {rec.game_info}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <Badge variant="neutral" size="sm">{rec.sport}</Badge>
                        <span className="text-sm text-gray-600 dark:text-slate-400">
                          {rec.market_type} · {rec.selection}
                        </span>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="flex items-center gap-1.5 justify-end">
                        {rec.edge > 0 ? (
                          <TrendingUp className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-500 dark:text-red-400" />
                        )}
                        <span className={`font-bold ${rec.edge > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
                          {rec.edge > 0 ? '+' : ''}{(rec.edge * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-slate-400 mt-0.5">
                        ${rec.suggested_stake.toFixed(0)} stake
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* Upcoming Games */}
        <Card padding="none">
          <div className="p-4 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Upcoming
              </h2>
              <p className="text-sm text-gray-600 dark:text-slate-400 mt-0.5">
                Games to watch
              </p>
            </div>
            <Link to="/games">
              <Button variant="ghost" size="sm">
                See All <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>

          <div className="divide-y divide-gray-100 dark:divide-slate-700">
            {games.length === 0 ? (
              <div className="p-6">
                <EmptyState
                  icon={Trophy}
                  title="No games scheduled"
                  description="Check back later."
                />
              </div>
            ) : (
              games.map((game) => (
                <div
                  key={game.id}
                  className="p-4 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors duration-200"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-gray-900 dark:text-white truncate">
                        {game.home_team_name || game.competitor1_name} vs{' '}
                        {game.away_team_name || game.competitor2_name}
                      </p>
                      <div className="flex items-center gap-2 mt-1.5">
                        <Badge variant="neutral" size="sm">{game.sport}</Badge>
                        {game.league && (
                          <span className="text-sm text-gray-600 dark:text-slate-400">
                            {game.league}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="flex items-center gap-1.5 text-gray-600 dark:text-slate-400 justify-end">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm font-medium">
                          {new Date(game.start_time).toLocaleDateString(undefined, {
                            month: 'short',
                            day: 'numeric'
                          })}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-slate-500 mt-0.5">
                        {new Date(game.start_time).toLocaleTimeString(undefined, {
                          hour: 'numeric',
                          minute: '2-digit'
                        })}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
