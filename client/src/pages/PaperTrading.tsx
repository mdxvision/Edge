import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  Clock,
  CheckCircle,
  XCircle,
  Minus,
  RotateCcw,
  Plus,
  Percent,
  Award,
  History
} from 'lucide-react';

interface BankrollStats {
  bankroll_id: number;
  starting_balance: number;
  current_balance: number;
  high_water_mark: number;
  low_water_mark: number;
  total_profit_loss: number;
  total_wagered: number;
  roi_percentage: number;
  win_percentage: number;
  units_won: number;
  stats: {
    total_bets: number;
    pending_bets: number;
    winning_bets: number;
    losing_bets: number;
    pushes: number;
  };
  streaks: {
    current: number;
    longest_win: number;
    longest_lose: number;
  };
}

interface Trade {
  id: number;
  sport: string;
  bet_type: string;
  selection: string;
  line_value: number | null;
  odds: number;
  stake: number;
  potential_payout: number;
  profit_loss?: number;
  game_description?: string;
  result_score?: string;
  status: string;
  placed_at: string;
  settled_at?: string;
}

const SPORTS = ['NFL', 'NBA', 'MLB', 'NHL', 'NCAA_FOOTBALL', 'NCAA_BASKETBALL'];
const BET_TYPES = ['spread', 'moneyline', 'total'];

export default function PaperTrading() {
  const queryClient = useQueryClient();
  const [showBetForm, setShowBetForm] = useState(false);
  const [betForm, setBetForm] = useState({
    sport: 'NFL',
    bet_type: 'spread',
    selection: '',
    odds: -110,
    stake: 100,
    line_value: '',
    game_description: '',
  });

  const { data: bankroll, isLoading: bankrollLoading } = useQuery({
    queryKey: ['paper-trading-bankroll'],
    queryFn: async () => {
      const response = await fetch('/api/paper-trading/bankroll');
      if (!response.ok) throw new Error('Failed to fetch bankroll');
      return response.json() as Promise<BankrollStats>;
    },
  });

  const { data: openBets } = useQuery({
    queryKey: ['paper-trading-open'],
    queryFn: async () => {
      const response = await fetch('/api/paper-trading/open');
      if (!response.ok) throw new Error('Failed to fetch open bets');
      return response.json();
    },
  });

  const { data: history } = useQuery({
    queryKey: ['paper-trading-history'],
    queryFn: async () => {
      const response = await fetch('/api/paper-trading/history?limit=20');
      if (!response.ok) throw new Error('Failed to fetch history');
      return response.json();
    },
  });

  const { data: performance } = useQuery({
    queryKey: ['paper-trading-performance'],
    queryFn: async () => {
      const response = await fetch('/api/paper-trading/performance/by-sport');
      if (!response.ok) throw new Error('Failed to fetch performance');
      return response.json();
    },
  });

  const placeBetMutation = useMutation({
    mutationFn: async (bet: typeof betForm) => {
      const response = await fetch('/api/paper-trading/place', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...bet,
          line_value: bet.line_value ? parseFloat(bet.line_value) : null,
        }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to place bet');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trading-bankroll'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-open'] });
      setShowBetForm(false);
      setBetForm({
        sport: 'NFL',
        bet_type: 'spread',
        selection: '',
        odds: -110,
        stake: 100,
        line_value: '',
        game_description: '',
      });
    },
  });

  const settleBetMutation = useMutation({
    mutationFn: async ({ tradeId, result }: { tradeId: number; result: string }) => {
      const response = await fetch(`/api/paper-trading/settle/${tradeId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ result }),
      });
      if (!response.ok) throw new Error('Failed to settle bet');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trading-bankroll'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-open'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-history'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-performance'] });
    },
  });

  const resetMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/paper-trading/reset', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to reset');
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paper-trading-bankroll'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-open'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-history'] });
      queryClient.invalidateQueries({ queryKey: ['paper-trading-performance'] });
    },
  });

  const formatMoney = (amount: number) => {
    const prefix = amount >= 0 ? '+$' : '-$';
    return `${prefix}${Math.abs(amount).toFixed(2)}`;
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  if (bankrollLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" text="Loading paper trading..." />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">Paper Trading</h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Virtual bankroll for strategy validation
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button onClick={() => setShowBetForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Place Bet
          </Button>
        </div>
      </div>

      {/* Bankroll Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 dark:bg-primary-500/20 rounded-lg">
              <DollarSign className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Balance</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                ${bankroll?.current_balance.toFixed(2)}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${(bankroll?.total_profit_loss ?? 0) >= 0 ? 'bg-success-100 dark:bg-success-500/20' : 'bg-error-100 dark:bg-error-500/20'}`}>
              {(bankroll?.total_profit_loss ?? 0) >= 0 ? (
                <TrendingUp className="w-5 h-5 text-success-600 dark:text-success-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-error-600 dark:text-error-400" />
              )}
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">P/L</p>
              <p className={`text-xl font-bold ${(bankroll?.total_profit_loss ?? 0) >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                {formatMoney(bankroll?.total_profit_loss ?? 0)}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-warning-100 dark:bg-warning-500/20 rounded-lg">
              <Percent className="w-5 h-5 text-warning-600 dark:text-warning-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">ROI</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {(bankroll?.roi_percentage ?? 0).toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-success-100 dark:bg-success-500/20 rounded-lg">
              <Target className="w-5 h-5 text-success-600 dark:text-success-400" />
            </div>
            <div>
              <p className="text-sm text-surface-500 dark:text-surface-400">Win Rate</p>
              <p className="text-xl font-bold text-surface-900 dark:text-white">
                {(bankroll?.win_percentage ?? 0).toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Stats Row */}
      <Card padding="md">
        <div className="flex flex-wrap gap-6 text-sm">
          <div>
            <span className="text-surface-500 dark:text-surface-400">Total Bets:</span>
            <span className="ml-2 font-bold text-surface-900 dark:text-white">{bankroll?.stats.total_bets}</span>
          </div>
          <div>
            <span className="text-surface-500 dark:text-surface-400">Record:</span>
            <span className="ml-2 font-bold text-success-600">{bankroll?.stats.winning_bets}W</span>
            <span className="mx-1 text-surface-400">-</span>
            <span className="font-bold text-error-600">{bankroll?.stats.losing_bets}L</span>
            <span className="mx-1 text-surface-400">-</span>
            <span className="font-bold text-surface-500">{bankroll?.stats.pushes}P</span>
          </div>
          <div>
            <span className="text-surface-500 dark:text-surface-400">Wagered:</span>
            <span className="ml-2 font-bold text-surface-900 dark:text-white">${bankroll?.total_wagered.toFixed(2)}</span>
          </div>
          <div>
            <span className="text-surface-500 dark:text-surface-400">Units:</span>
            <span className={`ml-2 font-bold ${(bankroll?.units_won ?? 0) >= 0 ? 'text-success-600' : 'text-error-600'}`}>
              {(bankroll?.units_won ?? 0) >= 0 ? '+' : ''}{bankroll?.units_won.toFixed(2)}u
            </span>
          </div>
          <div>
            <span className="text-surface-500 dark:text-surface-400">Streak:</span>
            <span className={`ml-2 font-bold ${(bankroll?.streaks.current ?? 0) > 0 ? 'text-success-600' : (bankroll?.streaks.current ?? 0) < 0 ? 'text-error-600' : 'text-surface-500'}`}>
              {(bankroll?.streaks.current ?? 0) > 0 ? `${bankroll?.streaks.current}W` : (bankroll?.streaks.current ?? 0) < 0 ? `${Math.abs(bankroll?.streaks.current ?? 0)}L` : '-'}
            </span>
          </div>
        </div>
      </Card>

      {/* Place Bet Form */}
      {showBetForm && (
        <Card padding="lg">
          <h2 className="text-xl font-bold text-surface-900 dark:text-white mb-6">Place a Bet</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              placeBetMutation.mutate(betForm);
            }}
            className="space-y-4"
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Sport</label>
                <Select value={betForm.sport} onChange={(e) => setBetForm({ ...betForm, sport: e.target.value })}>
                  {SPORTS.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Bet Type</label>
                <Select value={betForm.bet_type} onChange={(e) => setBetForm({ ...betForm, bet_type: e.target.value })}>
                  {BET_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Odds</label>
                <Input
                  type="number"
                  value={betForm.odds}
                  onChange={(e) => setBetForm({ ...betForm, odds: parseInt(e.target.value) || -110 })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Stake ($)</label>
                <Input
                  type="number"
                  value={betForm.stake}
                  onChange={(e) => setBetForm({ ...betForm, stake: parseFloat(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Selection</label>
                <Input
                  placeholder="e.g., Chiefs -3.5, Over 47.5"
                  value={betForm.selection}
                  onChange={(e) => setBetForm({ ...betForm, selection: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-700 dark:text-surface-300 mb-1">Line Value (optional)</label>
                <Input
                  type="number"
                  step="0.5"
                  placeholder="-3.5"
                  value={betForm.line_value}
                  onChange={(e) => setBetForm({ ...betForm, line_value: e.target.value })}
                />
              </div>
            </div>
            <div className="flex gap-3">
              <Button type="submit" disabled={placeBetMutation.isPending}>
                {placeBetMutation.isPending ? 'Placing...' : 'Place Bet'}
              </Button>
              <Button type="button" variant="outline" onClick={() => setShowBetForm(false)}>
                Cancel
              </Button>
            </div>
            {placeBetMutation.isError && (
              <p className="text-error-600 text-sm">{(placeBetMutation.error as Error).message}</p>
            )}
          </form>
        </Card>
      )}

      {/* Open Bets */}
      {(openBets?.bets?.length ?? 0) > 0 && (
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-6">
            <Clock className="w-5 h-5 text-warning-500" />
            <h2 className="text-xl font-bold text-surface-900 dark:text-white">Open Bets ({openBets.count})</h2>
          </div>
          <div className="space-y-3">
            {openBets.bets.map((bet: Trade) => (
              <div
                key={bet.id}
                className="flex items-center justify-between p-4 bg-warning-50 dark:bg-warning-500/10 rounded-lg"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant="neutral">{bet.sport}</Badge>
                    <Badge variant="outline">{bet.bet_type}</Badge>
                  </div>
                  <p className="font-semibold text-surface-900 dark:text-white">{bet.selection}</p>
                  <p className="text-sm text-surface-500 dark:text-surface-400">
                    ${bet.stake} @ {formatOdds(bet.odds)} | To win: ${(bet.potential_payout - bet.stake).toFixed(2)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => settleBetMutation.mutate({ tradeId: bet.id, result: 'won' })}
                    className="text-success-600 border-success-300 hover:bg-success-50"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => settleBetMutation.mutate({ tradeId: bet.id, result: 'lost' })}
                    className="text-error-600 border-error-300 hover:bg-error-50"
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => settleBetMutation.mutate({ tradeId: bet.id, result: 'push' })}
                    className="text-surface-500 border-surface-300 hover:bg-surface-50"
                  >
                    <Minus className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Performance by Sport */}
      {performance && Object.keys(performance).length > 0 && (
        <Card padding="lg">
          <div className="flex items-center gap-2 mb-6">
            <Award className="w-5 h-5 text-primary-500" />
            <h2 className="text-xl font-bold text-surface-900 dark:text-white">Performance by Sport</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(performance).map(([sport, stats]: [string, any]) => (
              <div
                key={sport}
                className={`p-4 rounded-lg ${stats.profit_loss >= 0 ? 'bg-success-50 dark:bg-success-500/10' : 'bg-error-50 dark:bg-error-500/10'}`}
              >
                <p className="font-bold text-surface-900 dark:text-white">{sport}</p>
                <p className="text-sm text-surface-500 dark:text-surface-400">
                  {stats.wins}W-{stats.losses}L ({stats.win_percentage}%)
                </p>
                <p className={`text-lg font-bold ${stats.profit_loss >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                  {formatMoney(stats.profit_loss)}
                </p>
                <p className="text-xs text-surface-400">{stats.roi}% ROI</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Bet History */}
      <Card padding="lg">
        <div className="flex items-center gap-2 mb-6">
          <History className="w-5 h-5 text-surface-500" />
          <h2 className="text-xl font-bold text-surface-900 dark:text-white">Recent History</h2>
        </div>
        {(history?.bets?.length ?? 0) === 0 ? (
          <EmptyState
            icon={History}
            title="No bet history"
            description="Place and settle some bets to see your history."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-surface-500 dark:text-surface-400 border-b border-surface-200 dark:border-surface-700">
                  <th className="pb-3 pr-4 font-medium">Selection</th>
                  <th className="pb-3 pr-4 font-medium">Sport</th>
                  <th className="pb-3 pr-4 text-center font-medium">Odds</th>
                  <th className="pb-3 pr-4 text-right font-medium">Stake</th>
                  <th className="pb-3 pr-4 text-right font-medium">P/L</th>
                  <th className="pb-3 font-medium">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100 dark:divide-surface-800">
                {history.bets.map((bet: Trade) => (
                  <tr key={bet.id} className="hover:bg-surface-50 dark:hover:bg-surface-800/50">
                    <td className="py-3 pr-4">
                      <p className="font-medium text-surface-900 dark:text-white">{bet.selection}</p>
                      <p className="text-xs text-surface-400">{bet.bet_type}</p>
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant="neutral">{bet.sport}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-center text-surface-600 dark:text-surface-400">
                      {formatOdds(bet.odds)}
                    </td>
                    <td className="py-3 pr-4 text-right text-surface-600 dark:text-surface-400">
                      ${bet.stake.toFixed(2)}
                    </td>
                    <td className={`py-3 pr-4 text-right font-bold ${(bet.profit_loss ?? 0) >= 0 ? 'text-success-600' : 'text-error-600'}`}>
                      {formatMoney(bet.profit_loss ?? 0)}
                    </td>
                    <td className="py-3">
                      <Badge
                        variant={bet.status === 'won' ? 'success' : bet.status === 'lost' ? 'danger' : 'neutral'}
                      >
                        {bet.status.toUpperCase()}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
