import { useEffect, useState } from 'react';
import { Card, Badge, Button, Select } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import ErrorMessage from '@/components/ui/ErrorMessage';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import type { Recommendation, Sport } from '@/types';
import { SPORTS, SPORT_LABELS } from '@/types';
import {
  TrendingUp,
  TrendingDown,
  Target,
  RefreshCw,
  Sparkles,
  DollarSign,
  Percent,
  ArrowLeftRight,
  User,
  Moon,
  Plane
} from 'lucide-react';

export default function Recommendations() {
  const { client } = useAuth();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSport, setSelectedSport] = useState<string>('all');
  const [minEdge, setMinEdge] = useState<string>('0.02');

  const fetchRecommendations = async () => {
    if (!client) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.recommendations.latest(client.id, 50);
      setRecommendations(data);
    } catch (err) {
      console.error('Failed to fetch recommendations:', err);
      setError('Couldn\'t load this. Try again.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [client]);

  const generateRecommendations = async () => {
    if (!client) return;
    setIsGenerating(true);
    try {
      const sports = selectedSport !== 'all' ? [selectedSport] : undefined;
      const result = await api.recommendations.run(client.id, {
        sports,
        min_edge: parseFloat(minEdge),
      });
      setRecommendations(result.recommendations);
    } catch (err) {
      console.error('Failed to generate recommendations:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const filteredRecs = selectedSport === 'all'
    ? recommendations
    : recommendations.filter((r) => r.sport === selectedSport);

  const totalStake = filteredRecs.reduce((acc, r) => acc + r.suggested_stake, 0);
  const avgEdge = filteredRecs.length > 0
    ? filteredRecs.reduce((acc, r) => acc + r.edge, 0) / filteredRecs.length
    : 0;

  const sportOptions = [
    { value: 'all', label: 'All Sports' },
    ...SPORTS.map((sport) => ({
      value: sport,
      label: SPORT_LABELS[sport as Sport],
    })),
  ];

  const edgeOptions = [
    { value: '0', label: 'Any Edge' },
    { value: '0.02', label: '2%+ Edge' },
    { value: '0.05', label: '5%+ Edge' },
    { value: '0.10', label: '10%+ Edge' },
  ];

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
          onRetry={fetchRecommendations}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">
            Curated Picks
          </h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Intelligent edge detection. Personalized for you.
          </p>
        </div>
        <Button
          onClick={generateRecommendations}
          isLoading={isGenerating}
          className="shrink-0"
          size="lg"
        >
          <RefreshCw className="w-5 h-5" />
          Generate Picks
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="w-full sm:w-56">
          <Select
            label="Sport"
            value={selectedSport}
            onChange={(e) => setSelectedSport(e.target.value)}
            options={sportOptions}
          />
        </div>
        <div className="w-full sm:w-56">
          <Select
            label="Minimum Edge"
            value={minEdge}
            onChange={(e) => setMinEdge(e.target.value)}
            options={edgeOptions}
          />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-primary-50 dark:bg-primary-500/10">
              <Target className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Curated Picks</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                {filteredRecs.length}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-success-50 dark:bg-success-500/10">
              <Percent className="w-6 h-6 text-success-600 dark:text-success-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Precision Rate</p>
              <p className="text-2xl font-bold text-success-600 dark:text-success-400">
                +{(avgEdge * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-warning-50 dark:bg-warning-500/10">
              <DollarSign className="w-6 h-6 text-warning-600 dark:text-warning-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Total Stake</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                ${totalStake.toLocaleString()}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Recommendations List */}
      <div className="grid gap-4">
        {filteredRecs.length === 0 ? (
          <Card padding="lg">
            <EmptyState
              icon={Target}
              title="No picks available"
              description="Picks refresh at 6 AM ET."
              action={{
                label: 'Generate Picks',
                onClick: generateRecommendations,
              }}
            />
          </Card>
        ) : (
          filteredRecs.map((rec) => (
            <Card key={rec.id} padding="none">
              <div className="p-5 md:p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-3">
                      <Badge variant="primary">{SPORT_LABELS[rec.sport as Sport] || rec.sport}</Badge>
                      <Badge variant="neutral">{rec.market_type}</Badge>
                      <Badge variant="outline">{rec.sportsbook}</Badge>
                    </div>
                    <h3 className="text-lg font-semibold text-surface-900 dark:text-white">
                      {rec.game_info}
                    </h3>
                    <p className="text-surface-500 dark:text-surface-400 mt-1">
                      {rec.selection} {rec.line_value ? `(${rec.line_value > 0 ? '+' : ''}${rec.line_value})` : ''} @ {rec.american_odds > 0 ? '+' : ''}{rec.american_odds}
                    </p>
                  </div>

                  <div className="flex flex-wrap lg:flex-nowrap items-center gap-6">
                    <div className="text-center">
                      <p className="text-caption text-surface-500 dark:text-surface-400">Edge</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        {rec.edge > 0 ? (
                          <TrendingUp className="w-4 h-4 text-success-500 dark:text-success-400" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-danger-500 dark:text-danger-400" />
                        )}
                        <span className={`text-lg font-bold ${rec.edge > 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                          {rec.edge > 0 ? '+' : ''}{(rec.edge * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-center">
                      <p className="text-caption text-surface-500 dark:text-surface-400">Confidence</p>
                      <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">
                        {(rec.model_probability * 100).toFixed(0)}%
                      </p>
                    </div>

                    <div className="text-center">
                      <p className="text-caption text-surface-500 dark:text-surface-400">Stake</p>
                      <p className="text-lg font-bold text-primary-600 dark:text-primary-400 mt-1">
                        ${rec.suggested_stake.toFixed(0)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
                  <div className="flex items-start gap-3">
                    <Sparkles className="w-5 h-5 text-primary-500 dark:text-primary-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-surface-900 dark:text-white mb-1">The Edge</p>
                      <p className="text-sm text-surface-600 dark:text-surface-400">
                        {rec.explanation}
                      </p>
                    </div>
                  </div>

                  {/* Edge Factor Badges */}
                  <div className="mt-3 pt-3 border-t border-surface-200 dark:border-surface-700 flex flex-wrap gap-2">
                    {rec.edge > 0.05 && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400">
                        <TrendingUp className="w-3 h-3" />
                        Strong Value
                      </span>
                    )}
                    {/* Line movement */}
                    {rec.edge > 0.03 && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400">
                        <ArrowLeftRight className="w-3 h-3" />
                        Line Tracked
                      </span>
                    )}
                    {/* Official tendency */}
                    {(rec.sport === 'NFL' || rec.sport === 'NBA' || rec.sport === 'MLB') && (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400">
                        <User className="w-3 h-3" />
                        Official Factor
                      </span>
                    )}
                    {/* Situational factors */}
                    {(rec.sport === 'NFL' || rec.sport === 'NBA') && rec.edge > 0.02 && (
                      <>
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400">
                          <Moon className="w-3 h-3" />
                          Rest Analyzed
                        </span>
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400">
                          <Plane className="w-3 h-3" />
                          Travel Factor
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
