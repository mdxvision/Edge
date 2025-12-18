import { useState, useEffect } from 'react';
import { Card, Button, Badge } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import ErrorMessage from '@/components/ui/ErrorMessage';
import api from '@/lib/api';
import type { BacktestResult, ModelStatus, TeamRating } from '@/types';
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Target,
  BarChart3,
  Play,
  RefreshCw,
  Database,
  ChevronDown,
  ChevronUp,
  Award,
  Users,
  Search
} from 'lucide-react';

interface CoachLeaderboardEntry {
  coach_id: number;
  coach_name: string;
  team: string | null;
  sport: string;
  ats_record: string;
  win_pct: number;
  edge: number;
  total_games: number;
}

interface Situation {
  value: string;
  label: string;
}

export default function Models() {
  const [modelStatus, setModelStatus] = useState<Record<string, ModelStatus>>({});
  const [backtestResults, setBacktestResults] = useState<BacktestResult[]>([]);
  const [teamRatings, setTeamRatings] = useState<TeamRating[]>([]);
  const [selectedSport, setSelectedSport] = useState<string>('NFL');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [showRatings, setShowRatings] = useState(false);
  const [seedMessage, setSeedMessage] = useState<string | null>(null);

  // Coach DNA state
  const [showCoachDNA, setShowCoachDNA] = useState(false);
  const [coachLeaderboard, setCoachLeaderboard] = useState<CoachLeaderboardEntry[]>([]);
  const [situations, setSituations] = useState<Situation[]>([]);
  const [selectedSituation, setSelectedSituation] = useState<string>('as_underdog');
  const [coachSportFilter, setCoachSportFilter] = useState<string>('');
  const [isLoadingCoaches, setIsLoadingCoaches] = useState(false);
  const [coachSearchQuery, setCoachSearchQuery] = useState('');

  const SUPPORTED_SPORTS = ['NFL', 'NBA', 'MLB', 'NHL'];
  const COACH_SPORTS = ['NFL', 'NBA', 'CBB'];

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (showRatings && selectedSport) {
      fetchTeamRatings(selectedSport);
    }
  }, [showRatings, selectedSport]);

  // Fetch coach data when Coach DNA section is opened
  useEffect(() => {
    if (showCoachDNA) {
      fetchSituations();
      fetchCoachLeaderboard();
    }
  }, [showCoachDNA]);

  // Refetch when filters change
  useEffect(() => {
    if (showCoachDNA) {
      fetchCoachLeaderboard();
    }
  }, [selectedSituation, coachSportFilter]);

  async function fetchData() {
    setIsLoading(true);
    setError(null);
    try {
      const [status, results] = await Promise.all([
        api.historical.getModelStatus(),
        api.historical.getBacktestResults(),
      ]);
      setModelStatus(status);
      setBacktestResults(results);
    } catch (err) {
      console.error('Failed to fetch model data:', err);
      setError('Couldn\'t load this. Try again.');
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchTeamRatings(sport: string) {
    try {
      const data = await api.historical.getTeamRatings(sport);
      setTeamRatings(data.teams || []);
    } catch (err) {
      console.error('Failed to fetch team ratings:', err);
      setTeamRatings([]);
    }
  }

  async function fetchSituations() {
    try {
      const data = await api.coaches.getSituationsList();
      setSituations(data.situations || []);
    } catch (err) {
      console.error('Failed to fetch situations:', err);
    }
  }

  async function fetchCoachLeaderboard() {
    setIsLoadingCoaches(true);
    try {
      const data = await api.coaches.getLeaderboard(
        selectedSituation,
        coachSportFilter || undefined,
        5
      );
      setCoachLeaderboard(data.leaderboard || []);
    } catch (err) {
      console.error('Failed to fetch coach leaderboard:', err);
      setCoachLeaderboard([]);
    } finally {
      setIsLoadingCoaches(false);
    }
  }

  async function handleSeedData() {
    setIsSeeding(true);
    setSeedMessage(null);
    try {
      const result = await api.historical.seedData(3);
      setSeedMessage(result.message);
      await fetchData();
    } catch (err) {
      console.error('Failed to seed data:', err);
      setSeedMessage('Something\'s not right.');
    } finally {
      setIsSeeding(false);
    }
  }

  async function handleTrainModels() {
    setIsTraining(true);
    try {
      await api.historical.trainModels();
      await fetchData();
    } catch (err) {
      console.error('Failed to train models:', err);
    } finally {
      setIsTraining(false);
    }
  }

  async function handleRunBacktest(sport: string) {
    setIsBacktesting(true);
    try {
      await api.historical.runBacktest(sport, 2, 0.03);
      await fetchData();
    } catch (err) {
      console.error('Failed to run backtest:', err);
    } finally {
      setIsBacktesting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" text="Analyzing..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">
            Intelligence
          </h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Precision power ratings. Validated performance.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            onClick={handleSeedData}
            disabled={isSeeding}
          >
            <Database className="w-4 h-4" />
            {isSeeding ? 'Seeding...' : 'Seed Data'}
          </Button>
          <Button
            variant="secondary"
            onClick={handleTrainModels}
            disabled={isTraining}
          >
            <RefreshCw className={`w-4 h-4 ${isTraining ? 'animate-spin' : ''}`} />
            {isTraining ? 'Calibrating...' : 'Calibrate'}
          </Button>
        </div>
      </div>

      {seedMessage && (
        <div className="p-3 bg-success-50 dark:bg-success-500/10 border border-success-200 dark:border-success-500/30 rounded-lg text-success-700 dark:text-success-400">
          {seedMessage}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {SUPPORTED_SPORTS.map((sport) => {
          const status = modelStatus[sport];
          return (
            <Card key={sport} padding="md">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                  <span className="font-semibold text-surface-900 dark:text-white">{sport}</span>
                </div>
                <Badge variant={status?.is_fitted ? 'success' : 'warning'}>
                  {status?.is_fitted ? 'Calibrated' : 'Pending'}
                </Badge>
              </div>
              <div className="space-y-2 text-sm text-surface-600 dark:text-surface-400">
                <div className="flex justify-between">
                  <span>Teams:</span>
                  <span className="font-medium">{status?.teams_tracked || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>K-Factor:</span>
                  <span className="font-medium">{status?.k_factor || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Home Advantage:</span>
                  <span className="font-medium">{status?.home_advantage || '-'}</span>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="w-full mt-3"
                onClick={() => handleRunBacktest(sport)}
                disabled={isBacktesting || !status?.is_fitted}
              >
                <Play className="w-4 h-4" />
                Run Backtest
              </Button>
            </Card>
          );
        })}
      </div>

      <Card>
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setShowRatings(!showRatings)}
        >
          <div className="flex items-center gap-3">
            <Award className="w-5 h-5 text-warning-600 dark:text-warning-500" />
            <h2 className="font-semibold text-surface-900 dark:text-white">
              Power Ratings
            </h2>
          </div>
          {showRatings ? (
            <ChevronUp className="w-5 h-5 text-surface-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-surface-500" />
          )}
        </div>

        {showRatings && (
          <div className="mt-4">
            <div className="flex gap-2 mb-4">
              {SUPPORTED_SPORTS.map((sport) => (
                <Button
                  key={sport}
                  variant={selectedSport === sport ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setSelectedSport(sport)}
                >
                  {sport}
                </Button>
              ))}
            </div>

            <div className="max-h-96 overflow-y-auto">
              <table className="w-full">
                <thead className="sticky top-0 bg-white dark:bg-surface-900">
                  <tr className="text-left text-sm text-surface-500 border-b border-surface-200 dark:border-surface-800">
                    <th className="pb-2 font-medium">Rank</th>
                    <th className="pb-2 font-medium">Team</th>
                    <th className="pb-2 font-medium text-right">Rating</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                  {teamRatings.map((team, index) => (
                    <tr key={team.id} className="text-sm">
                      <td className="py-2 text-surface-500">{index + 1}</td>
                      <td className="py-2 font-medium text-surface-900 dark:text-white">
                        {team.name}
                      </td>
                      <td className="py-2 text-right">
                        <span className={`font-mono ${
                          (team.model_rating || team.rating) > 1550
                            ? 'text-success-600 dark:text-success-500'
                            : (team.model_rating || team.rating) < 1450
                              ? 'text-danger-600 dark:text-danger-500'
                              : 'text-surface-600 dark:text-surface-400'
                        }`}>
                          {(team.model_rating || team.rating).toFixed(0)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {teamRatings.length === 0 && (
                <EmptyState
                  icon={Award}
                  title="No ratings available"
                  description="Calibrate first to see power ratings."
                  className="py-6"
                />
              )}
            </div>
          </div>
        )}
      </Card>

      <Card>
        <div className="flex items-center gap-3 mb-4">
          <BarChart3 className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <h2 className="font-semibold text-surface-900 dark:text-white">
            Backtest Results
          </h2>
        </div>

        {backtestResults.length === 0 ? (
          <EmptyState
            icon={Target}
            title="No backtest results"
            description="Seed data and calibrate, then run backtests."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-surface-500 border-b border-surface-200 dark:border-surface-800">
                  <th className="pb-2 font-medium">Sport</th>
                  <th className="pb-2 font-medium">Period</th>
                  <th className="pb-2 font-medium text-right">Precision</th>
                  <th className="pb-2 font-medium text-right">ROI</th>
                  <th className="pb-2 font-medium text-right">Bets</th>
                  <th className="pb-2 font-medium text-right">Brier Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                {backtestResults.map((result) => (
                  <tr key={result.id} className="text-sm">
                    <td className="py-3">
                      <Badge variant="neutral">{result.sport}</Badge>
                    </td>
                    <td className="py-3 text-surface-600 dark:text-surface-400">
                      {result.period}
                    </td>
                    <td className="py-3 text-right font-medium text-surface-900 dark:text-white">
                      {result.accuracy}%
                    </td>
                    <td className={`py-3 text-right font-medium ${
                      result.roi && result.roi > 0
                        ? 'text-success-600 dark:text-success-500'
                        : 'text-danger-600 dark:text-danger-500'
                    }`}>
                      {result.roi !== null ? `${result.roi > 0 ? '+' : ''}${result.roi}%` : '-'}
                    </td>
                    <td className="py-3 text-right text-surface-600 dark:text-surface-400">
                      {result.bets}
                    </td>
                    <td className="py-3 text-right text-surface-600 dark:text-surface-400 font-mono">
                      {result.brier_score?.toFixed(4) || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Coach DNA Section */}
      <Card>
        <div
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setShowCoachDNA(!showCoachDNA)}
        >
          <div className="flex items-center gap-3">
            <Users className="w-5 h-5 text-premium-600 dark:text-premium-500" />
            <div>
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Coach DNA
              </h2>
              <p className="text-sm text-surface-500 dark:text-surface-400">
                Situational records and behavioral analysis
              </p>
            </div>
          </div>
          {showCoachDNA ? (
            <ChevronUp className="w-5 h-5 text-surface-500" />
          ) : (
            <ChevronDown className="w-5 h-5 text-surface-500" />
          )}
        </div>

        {showCoachDNA && (
          <div className="mt-4 space-y-4">
            {/* Filters */}
            <div className="flex flex-wrap gap-2">
              <div className="flex gap-2">
                <select
                  value={selectedSituation}
                  onChange={(e) => setSelectedSituation(e.target.value)}
                  className="px-3 py-2 text-sm rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-white"
                >
                  {situations.length > 0 ? (
                    situations.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))
                  ) : (
                    <>
                      <option value="as_underdog">As Underdog</option>
                      <option value="as_favorite">As Favorite</option>
                      <option value="after_loss">After Loss</option>
                      <option value="primetime">Primetime</option>
                      <option value="in_playoffs">Playoffs</option>
                      <option value="back_to_back">Back-to-Back</option>
                    </>
                  )}
                </select>
              </div>
              <div className="flex gap-1">
                <Button
                  variant={coachSportFilter === '' ? 'primary' : 'secondary'}
                  size="sm"
                  onClick={() => setCoachSportFilter('')}
                >
                  All
                </Button>
                {COACH_SPORTS.map((sport) => (
                  <Button
                    key={sport}
                    variant={coachSportFilter === sport ? 'primary' : 'secondary'}
                    size="sm"
                    onClick={() => setCoachSportFilter(sport)}
                  >
                    {sport}
                  </Button>
                ))}
              </div>
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
              <input
                type="text"
                placeholder="Search coaches..."
                value={coachSearchQuery}
                onChange={(e) => setCoachSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-surface-200 dark:border-surface-700 bg-white dark:bg-surface-800 text-surface-900 dark:text-white placeholder-surface-400"
              />
            </div>

            {/* Leaderboard */}
            <div>
              <h3 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">
                Top Coaches - {situations.find(s => s.value === selectedSituation)?.label || selectedSituation.replace(/_/g, ' ')}
              </h3>

              {isLoadingCoaches ? (
                <div className="flex justify-center py-6">
                  <LoadingSpinner size="sm" />
                </div>
              ) : coachLeaderboard.length === 0 ? (
                <EmptyState
                  icon={Users}
                  title="No coaches found"
                  description="Seed coach data to see leaderboards."
                  className="py-6"
                />
              ) : (
                <div className="space-y-2">
                  {coachLeaderboard
                    .filter(c => !coachSearchQuery || c.coach_name.toLowerCase().includes(coachSearchQuery.toLowerCase()))
                    .map((coach, index) => (
                    <div
                      key={coach.coach_id}
                      className="flex items-center justify-between p-3 rounded-lg bg-surface-50 dark:bg-surface-800/50 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          index === 0 ? 'bg-warning-100 text-warning-700 dark:bg-warning-500/20 dark:text-warning-400' :
                          index === 1 ? 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300' :
                          index === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400' :
                          'bg-surface-100 text-surface-600 dark:bg-surface-700 dark:text-surface-400'
                        }`}>
                          {index + 1}
                        </span>
                        <div>
                          <div className="font-medium text-surface-900 dark:text-white">
                            {coach.coach_name}
                          </div>
                          <div className="text-xs text-surface-500 dark:text-surface-400">
                            {coach.team || coach.sport}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <div className="text-sm font-medium text-surface-700 dark:text-surface-300">
                            {coach.ats_record}
                          </div>
                          <div className="text-xs text-surface-500 dark:text-surface-400">
                            {coach.total_games} games
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {coach.edge >= 0 ? (
                            <TrendingUp className="w-4 h-4 text-success-500" />
                          ) : (
                            <TrendingDown className="w-4 h-4 text-danger-500" />
                          )}
                          <span className={`font-bold ${
                            coach.edge >= 5 ? 'text-success-600 dark:text-success-400' :
                            coach.edge >= 0 ? 'text-primary-600 dark:text-primary-400' :
                            coach.edge >= -5 ? 'text-warning-600 dark:text-warning-400' :
                            'text-danger-600 dark:text-danger-400'
                          }`}>
                            {coach.edge >= 0 ? '+' : ''}{coach.edge.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Edge explanation */}
            <div className="p-3 rounded-lg bg-premium-50 dark:bg-premium-500/10 border border-premium-200 dark:border-premium-500/30">
              <div className="flex items-start gap-2">
                <Brain className="w-4 h-4 text-premium-600 dark:text-premium-400 mt-0.5" />
                <div className="text-sm">
                  <span className="font-medium text-premium-900 dark:text-premium-100">
                    EdgeBet Exclusive:
                  </span>
                  <span className="text-premium-700 dark:text-premium-300 ml-1">
                    Coach DNA tracks ATS performance in specific situations like &quot;after a loss&quot; or &quot;as underdog&quot; to find hidden edges.
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      <Card className="border-primary-200 dark:border-primary-500/30 bg-primary-50/50 dark:bg-primary-500/5">
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
          <div>
            <h3 className="font-semibold text-primary-900 dark:text-primary-100">
              How It Works
            </h3>
            <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">
              Intelligent power ratings use recency-weighted calculations with sport-specific
              K-factors and margin adjustments. Form tracked over 5-10 games with calibrated
              home-field advantage.
            </p>
            <ul className="text-sm text-primary-700 dark:text-primary-300 mt-2 space-y-1">
              <li>NFL: K=32, +48 pts home</li>
              <li>NBA: K=28, +35 pts home</li>
              <li>MLB: K=12, +25 pts home</li>
              <li>NHL: K=20, +30 pts home</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
