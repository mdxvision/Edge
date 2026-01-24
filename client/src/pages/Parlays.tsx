import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import EmptyState from '@/components/ui/EmptyState';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';
import { Layers, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';

interface ParlayLeg {
  id: string;
  selection: string;
  odds: number;
  probability: number;
  sport?: string;
}

export default function Parlays() {
  const [legs, setLegs] = useState<ParlayLeg[]>([]);
  const [newLeg, setNewLeg] = useState({
    selection: '',
    odds: '',
    probability: '',
    sport: '',
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      api.parlays.analyze(
        legs.map((l) => ({
          selection: l.selection,
          odds: l.odds,
          probability: l.probability,
          sport: l.sport,
        }))
      ),
  });

  const addLeg = () => {
    if (!newLeg.selection || !newLeg.odds || !newLeg.probability) return;

    setLegs([
      ...legs,
      {
        id: Date.now().toString(),
        selection: newLeg.selection,
        odds: parseInt(newLeg.odds),
        probability: parseFloat(newLeg.probability) / 100,
        sport: newLeg.sport || undefined,
      },
    ]);
    setNewLeg({ selection: '', odds: '', probability: '', sport: '' });
  };

  const removeLeg = (id: string) => {
    setLegs(legs.filter((l) => l.id !== id));
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  const formatPercent = (val: number) => {
    return (val * 100).toFixed(1) + '%';
  };

  const analysis = analyzeMutation.data;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-display text-surface-900 dark:text-white">Parlay Lab</h1>
        <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
          Intelligent correlation detection. See your true edge.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column - Build Parlay */}
        <div className="space-y-6">
          {/* Add Leg Card */}
          <Card padding="lg">
            <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Add Pick</h2>
            <div className="space-y-3">
              <Input
                placeholder="Selection (e.g., Chiefs -3.5)"
                value={newLeg.selection}
                onChange={(e) => setNewLeg({ ...newLeg, selection: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  type="number"
                  placeholder="Odds (-110, +150)"
                  value={newLeg.odds}
                  onChange={(e) => setNewLeg({ ...newLeg, odds: e.target.value })}
                />
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Your Probability (%)"
                  value={newLeg.probability}
                  onChange={(e) => setNewLeg({ ...newLeg, probability: e.target.value })}
                />
              </div>
              <Select
                value={newLeg.sport}
                onChange={(e) => setNewLeg({ ...newLeg, sport: e.target.value })}
              >
                <option value="">Sport (optional)</option>
                {SPORTS.map((sport) => (
                  <option key={sport} value={sport}>
                    {sport.replace('_', ' ')}
                  </option>
                ))}
              </Select>
              <Button onClick={addLeg} disabled={!newLeg.selection || !newLeg.odds || !newLeg.probability}>
                Add Pick
              </Button>
            </div>
          </Card>

          {/* Parlay Legs Card */}
          <Card padding="lg">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-h2 text-surface-900 dark:text-white">Your Parlay ({legs.length} picks)</h2>
              {legs.length > 0 && (
                <Button size="sm" variant="outline" onClick={() => setLegs([])}>
                  Clear
                </Button>
              )}
            </div>

            {legs.length === 0 ? (
              <EmptyState
                icon={Layers}
                title="No picks added"
                description="Add picks to build your parlay."
                className="py-6"
              />
            ) : (
              <div className="space-y-3">
                {legs.map((leg, idx) => (
                  <div
                    key={leg.id}
                    className="flex items-center justify-between p-4 bg-surface-50 dark:bg-surface-800 rounded-xl"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-surface-500">#{idx + 1}</span>
                        <span className="font-semibold text-surface-900 dark:text-white">{leg.selection}</span>
                        {leg.sport && <Badge variant="neutral">{leg.sport}</Badge>}
                      </div>
                      <p className="text-sm text-surface-500 dark:text-surface-400">
                        {formatOdds(leg.odds)} · {formatPercent(leg.probability)} probability
                      </p>
                    </div>
                    <Button size="sm" variant="ghost" onClick={() => removeLeg(leg.id)}>
                      Remove
                    </Button>
                  </div>
                ))}

                <Button
                  className="w-full mt-4"
                  onClick={() => analyzeMutation.mutate()}
                  disabled={legs.length < 2 || analyzeMutation.isPending}
                >
                  {analyzeMutation.isPending ? 'Analyzing...' : 'Analyze Parlay'}
                </Button>
              </div>
            )}
          </Card>
        </div>

        {/* Right Column - Analysis */}
        <div className="space-y-6">
          {analysis && (
            <>
              {/* Main Analysis */}
              <Card padding="lg">
                <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Analysis</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
                    <p className="text-sm text-surface-500 dark:text-surface-400">Combined Odds</p>
                    <p className="text-xl font-bold text-surface-900 dark:text-white">{formatOdds(analysis.combined_odds)}</p>
                  </div>
                  <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
                    <p className="text-sm text-surface-500 dark:text-surface-400">Win Probability</p>
                    <p className="text-xl font-bold text-surface-900 dark:text-white">
                      {formatPercent(analysis.adjusted_probability)}
                    </p>
                  </div>
                  <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
                    <p className="text-sm text-surface-500 dark:text-surface-400">Edge</p>
                    <p className={`text-xl font-bold flex items-center gap-1 ${
                      analysis.edge > 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
                    }`}>
                      {analysis.edge > 0 ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                      {formatPercent(analysis.edge)}
                    </p>
                  </div>
                  <div className="p-4 bg-surface-50 dark:bg-surface-800 rounded-xl">
                    <p className="text-sm text-surface-500 dark:text-surface-400">Projected Edge</p>
                    <p className={`text-xl font-bold ${
                      analysis.ev_per_dollar > 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
                    }`}>
                      ${analysis.ev_per_dollar.toFixed(2)}
                    </p>
                  </div>
                </div>

                {analysis.correlation_adjustment !== 0 && (
                  <div className="mt-4 p-4 bg-warning-50 dark:bg-warning-500/10 border border-warning-200 dark:border-warning-500/30 rounded-xl">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-warning-600 dark:text-warning-400" />
                      <p className="text-sm font-medium text-warning-700 dark:text-warning-300">
                        Correlation Detected: {formatPercent(Math.abs(analysis.correlation_adjustment))}
                        {analysis.correlation_adjustment > 0 ? ' boost' : ' reduction'}
                      </p>
                    </div>
                  </div>
                )}

                <div className={`mt-4 p-4 rounded-xl flex items-center gap-3 ${
                  analysis.is_positive_ev
                    ? 'bg-success-50 dark:bg-success-500/10 border border-success-200 dark:border-success-500/30'
                    : 'bg-danger-50 dark:bg-danger-500/10 border border-danger-200 dark:border-danger-500/30'
                }`}>
                  {analysis.is_positive_ev ? (
                    <CheckCircle className="w-6 h-6 text-success-600 dark:text-success-400" />
                  ) : (
                    <XCircle className="w-6 h-6 text-danger-600 dark:text-danger-400" />
                  )}
                  <p className={`font-semibold ${
                    analysis.is_positive_ev
                      ? 'text-success-700 dark:text-success-300'
                      : 'text-danger-700 dark:text-danger-300'
                  }`}>
                    {analysis.is_positive_ev ? '+EV Parlay' : 'Negative EV'}
                  </p>
                </div>
              </Card>

              {/* Risk Assessment */}
              <Card padding="lg">
                <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Risk Assessment</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-surface-600 dark:text-surface-400">Risk Level</span>
                    <Badge
                      variant={
                        analysis.risk_assessment.risk_level === 'low'
                          ? 'success'
                          : analysis.risk_assessment.risk_level === 'medium'
                          ? 'warning'
                          : 'danger'
                      }
                    >
                      {analysis.risk_assessment.risk_level.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-surface-600 dark:text-surface-400">Win Probability</span>
                    <span className="font-medium text-surface-900 dark:text-white">
                      {formatPercent(analysis.risk_assessment.win_probability)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-surface-600 dark:text-surface-400">Max Stake</span>
                    <span className="font-medium text-surface-900 dark:text-white">
                      {analysis.risk_assessment.suggested_max_stake_percent.toFixed(1)}% of bankroll
                    </span>
                  </div>
                  <div className="pt-4 border-t border-surface-200 dark:border-surface-700">
                    <p className="text-sm text-surface-600 dark:text-surface-400">
                      {analysis.risk_assessment.recommendation}
                    </p>
                  </div>
                </div>
              </Card>

              {/* Leg Breakdown */}
              <Card padding="lg">
                <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Pick Breakdown</h2>
                <div className="space-y-2">
                  {analysis.legs.map((leg: { selection: string; edge: number }, idx: number) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 border-b border-surface-200 dark:border-surface-700 last:border-0"
                    >
                      <span className="text-surface-700 dark:text-surface-300">{leg.selection}</span>
                      <span className={`text-sm font-medium ${
                        leg.edge > 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
                      }`}>
                        {formatPercent(leg.edge)} edge
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}

          {!analysis && legs.length >= 2 && (
            <Card padding="lg">
              <div className="text-center py-8">
                <Layers className="w-12 h-12 text-surface-400 mx-auto mb-4" />
                <p className="text-surface-500 dark:text-surface-400">
                  Analyze to see your edge.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
