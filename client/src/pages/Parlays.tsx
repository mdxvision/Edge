import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';

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
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Parlay Builder</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Build and analyze parlays with correlated leg detection
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Add Leg</h2>
            <div className="space-y-3">
              <Input
                placeholder="Selection (e.g., Chiefs -3.5)"
                value={newLeg.selection}
                onChange={(e) => setNewLeg({ ...newLeg, selection: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-3">
                <Input
                  type="number"
                  placeholder="American Odds (-110, +150)"
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
                Add Leg
              </Button>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold dark:text-white">Your Parlay ({legs.length} legs)</h2>
              {legs.length > 0 && (
                <Button size="sm" variant="outline" onClick={() => setLegs([])}>
                  Clear All
                </Button>
              )}
            </div>

            {legs.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">
                Add legs to build your parlay
              </p>
            ) : (
              <div className="space-y-3">
                {legs.map((leg, idx) => (
                  <div
                    key={leg.id}
                    className="flex items-center justify-between p-3 bg-surface-50 dark:bg-surface-800 rounded-lg"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-surface-500">#{idx + 1}</span>
                        <span className="font-medium dark:text-white">{leg.selection}</span>
                        {leg.sport && <Badge variant="secondary">{leg.sport}</Badge>}
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {formatOdds(leg.odds)} | {formatPercent(leg.probability)} probability
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

        <div className="space-y-4">
          {analysis && (
            <>
              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 dark:text-white">Parlay Analysis</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Combined Odds</p>
                    <p className="text-xl font-bold dark:text-white">{formatOdds(analysis.combined_odds)}</p>
                  </div>
                  <div className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Win Probability</p>
                    <p className="text-xl font-bold dark:text-white">
                      {formatPercent(analysis.adjusted_probability)}
                    </p>
                  </div>
                  <div className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">Edge</p>
                    <p
                      className={`text-xl font-bold ${
                        analysis.edge > 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {formatPercent(analysis.edge)}
                    </p>
                  </div>
                  <div className="p-3 bg-surface-50 dark:bg-surface-800 rounded-lg">
                    <p className="text-sm text-gray-500 dark:text-gray-400">EV per $</p>
                    <p
                      className={`text-xl font-bold ${
                        analysis.ev_per_dollar > 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      ${analysis.ev_per_dollar.toFixed(2)}
                    </p>
                  </div>
                </div>

                {analysis.correlation_adjustment !== 0 && (
                  <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                    <p className="text-sm text-yellow-800 dark:text-yellow-200">
                      Correlation adjustment applied: {formatPercent(Math.abs(analysis.correlation_adjustment))}
                      {analysis.correlation_adjustment > 0 ? ' boost' : ' reduction'}
                    </p>
                  </div>
                )}

                <div
                  className={`mt-4 p-4 rounded-lg ${
                    analysis.is_positive_ev
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                      : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                  }`}
                >
                  <p
                    className={`font-medium ${
                      analysis.is_positive_ev
                        ? 'text-green-800 dark:text-green-200'
                        : 'text-red-800 dark:text-red-200'
                    }`}
                  >
                    {analysis.is_positive_ev ? '+EV Parlay' : 'Negative EV'}
                  </p>
                </div>
              </Card>

              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 dark:text-white">Risk Assessment</h2>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-300">Risk Level</span>
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
                    <span className="text-gray-600 dark:text-gray-300">Win Probability</span>
                    <span className="font-medium dark:text-white">
                      {formatPercent(analysis.risk_assessment.win_probability)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600 dark:text-gray-300">Max Stake (% of bankroll)</span>
                    <span className="font-medium dark:text-white">
                      {analysis.risk_assessment.suggested_max_stake_percent.toFixed(1)}%
                    </span>
                  </div>
                  <div className="pt-3 border-t dark:border-gray-700">
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {analysis.risk_assessment.recommendation}
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="p-6">
                <h2 className="text-lg font-semibold mb-4 dark:text-white">Leg Breakdown</h2>
                <div className="space-y-2">
                  {analysis.legs.map((leg, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 border-b dark:border-gray-700 last:border-0"
                    >
                      <span className="text-gray-700 dark:text-gray-300">{leg.selection}</span>
                      <div className="text-right">
                        <span
                          className={`text-sm font-medium ${
                            leg.edge > 0 ? 'text-green-600' : 'text-red-600'
                          }`}
                        >
                          {formatPercent(leg.edge)} edge
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}

          {!analysis && legs.length >= 2 && (
            <Card className="p-6">
              <div className="text-center py-8">
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  Click "Analyze Parlay" to see detailed analysis
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
