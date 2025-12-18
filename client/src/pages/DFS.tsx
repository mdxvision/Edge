import { useState, useEffect } from 'react';
import { Card, Button, Badge } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import type { DFSProjection, OptimizeResult, DFSStack, DFSLineup } from '@/types';
import {
  Zap,
  TrendingUp,
  Users,
  Target,
  Layers,
  RefreshCw,
  Trash2,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react';

const DFS_SPORTS = [
  { id: 'NFL', name: 'NFL' },
  { id: 'NBA', name: 'NBA' },
  { id: 'MLB', name: 'MLB' },
  { id: 'NHL', name: 'NHL' },
];

const PLATFORMS = ['DraftKings', 'FanDuel'];
const LINEUP_TYPES = [
  { id: 'balanced', name: 'Balanced', desc: 'Precision value plays' },
  { id: 'cash', name: 'Cash Game', desc: 'High floor, consistent' },
  { id: 'gpp', name: 'GPP Tournament', desc: 'High ceiling, contrarian' },
];

export default function DFS() {
  const { client } = useAuth();
  const [selectedSport, setSelectedSport] = useState('NFL');
  const [selectedPlatform, setSelectedPlatform] = useState('DraftKings');
  const [lineupType, setLineupType] = useState('balanced');
  const [projections, setProjections] = useState<DFSProjection[]>([]);
  const [currentLineup, setCurrentLineup] = useState<OptimizeResult | null>(null);
  const [savedLineups, setSavedLineups] = useState<DFSLineup[]>([]);
  const [stacks, setStacks] = useState<DFSStack[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [showProjections, setShowProjections] = useState(false);
  const [showStacks, setShowStacks] = useState(false);

  useEffect(() => {
    loadData();
  }, [selectedSport, selectedPlatform]);

  useEffect(() => {
    if (client) {
      loadLineups();
    }
  }, [client, selectedSport]);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    try {
      const [projData, stackData] = await Promise.all([
        api.dfs.getProjections(selectedSport, selectedPlatform, 50),
        api.dfs.getStacks(selectedSport),
      ]);
      setProjections(projData.projections);
      setStacks(stackData.stacks);
    } catch (err) {
      console.error('Failed to load DFS data:', err);
      setError('Couldn\'t load this. Try again.');
    } finally {
      setIsLoading(false);
    }
  }

  async function loadLineups() {
    if (!client) return;
    try {
      const data = await api.dfs.getLineups(client.id, selectedSport);
      setSavedLineups(data.lineups);
    } catch (err) {
      console.error('Failed to load lineups:', err);
    }
  }

  async function handleOptimize() {
    if (!client) return;
    setIsOptimizing(true);
    try {
      const result = await api.dfs.optimize(client.id, {
        sport: selectedSport,
        platform: selectedPlatform,
        lineup_type: lineupType,
        num_lineups: 1,
      });
      setCurrentLineup(result);
      await loadLineups();
    } catch (err) {
      console.error('Failed to optimize lineup:', err);
    } finally {
      setIsOptimizing(false);
    }
  }

  async function handleDeleteLineup(lineupId: number) {
    if (!client) return;
    try {
      await api.dfs.deleteLineup(client.id, lineupId);
      await loadLineups();
    } catch (err) {
      console.error('Failed to delete lineup:', err);
    }
  }

  if (isLoading && projections.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <LoadingSpinner size="lg" text="Analyzing..." />
      </div>
    );
  }

  if (error && projections.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <ErrorMessage
          message={error}
          variant="fullpage"
          onRetry={loadData}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">
            Lineups
          </h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Precision projections. Intelligent correlation.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1 p-1 bg-surface-100 dark:bg-surface-800 rounded-lg">
          {DFS_SPORTS.map((sport) => (
            <button
              key={sport.id}
              onClick={() => setSelectedSport(sport.id)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedSport === sport.id
                  ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
              }`}
            >
              {sport.name}
            </button>
          ))}
        </div>
        <div className="flex gap-1 p-1 bg-surface-100 dark:bg-surface-800 rounded-lg">
          {PLATFORMS.map((platform) => (
            <button
              key={platform}
              onClick={() => setSelectedPlatform(platform)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                selectedPlatform === platform
                  ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-sm'
                  : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-white'
              }`}
            >
              {platform}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Zap className="w-5 h-5 text-warning-500" />
                <h2 className="font-semibold text-surface-900 dark:text-white">
                  Build Optimal Lineup
                </h2>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              {LINEUP_TYPES.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setLineupType(type.id)}
                  className={`p-3 rounded-lg border-2 text-left transition-colors ${
                    lineupType === type.id
                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-500/10'
                      : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                  }`}
                >
                  <div className="font-medium text-surface-900 dark:text-white">
                    {type.name}
                  </div>
                  <div className="text-xs text-surface-500 mt-1">{type.desc}</div>
                </button>
              ))}
            </div>

            <Button
              onClick={handleOptimize}
              disabled={isOptimizing || !client}
              className="w-full"
            >
              <RefreshCw className={`w-4 h-4 ${isOptimizing ? 'animate-spin' : ''}`} />
              {isOptimizing ? 'Analyzing...' : 'Build Optimal Lineup'}
            </Button>

            {currentLineup && currentLineup.success && currentLineup.lineup && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-medium text-surface-900 dark:text-white">
                    Optimal Lineup
                  </h3>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-surface-500">
                      Salary: <span className="font-medium text-surface-900 dark:text-white">
                        ${currentLineup.total_salary?.toLocaleString()}
                      </span>
                    </span>
                    <span className="text-surface-500">
                      Projected: <span className="font-medium text-success-600 dark:text-success-500">
                        {currentLineup.projected_points} pts
                      </span>
                    </span>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-left text-sm text-surface-500 border-b border-surface-200 dark:border-surface-800">
                        <th className="pb-2 font-medium">Pos</th>
                        <th className="pb-2 font-medium">Player</th>
                        <th className="pb-2 font-medium text-right">Salary</th>
                        <th className="pb-2 font-medium text-right">Proj</th>
                        <th className="pb-2 font-medium text-right">Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                      {currentLineup.lineup.map((player, idx) => (
                        <tr key={idx} className="text-sm">
                          <td className="py-2">
                            <Badge variant="neutral">{player.position}</Badge>
                          </td>
                          <td className="py-2 font-medium text-surface-900 dark:text-white">
                            {player.player_name}
                          </td>
                          <td className="py-2 text-right text-surface-600 dark:text-surface-400">
                            ${player.salary.toLocaleString()}
                          </td>
                          <td className="py-2 text-right font-medium text-success-600 dark:text-success-500">
                            {player.projected_points}
                          </td>
                          <td className="py-2 text-right text-surface-600 dark:text-surface-400">
                            {player.value_score.toFixed(1)}x
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {currentLineup.correlation_analysis && (
                  <div className="mt-4 p-3 bg-surface-50 dark:bg-surface-800/50 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                      <Layers className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                      <span className="font-medium text-surface-900 dark:text-white text-sm">
                        Correlation Analysis
                      </span>
                      <Badge variant={
                        currentLineup.correlation_analysis.lineup_rating === 'highly_correlated' ? 'success' :
                        currentLineup.correlation_analysis.lineup_rating === 'well_correlated' ? 'primary' :
                        'warning'
                      }>
                        {currentLineup.correlation_analysis.lineup_rating.replace('_', ' ')}
                      </Badge>
                    </div>
                    <p className="text-sm text-surface-600 dark:text-surface-400">
                      {currentLineup.correlation_analysis.recommendation}
                    </p>
                  </div>
                )}
              </div>
            )}
          </Card>

          <Card>
            <div
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setShowProjections(!showProjections)}
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                <h2 className="font-semibold text-surface-900 dark:text-white">
                  Precision Projections
                </h2>
                <Badge variant="neutral">{projections.length}</Badge>
              </div>
              {showProjections ? (
                <ChevronUp className="w-5 h-5 text-surface-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-surface-500" />
              )}
            </div>

            {showProjections && (
              <div className="mt-4 max-h-96 overflow-y-auto">
                <table className="w-full">
                  <thead className="sticky top-0 bg-white dark:bg-surface-900">
                    <tr className="text-left text-sm text-surface-500 border-b border-surface-200 dark:border-surface-800">
                      <th className="pb-2 font-medium">Player</th>
                      <th className="pb-2 font-medium">Pos</th>
                      <th className="pb-2 font-medium text-right">Salary</th>
                      <th className="pb-2 font-medium text-right">Proj</th>
                      <th className="pb-2 font-medium text-right">Ceil</th>
                      <th className="pb-2 font-medium text-right">Value</th>
                      <th className="pb-2 font-medium text-right">Own%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-200 dark:divide-surface-800">
                    {projections.slice(0, 50).map((p) => (
                      <tr key={p.player_id} className="text-sm">
                        <td className="py-2 font-medium text-surface-900 dark:text-white">
                          {p.player_name}
                        </td>
                        <td className="py-2 text-surface-500">{p.position}</td>
                        <td className="py-2 text-right text-surface-600 dark:text-surface-400">
                          ${p.salary.toLocaleString()}
                        </td>
                        <td className="py-2 text-right font-medium text-surface-900 dark:text-white">
                          {p.projected_points}
                        </td>
                        <td className="py-2 text-right text-success-600 dark:text-success-500">
                          {p.ceiling}
                        </td>
                        <td className={`py-2 text-right font-medium ${
                          p.value_score >= 5 ? 'text-success-600 dark:text-success-500' :
                          p.value_score >= 4 ? 'text-primary-600 dark:text-primary-400' :
                          'text-surface-600 dark:text-surface-400'
                        }`}>
                          {p.value_score.toFixed(1)}x
                        </td>
                        <td className="py-2 text-right text-surface-500">
                          {p.ownership_projection}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <div className="flex items-center gap-3 mb-4">
              <Users className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h2 className="font-semibold text-surface-900 dark:text-white">
                Saved Lineups
              </h2>
            </div>

            {savedLineups.length === 0 ? (
              <EmptyState
                icon={Target}
                title="No saved lineups"
                description="Build a lineup to get started."
                className="py-6"
              />
            ) : (
              <div className="space-y-3">
                {savedLineups.slice(0, 5).map((lineup) => (
                  <div
                    key={lineup.id}
                    className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="neutral">{lineup.lineup_type}</Badge>
                      <button
                        onClick={() => handleDeleteLineup(lineup.id)}
                        className="text-surface-400 hover:text-danger-600 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-surface-500">Projected</span>
                      <span className="font-medium text-success-600 dark:text-success-500">
                        {lineup.projected_points} pts
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-surface-500">Salary</span>
                      <span className="text-surface-900 dark:text-white">
                        ${lineup.total_salary.toLocaleString()}
                      </span>
                    </div>
                    <div className="text-xs text-surface-400 mt-1">
                      {new Date(lineup.created_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <div
              className="flex items-center justify-between cursor-pointer"
              onClick={() => setShowStacks(!showStacks)}
            >
              <div className="flex items-center gap-3">
                <Layers className="w-5 h-5 text-warning-500" />
                <h2 className="font-semibold text-surface-900 dark:text-white">
                  Optimal Stacks
                </h2>
              </div>
              {showStacks ? (
                <ChevronUp className="w-5 h-5 text-surface-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-surface-500" />
              )}
            </div>

            {showStacks && (
              <div className="mt-4 space-y-3">
                {stacks.map((stack, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-surface-900 dark:text-white text-sm">
                        {stack.name}
                      </span>
                      <span className={`text-sm font-medium ${
                        stack.correlation >= 0.4 ? 'text-success-600 dark:text-success-500' :
                        stack.correlation >= 0.2 ? 'text-primary-600 dark:text-primary-400' :
                        'text-surface-500'
                      }`}>
                        {(stack.correlation * 100).toFixed(0)}% corr
                      </span>
                    </div>
                    <div className="flex gap-1 mb-1">
                      {stack.positions.map((pos, i) => (
                        <Badge key={i} variant="neutral" className="text-xs">
                          {pos}
                        </Badge>
                      ))}
                    </div>
                    <p className="text-xs text-surface-500">{stack.notes}</p>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="border-primary-200 dark:border-primary-500/30 bg-primary-50/50 dark:bg-primary-500/5">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
              <div>
                <h3 className="font-semibold text-primary-900 dark:text-primary-100 text-sm">
                  The Edge
                </h3>
                <ul className="text-xs text-primary-700 dark:text-primary-300 mt-2 space-y-1">
                  <li>Cash: Prioritize floor and consistency</li>
                  <li>GPP: Stack correlated players for upside</li>
                  <li>Value plays (5x+) are key to winning</li>
                  <li>Monitor ownership to find leverage</li>
                </ul>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
