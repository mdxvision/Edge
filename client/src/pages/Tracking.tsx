import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';
import { ClipboardList, Trophy, Target, DollarSign, Percent, Activity } from 'lucide-react';

export default function Tracking() {
  const queryClient = useQueryClient();
  const [showAddBet, setShowAddBet] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [sportFilter, setSportFilter] = useState<string>('');

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['tracking-stats'],
    queryFn: () => api.tracking.getStats(),
  });

  const { data: bets, isLoading: betsLoading } = useQuery({
    queryKey: ['tracked-bets', statusFilter, sportFilter],
    queryFn: () => api.tracking.getBets(statusFilter || undefined, sportFilter || undefined),
  });

  const { data: leaderboard } = useQuery({
    queryKey: ['leaderboard'],
    queryFn: () => api.tracking.getLeaderboard('total_profit', 10),
  });

  const placeBetMutation = useMutation({
    mutationFn: api.tracking.placeBet,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tracked-bets'] });
      queryClient.invalidateQueries({ queryKey: ['tracking-stats'] });
      setShowAddBet(false);
    },
  });

  const settleBetMutation = useMutation({
    mutationFn: ({ betId, result }: { betId: number; result: string }) =>
      api.tracking.settleBet(betId, result),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tracked-bets'] });
      queryClient.invalidateQueries({ queryKey: ['tracking-stats'] });
    },
  });

  const handleAddBet = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    placeBetMutation.mutate({
      sport: formData.get('sport') as string,
      bet_type: formData.get('bet_type') as string,
      selection: formData.get('selection') as string,
      odds: parseInt(formData.get('odds') as string),
      stake: parseFloat(formData.get('stake') as string),
      sportsbook: formData.get('sportsbook') as string || undefined,
    });
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  const formatMoney = (amount: number) => {
    return amount >= 0 ? `+$${amount.toFixed(2)}` : `-$${Math.abs(amount).toFixed(2)}`;
  };

  const getBetStatusLabel = (status: string, result?: string | null) => {
    if (status === 'pending') return 'In Play';
    if (result === 'won') return 'Cashed ✓';
    if (result === 'lost') return 'Missed';
    return result?.toUpperCase() || status;
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">Your Bets</h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Track performance. See your edge.
          </p>
        </div>
        <Button onClick={() => setShowAddBet(!showAddBet)} size="lg">
          {showAddBet ? 'Cancel' : 'Track a Bet'}
        </Button>
      </div>

      {/* Add Bet Form */}
      {showAddBet && (
        <Card padding="lg">
          <h2 className="text-h2 text-surface-900 dark:text-white mb-6">Track a Bet</h2>
          <form onSubmit={handleAddBet} className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Select name="sport" required>
              <option value="">Select Sport</option>
              {SPORTS.map(sport => (
                <option key={sport} value={sport}>{sport.replace('_', ' ')}</option>
              ))}
            </Select>
            <Select name="bet_type" required>
              <option value="">Bet Type</option>
              <option value="moneyline">Moneyline</option>
              <option value="spread">Spread</option>
              <option value="total">Total</option>
              <option value="prop">Prop</option>
              <option value="future">Future</option>
            </Select>
            <Input name="selection" placeholder="Selection (e.g., Team A -3.5)" required />
            <Input name="odds" type="number" placeholder="Odds (-110, +150)" required />
            <Input name="stake" type="number" step="0.01" placeholder="Stake ($)" required />
            <Input name="sportsbook" placeholder="Sportsbook (optional)" />
            <div className="md:col-span-3">
              <Button type="submit" disabled={placeBetMutation.isPending}>
                {placeBetMutation.isPending ? 'Adding...' : 'Track This'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-success-50 dark:bg-success-500/10">
              <DollarSign className="w-6 h-6 text-success-600 dark:text-success-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Performance</p>
              <p className={`text-2xl font-bold ${(stats?.total_profit || 0) >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                {stats ? formatMoney(stats.total_profit) : '$0.00'}
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-primary-50 dark:bg-primary-500/10">
              <Target className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Precision Rate</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                {stats?.win_rate.toFixed(1) || 0}%
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-warning-50 dark:bg-warning-500/10">
              <Percent className="w-6 h-6 text-warning-600 dark:text-warning-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">ROI</p>
              <p className={`text-2xl font-bold ${(stats?.roi || 0) >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                {stats?.roi.toFixed(2) || 0}%
              </p>
            </div>
          </div>
        </Card>
        <Card padding="md">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-2xl bg-primary-50 dark:bg-primary-500/10">
              <Activity className="w-6 h-6 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <p className="text-sm font-medium text-surface-500 dark:text-surface-400">Current Streak</p>
              <p className="text-2xl font-bold text-surface-900 dark:text-white">
                {stats?.current_streak || 0} W
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bets List */}
        <div className="lg:col-span-2">
          <Card padding="lg">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <h2 className="text-h2 text-surface-900 dark:text-white">All Bets</h2>
              <div className="flex gap-2">
                <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="">All Status</option>
                  <option value="pending">In Play</option>
                  <option value="settled">Settled</option>
                </Select>
                <Select value={sportFilter} onChange={(e) => setSportFilter(e.target.value)}>
                  <option value="">All Sports</option>
                  {SPORTS.map(sport => (
                    <option key={sport} value={sport}>{sport.replace('_', ' ')}</option>
                  ))}
                </Select>
              </div>
            </div>

            {betsLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner text="Analyzing..." />
              </div>
            ) : bets?.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No bets yet"
                description="Track your first bet to see performance."
                action={{
                  label: 'Track a Bet',
                  onClick: () => setShowAddBet(true),
                }}
              />
            ) : (
              <div className="space-y-3">
                {bets?.map(bet => (
                  <div key={bet.id} className="border border-surface-200 dark:border-surface-700 rounded-xl p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <Badge variant="primary">{bet.sport}</Badge>
                          <Badge variant="neutral">{bet.bet_type}</Badge>
                          <Badge variant={bet.status === 'pending' ? 'warning' : bet.result === 'won' ? 'success' : 'danger'}>
                            {getBetStatusLabel(bet.status, bet.result)}
                          </Badge>
                        </div>
                        <p className="font-semibold text-surface-900 dark:text-white">{bet.selection}</p>
                        <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
                          {formatOdds(bet.odds)} · ${bet.stake.toFixed(2)} stake
                          {bet.sportsbook && ` · ${bet.sportsbook}`}
                        </p>
                      </div>
                      <div className="text-right">
                        {bet.status === 'settled' && bet.profit_loss !== null && (
                          <p className={`text-lg font-bold ${bet.profit_loss >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                            {formatMoney(bet.profit_loss)}
                          </p>
                        )}
                        {bet.status === 'pending' && (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => settleBetMutation.mutate({ betId: bet.id, result: 'won' })}
                            >
                              Cashed
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => settleBetMutation.mutate({ betId: bet.id, result: 'lost' })}
                            >
                              Missed
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => settleBetMutation.mutate({ betId: bet.id, result: 'push' })}
                            >
                              Push
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Leaderboard Preview */}
          <Card padding="lg">
            <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Leaderboard</h2>
            {leaderboard?.length === 0 ? (
              <EmptyState
                icon={Trophy}
                title="No entries yet"
                description="The leaderboard updates weekly."
                className="py-4"
              />
            ) : (
              <div className="space-y-3">
                {leaderboard?.map((entry, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b border-surface-200 dark:border-surface-700 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className={`w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold ${
                        idx === 0 ? 'bg-warning-100 text-warning-700 dark:bg-warning-500/20 dark:text-warning-400' :
                        idx === 1 ? 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300' :
                        idx === 2 ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400' :
                        'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400'
                      }`}>
                        {entry.rank}
                      </span>
                      <span className="font-medium text-surface-900 dark:text-white">{entry.display_name}</span>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold ${entry.total_profit >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
                        {formatMoney(entry.total_profit)}
                      </p>
                      <p className="text-xs text-surface-500 dark:text-surface-400">{entry.roi_percentage.toFixed(1)}% ROI</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Performance Stats */}
          <Card padding="lg">
            <h2 className="text-h2 text-surface-900 dark:text-white mb-4">Your Edge</h2>
            {statsLoading ? (
              <div className="flex justify-center py-4">
                <LoadingSpinner size="sm" />
              </div>
            ) : stats ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Total Bets</span>
                  <span className="font-medium text-surface-900 dark:text-white">{stats.total_bets}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Cashed / Missed</span>
                  <span className="font-medium text-surface-900 dark:text-white">{stats.winning_bets} / {stats.losing_bets}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Total Staked</span>
                  <span className="font-medium text-surface-900 dark:text-white">${stats.total_staked.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Avg Odds</span>
                  <span className="font-medium text-surface-900 dark:text-white">{formatOdds(stats.average_odds)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Best Win</span>
                  <span className="font-medium text-success-600 dark:text-success-400">${stats.best_win.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Worst Loss</span>
                  <span className="font-medium text-danger-600 dark:text-danger-400">-${Math.abs(stats.worst_loss).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-surface-500 dark:text-surface-400">Best Streak</span>
                  <span className="font-medium text-surface-900 dark:text-white">{stats.best_streak} wins</span>
                </div>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
