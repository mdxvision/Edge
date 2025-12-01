import { useState, useEffect } from 'react';
import { Card, Button, Badge } from '@/components/ui';
import api from '@/lib/api';
import type { BacktestResult, ModelStatus, TeamRating } from '@/types';
import { 
  Brain, 
  TrendingUp, 
  Target, 
  BarChart3, 
  Play,
  RefreshCw,
  Database,
  ChevronDown,
  ChevronUp,
  Award
} from 'lucide-react';

export default function Models() {
  const [modelStatus, setModelStatus] = useState<Record<string, ModelStatus>>({});
  const [backtestResults, setBacktestResults] = useState<BacktestResult[]>([]);
  const [teamRatings, setTeamRatings] = useState<TeamRating[]>([]);
  const [selectedSport, setSelectedSport] = useState<string>('NFL');
  const [isLoading, setIsLoading] = useState(true);
  const [isSeeding, setIsSeeding] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [isBacktesting, setIsBacktesting] = useState(false);
  const [showRatings, setShowRatings] = useState(false);
  const [seedMessage, setSeedMessage] = useState<string | null>(null);

  const SUPPORTED_SPORTS = ['NFL', 'NBA', 'MLB', 'NHL'];

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (showRatings && selectedSport) {
      fetchTeamRatings(selectedSport);
    }
  }, [showRatings, selectedSport]);

  async function fetchData() {
    setIsLoading(true);
    try {
      const [status, results] = await Promise.all([
        api.historical.getModelStatus(),
        api.historical.getBacktestResults(),
      ]);
      setModelStatus(status);
      setBacktestResults(results);
    } catch (err) {
      console.error('Failed to fetch model data:', err);
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

  async function handleSeedData() {
    setIsSeeding(true);
    setSeedMessage(null);
    try {
      const result = await api.historical.seedData(3);
      setSeedMessage(result.message);
      await fetchData();
    } catch (err) {
      console.error('Failed to seed data:', err);
      setSeedMessage('Failed to seed data');
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
      <div className="animate-pulse space-y-6">
        <div className="h-8 bg-surface-200 dark:bg-surface-800 rounded w-48" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-32 bg-surface-200 dark:bg-surface-800 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Model Performance
          </h1>
          <p className="text-surface-500 mt-1">
            Advanced ELO models with backtesting validation
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
            {isTraining ? 'Training...' : 'Train Models'}
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
                  {status?.is_fitted ? 'Trained' : 'Untrained'}
                </Badge>
              </div>
              <div className="space-y-2 text-sm text-surface-600 dark:text-surface-400">
                <div className="flex justify-between">
                  <span>Teams Tracked:</span>
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
              Team Power Rankings
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
                <p className="text-center text-surface-500 py-4">
                  No ratings available. Train models first.
                </p>
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
          <div className="text-center py-8 text-surface-500">
            <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>No backtest results yet</p>
            <p className="text-sm mt-1">Seed data and train models, then run backtests</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-surface-500 border-b border-surface-200 dark:border-surface-800">
                  <th className="pb-2 font-medium">Sport</th>
                  <th className="pb-2 font-medium">Period</th>
                  <th className="pb-2 font-medium text-right">Accuracy</th>
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

      <Card className="border-primary-200 dark:border-primary-500/30 bg-primary-50/50 dark:bg-primary-500/5">
        <div className="flex items-start gap-3">
          <TrendingUp className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
          <div>
            <h3 className="font-semibold text-primary-900 dark:text-primary-100">
              About the Models
            </h3>
            <p className="text-sm text-primary-700 dark:text-primary-300 mt-1">
              Our advanced ELO system uses recency-weighted ratings with sport-specific 
              K-factors and margin-of-victory adjustments. Models track team form over 
              the last 5-10 games and incorporate home-field advantage calibrated per sport.
            </p>
            <ul className="text-sm text-primary-700 dark:text-primary-300 mt-2 space-y-1">
              <li>• NFL: K=32, Home advantage +48 pts</li>
              <li>• NBA: K=28, Home advantage +35 pts</li>
              <li>• MLB: K=12, Home advantage +25 pts</li>
              <li>• NHL: K=20, Home advantage +30 pts</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
