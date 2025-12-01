import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, Badge, Button } from '@/components/ui';
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
  Clock
} from 'lucide-react';

export default function Dashboard() {
  const { client } = useAuth();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [games, setGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      if (!client) return;
      try {
        const [recs, gamesData] = await Promise.all([
          api.recommendations.latest(client.id, 5),
          api.games.list(),
        ]);
        setRecommendations(recs);
        setGames(gamesData.slice(0, 5));
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchData();
  }, [client]);

  const stats = [
    {
      label: 'Bankroll',
      value: `$${client?.bankroll.toLocaleString() || '0'}`,
      icon: DollarSign,
      color: 'text-primary-600 dark:text-primary-400',
      bg: 'bg-primary-50 dark:bg-primary-500/10',
    },
    {
      label: 'Active Picks',
      value: recommendations.length.toString(),
      icon: Target,
      color: 'text-success-600 dark:text-success-500',
      bg: 'bg-success-50 dark:bg-success-500/10',
    },
    {
      label: 'Avg Edge',
      value: recommendations.length > 0
        ? `+${(recommendations.reduce((acc, r) => acc + r.edge, 0) / recommendations.length * 100).toFixed(1)}%`
        : '0%',
      icon: TrendingUp,
      color: 'text-warning-600 dark:text-warning-500',
      bg: 'bg-warning-50 dark:bg-warning-500/10',
    },
    {
      label: 'Risk Profile',
      value: client?.risk_profile ? client.risk_profile.charAt(0).toUpperCase() + client.risk_profile.slice(1) : 'Balanced',
      icon: Trophy,
      color: 'text-surface-600 dark:text-surface-400',
      bg: 'bg-surface-100 dark:bg-surface-800',
    },
  ];

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-surface-200 dark:bg-surface-800 rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-surface-200 dark:bg-surface-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
          Welcome back, {client?.name}
        </h1>
        <p className="text-surface-500 mt-1">
          Here's your betting analytics overview
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} padding="md" data-testid="stats-card">
            <div className="flex items-center gap-4">
              <div className={`p-3 rounded-xl ${stat.bg}`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-sm text-surface-500">{stat.label}</p>
                <p className="text-xl font-semibold text-surface-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card padding="none">
          <div className="p-4 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900 dark:text-white">
              Top Recommendations
            </h2>
            <Link to="/recommendations">
              <Button variant="ghost" size="sm">
                View All <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
          <div className="divide-y divide-surface-200 dark:divide-surface-800">
            {recommendations.length === 0 ? (
              <div className="p-8 text-center text-surface-500">
                <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No recommendations yet</p>
                <Link to="/recommendations">
                  <Button variant="primary" size="sm" className="mt-3">
                    Generate Picks
                  </Button>
                </Link>
              </div>
            ) : (
              recommendations.map((rec) => (
                <div key={rec.id} className="p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-surface-900 dark:text-white">
                        {rec.game_info}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="neutral">{rec.sport}</Badge>
                        <span className="text-xs text-surface-500">
                          {rec.market_type} • {rec.selection}
                        </span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1">
                        {rec.edge > 0 ? (
                          <TrendingUp className="w-4 h-4 text-success-500" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-danger-500" />
                        )}
                        <span className={`font-semibold ${rec.edge > 0 ? 'text-success-600' : 'text-danger-600'}`}>
                          {rec.edge > 0 ? '+' : ''}{(rec.edge * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-xs text-surface-500 mt-1">
                        ${rec.suggested_stake.toFixed(0)} stake
                      </p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card padding="none">
          <div className="p-4 border-b border-surface-200 dark:border-surface-800 flex items-center justify-between">
            <h2 className="font-semibold text-surface-900 dark:text-white">
              Upcoming Games
            </h2>
            <Link to="/games">
              <Button variant="ghost" size="sm">
                View All <ChevronRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
          <div className="divide-y divide-surface-200 dark:divide-surface-800">
            {games.length === 0 ? (
              <div className="p-8 text-center text-surface-500">
                <Trophy className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No upcoming games</p>
              </div>
            ) : (
              games.map((game) => (
                <div key={game.id} className="p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-surface-900 dark:text-white">
                        {game.home_team_name || game.competitor1_name} vs{' '}
                        {game.away_team_name || game.competitor2_name}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="neutral">{game.sport}</Badge>
                        <span className="text-xs text-surface-500">{game.league}</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-surface-500">
                        <Clock className="w-4 h-4" />
                        <span className="text-xs">
                          {new Date(game.start_time).toLocaleDateString()}
                        </span>
                      </div>
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
