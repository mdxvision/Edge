import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Select from '@/components/ui/Select';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Trophy,
  Target,
  BarChart3,
  Flame,
  Snowflake
} from 'lucide-react';

interface PowerRating {
  rank: number;
  team_name: string;
  team_abbrev: string;
  power_rating: number;
  offensive_rating: number | null;
  defensive_rating: number | null;
  net_rating: number | null;
  home_advantage: number;
  record: string;
  ats_record: string;
  ats_percentage: number | null;
  ats_trend: string;
  last_5_ats: string | null;
  last_5_su: string | null;
  over_under: string;
  sos_rating: number | null;
  sos_rank: number | null;
}

const SPORTS = [
  { value: 'NFL', label: 'NFL' },
  { value: 'NBA', label: 'NBA' },
  { value: 'MLB', label: 'MLB' },
  { value: 'NHL', label: 'NHL' },
  { value: 'NCAA_FOOTBALL', label: 'NCAAF' },
  { value: 'NCAA_BASKETBALL', label: 'NCAAB' },
];

export default function PowerRatings() {
  const [sport, setSport] = useState('NFL');
  const [view, setView] = useState<'ratings' | 'ats'>('ratings');

  const { data: ratingsData, isLoading } = useQuery({
    queryKey: ['power-ratings', sport],
    queryFn: async () => {
      const response = await fetch(`/api/power-ratings/${sport}`);
      if (!response.ok) throw new Error('Failed to fetch power ratings');
      return response.json();
    },
  });

  const { data: bestATS } = useQuery({
    queryKey: ['best-ats', sport],
    queryFn: async () => {
      const response = await fetch(`/api/power-ratings/${sport}/ats/best?limit=10`);
      if (!response.ok) throw new Error('Failed to fetch best ATS');
      return response.json();
    },
    enabled: view === 'ats',
  });

  const { data: worstATS } = useQuery({
    queryKey: ['worst-ats', sport],
    queryFn: async () => {
      const response = await fetch(`/api/power-ratings/${sport}/ats/worst?limit=10`);
      if (!response.ok) throw new Error('Failed to fetch worst ATS');
      return response.json();
    },
    enabled: view === 'ats',
  });

  const getTrendIcon = (trend: string) => {
    if (trend === 'hot') return <Flame className="w-4 h-4 text-success-500" />;
    if (trend === 'cold') return <Snowflake className="w-4 h-4 text-error-500" />;
    return <Minus className="w-4 h-4 text-surface-400" />;
  };

  const getATSColor = (percentage: number | null) => {
    if (percentage === null) return 'text-surface-500';
    if (percentage >= 55) return 'text-success-500';
    if (percentage <= 45) return 'text-error-500';
    return 'text-surface-600 dark:text-surface-400';
  };

  const getRatingColor = (rating: number) => {
    if (rating >= 60) return 'text-success-500';
    if (rating >= 55) return 'text-success-400';
    if (rating <= 40) return 'text-error-500';
    if (rating <= 45) return 'text-error-400';
    return 'text-surface-600 dark:text-surface-400';
  };

  const formatLast5 = (last5: string | null) => {
    if (!last5) return null;
    return last5.split('').map((result, i) => (
      <span
        key={i}
        className={`inline-block w-5 h-5 text-xs font-bold rounded flex items-center justify-center ${
          result === 'W'
            ? 'bg-success-100 text-success-700 dark:bg-success-500/20 dark:text-success-400'
            : 'bg-error-100 text-error-700 dark:bg-error-500/20 dark:text-error-400'
        }`}
      >
        {result}
      </span>
    ));
  };

  const ratings: PowerRating[] = ratingsData?.ratings || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">Power Ratings</h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Team strength rankings and ATS performance
          </p>
        </div>
        <div className="flex gap-3">
          <Select value={sport} onChange={(e) => setSport(e.target.value)}>
            {SPORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </Select>
          <Select value={view} onChange={(e) => setView(e.target.value as 'ratings' | 'ats')}>
            <option value="ratings">Power Ratings</option>
            <option value="ats">ATS Analysis</option>
          </Select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 dark:bg-primary-500/20 rounded-lg">
              <BarChart3 className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Teams</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {ratings.length}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-success-100 dark:bg-success-500/20 rounded-lg">
              <Trophy className="w-5 h-5 text-success-600 dark:text-success-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Top Rated</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {ratings[0]?.team_abbrev || '-'}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-warning-100 dark:bg-warning-500/20 rounded-lg">
              <Flame className="w-5 h-5 text-warning-600 dark:text-warning-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Best ATS</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {ratings.filter(r => r.ats_trend === 'hot').length}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-error-100 dark:bg-error-500/20 rounded-lg">
              <Target className="w-5 h-5 text-error-600 dark:text-error-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Fade Targets</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {ratings.filter(r => r.ats_trend === 'cold').length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      {view === 'ratings' ? (
        <Card padding="lg">
          <h2 className="text-xl font-bold text-surface-900 dark:text-white mb-6">
            {sport} Power Rankings
          </h2>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner size="lg" text="Loading ratings..." />
            </div>
          ) : ratings.length === 0 ? (
            <EmptyState
              icon={BarChart3}
              title="No ratings available"
              description="Power ratings data is not available for this sport yet."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-surface-500 dark:text-surface-400 border-b border-surface-200 dark:border-surface-700">
                    <th className="pb-4 pr-4 font-medium">#</th>
                    <th className="pb-4 pr-4 font-medium">Team</th>
                    <th className="pb-4 pr-4 text-center font-medium">Rating</th>
                    <th className="pb-4 pr-4 text-center font-medium">Off</th>
                    <th className="pb-4 pr-4 text-center font-medium">Def</th>
                    <th className="pb-4 pr-4 text-center font-medium">Record</th>
                    <th className="pb-4 pr-4 text-center font-medium">ATS</th>
                    <th className="pb-4 pr-4 text-center font-medium">ATS%</th>
                    <th className="pb-4 pr-4 text-center font-medium">Last 5</th>
                    <th className="pb-4 pr-4 text-center font-medium">O/U</th>
                    <th className="pb-4 pr-4 text-center font-medium">SoS</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                  {ratings.map((team) => (
                    <tr
                      key={team.rank}
                      className="hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
                    >
                      <td className="py-4 pr-4">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${
                          team.rank <= 3
                            ? 'bg-warning-100 text-warning-700 dark:bg-warning-500/20 dark:text-warning-400'
                            : team.rank <= 10
                            ? 'bg-success-100 text-success-700 dark:bg-success-500/20 dark:text-success-400'
                            : 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
                        }`}>
                          {team.rank}
                        </span>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-surface-900 dark:text-white">
                            {team.team_name}
                          </span>
                          {getTrendIcon(team.ats_trend)}
                        </div>
                      </td>
                      <td className="py-4 pr-4 text-center">
                        <span className={`font-bold text-lg ${getRatingColor(team.power_rating)}`}>
                          {team.power_rating.toFixed(1)}
                        </span>
                      </td>
                      <td className="py-4 pr-4 text-center text-surface-600 dark:text-surface-400">
                        {team.offensive_rating?.toFixed(1) || '-'}
                      </td>
                      <td className="py-4 pr-4 text-center text-surface-600 dark:text-surface-400">
                        {team.defensive_rating?.toFixed(1) || '-'}
                      </td>
                      <td className="py-4 pr-4 text-center text-surface-600 dark:text-surface-400">
                        {team.record}
                      </td>
                      <td className="py-4 pr-4 text-center font-medium text-surface-900 dark:text-white">
                        {team.ats_record}
                      </td>
                      <td className="py-4 pr-4 text-center">
                        <span className={`font-bold ${getATSColor(team.ats_percentage)}`}>
                          {team.ats_percentage?.toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-4 pr-4">
                        <div className="flex gap-1 justify-center">
                          {formatLast5(team.last_5_ats)}
                        </div>
                      </td>
                      <td className="py-4 pr-4 text-center text-surface-600 dark:text-surface-400">
                        {team.over_under}
                      </td>
                      <td className="py-4 pr-4 text-center text-surface-500 dark:text-surface-500">
                        {team.sos_rank || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Best ATS Teams */}
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-6">
              <Flame className="w-6 h-6 text-success-500" />
              <h2 className="text-xl font-bold text-surface-900 dark:text-white">
                Best ATS Teams
              </h2>
            </div>
            {bestATS?.teams?.length > 0 ? (
              <div className="space-y-3">
                {bestATS.teams.map((team: any, index: number) => (
                  <div
                    key={team.team_name}
                    className="flex items-center justify-between p-3 bg-success-50 dark:bg-success-500/10 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-success-600 dark:text-success-400">
                        #{index + 1}
                      </span>
                      <div>
                        <p className="font-semibold text-surface-900 dark:text-white">
                          {team.team_name}
                        </p>
                        <p className="text-sm text-surface-500 dark:text-surface-400">
                          {team.ats_record}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-bold text-success-600 dark:text-success-400">
                        {team.ats_percentage.toFixed(1)}%
                      </p>
                      <div className="flex gap-0.5 justify-end mt-1">
                        {formatLast5(team.last_5_ats)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={TrendingUp}
                title="No data"
                description="ATS data not available"
              />
            )}
          </Card>

          {/* Worst ATS Teams (Fade Targets) */}
          <Card padding="lg">
            <div className="flex items-center gap-2 mb-6">
              <Snowflake className="w-6 h-6 text-error-500" />
              <h2 className="text-xl font-bold text-surface-900 dark:text-white">
                Fade Targets
              </h2>
            </div>
            {worstATS?.teams?.length > 0 ? (
              <div className="space-y-3">
                {worstATS.teams.map((team: any, index: number) => (
                  <div
                    key={team.team_name}
                    className="flex items-center justify-between p-3 bg-error-50 dark:bg-error-500/10 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-error-600 dark:text-error-400">
                        #{index + 1}
                      </span>
                      <div>
                        <p className="font-semibold text-surface-900 dark:text-white">
                          {team.team_name}
                        </p>
                        <p className="text-sm text-surface-500 dark:text-surface-400">
                          {team.ats_record}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-bold text-error-600 dark:text-error-400">
                        {team.ats_percentage.toFixed(1)}%
                      </p>
                      <div className="flex gap-0.5 justify-end mt-1">
                        {formatLast5(team.last_5_ats)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={TrendingDown}
                title="No data"
                description="ATS data not available"
              />
            )}
          </Card>
        </div>
      )}

      {/* Legend */}
      <Card padding="md">
        <div className="flex flex-wrap gap-6 text-sm text-surface-600 dark:text-surface-400">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-success-500" />
            <span>Hot ATS ({'>'}55%)</span>
          </div>
          <div className="flex items-center gap-2">
            <Snowflake className="w-4 h-4 text-error-500" />
            <span>Cold ATS ({'<'}45%)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-success-500">60+</span>
            <span>Elite Rating</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-error-500">{'<'}40</span>
            <span>Poor Rating</span>
          </div>
          <div className="flex items-center gap-2">
            <span>SoS</span>
            <span>= Strength of Schedule Rank</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
