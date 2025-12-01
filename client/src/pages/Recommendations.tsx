import { useEffect, useState } from 'react';
import { Card, Badge, Button, Select } from '@/components/ui';
import { useAuth } from '@/context/AuthContext';
import api from '@/lib/api';
import type { Recommendation, Sport } from '@/types';
import { SPORTS, SPORT_LABELS } from '@/types';
import { 
  TrendingUp, 
  TrendingDown, 
  Target, 
  RefreshCw,
  Info,
  DollarSign,
  Percent
} from 'lucide-react';

export default function Recommendations() {
  const { client } = useAuth();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedSport, setSelectedSport] = useState<string>('all');
  const [minEdge, setMinEdge] = useState<string>('0.02');

  const fetchRecommendations = async () => {
    if (!client) return;
    try {
      const data = await api.recommendations.latest(client.id, 50);
      setRecommendations(data);
    } catch (err) {
      console.error('Failed to fetch recommendations:', err);
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
      <div className="space-y-6">
        <div className="h-8 bg-surface-200 dark:bg-surface-800 rounded w-48 animate-pulse" />
        <div className="grid gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-32 bg-surface-200 dark:bg-surface-800 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Recommendations
          </h1>
          <p className="text-surface-500 mt-1">
            AI-powered betting picks based on edge analysis
          </p>
        </div>
        <Button
          onClick={generateRecommendations}
          isLoading={isGenerating}
          className="shrink-0"
        >
          <RefreshCw className="w-4 h-4" />
          Generate New Picks
        </Button>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="w-full sm:w-48">
          <Select
            label="Sport Filter"
            value={selectedSport}
            onChange={(e) => setSelectedSport(e.target.value)}
            options={sportOptions}
          />
        </div>
        <div className="w-full sm:w-48">
          <Select
            label="Minimum Edge"
            value={minEdge}
            onChange={(e) => setMinEdge(e.target.value)}
            options={edgeOptions}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary-50 dark:bg-primary-500/10">
              <Target className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500">Total Picks</p>
              <p className="text-xl font-semibold text-surface-900 dark:text-white">
                {filteredRecs.length}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-success-50 dark:bg-success-500/10">
              <Percent className="w-5 h-5 text-success-600 dark:text-success-500" />
            </div>
            <div>
              <p className="text-sm text-surface-500">Average Edge</p>
              <p className="text-xl font-semibold text-success-600 dark:text-success-500">
                +{(avgEdge * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning-50 dark:bg-warning-500/10">
              <DollarSign className="w-5 h-5 text-warning-600 dark:text-warning-500" />
            </div>
            <div>
              <p className="text-sm text-surface-500">Total Stake</p>
              <p className="text-xl font-semibold text-surface-900 dark:text-white">
                ${totalStake.toLocaleString()}
              </p>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-4">
        {filteredRecs.length === 0 ? (
          <Card className="text-center py-12">
            <Target className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-4" />
            <p className="text-surface-500">No recommendations found</p>
            <p className="text-sm text-surface-400 mt-1">
              Click "Generate New Picks" to get personalized recommendations
            </p>
          </Card>
        ) : (
          filteredRecs.map((rec) => (
            <Card key={rec.id} padding="none" className="overflow-hidden">
              <div className="p-4 md:p-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="primary">{SPORT_LABELS[rec.sport as Sport] || rec.sport}</Badge>
                      <Badge variant="neutral">{rec.market_type}</Badge>
                      <Badge variant="neutral">{rec.sportsbook}</Badge>
                    </div>
                    <h3 className="text-lg font-semibold text-surface-900 dark:text-white">
                      {rec.game_info}
                    </h3>
                    <p className="text-surface-500 mt-1">
                      {rec.selection} {rec.line_value ? `(${rec.line_value > 0 ? '+' : ''}${rec.line_value})` : ''} @ {rec.american_odds > 0 ? '+' : ''}{rec.american_odds}
                    </p>
                  </div>

                  <div className="flex flex-wrap lg:flex-nowrap items-center gap-4 lg:gap-6">
                    <div className="text-center">
                      <p className="text-xs text-surface-500 uppercase tracking-wide">Edge</p>
                      <div className="flex items-center gap-1 mt-1">
                        {rec.edge > 0 ? (
                          <TrendingUp className="w-4 h-4 text-success-500" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-danger-500" />
                        )}
                        <span className={`text-lg font-bold ${rec.edge > 0 ? 'text-success-600' : 'text-danger-600'}`}>
                          {rec.edge > 0 ? '+' : ''}{(rec.edge * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>

                    <div className="text-center">
                      <p className="text-xs text-surface-500 uppercase tracking-wide">Model Prob</p>
                      <p className="text-lg font-bold text-surface-900 dark:text-white mt-1">
                        {(rec.model_probability * 100).toFixed(0)}%
                      </p>
                    </div>

                    <div className="text-center">
                      <p className="text-xs text-surface-500 uppercase tracking-wide">Stake</p>
                      <p className="text-lg font-bold text-primary-600 dark:text-primary-400 mt-1">
                        ${rec.suggested_stake.toFixed(0)}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-surface-50 dark:bg-surface-800/50 rounded-lg">
                  <div className="flex items-start gap-2">
                    <Info className="w-4 h-4 text-surface-400 mt-0.5 shrink-0" />
                    <p className="text-sm text-surface-600 dark:text-surface-400">
                      {rec.explanation}
                    </p>
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
