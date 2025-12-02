import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { api } from '@/lib/api';
import { SPORTS } from '@/types';

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

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Bet Tracking</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Track your bets and performance</p>
        </div>
        <Button onClick={() => setShowAddBet(!showAddBet)}>
          {showAddBet ? 'Cancel' : 'Track New Bet'}
        </Button>
      </div>

      {showAddBet && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4 dark:text-white">Add New Bet</h2>
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
            <Input name="odds" type="number" placeholder="Odds (-110, +150, etc)" required />
            <Input name="stake" type="number" step="0.01" placeholder="Stake ($)" required />
            <Input name="sportsbook" placeholder="Sportsbook (optional)" />
            <div className="md:col-span-3">
              <Button type="submit" disabled={placeBetMutation.isPending}>
                {placeBetMutation.isPending ? 'Adding...' : 'Add Bet'}
              </Button>
            </div>
          </form>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Profit</p>
          <p className={`text-2xl font-bold ${(stats?.total_profit || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {stats ? formatMoney(stats.total_profit) : '$0.00'}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Win Rate</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats?.win_rate.toFixed(1) || 0}%
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">ROI</p>
          <p className={`text-2xl font-bold ${(stats?.roi || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {stats?.roi.toFixed(2) || 0}%
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Current Streak</p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {stats?.current_streak || 0} W
          </p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold dark:text-white">Your Bets</h2>
              <div className="flex gap-2">
                <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="">All Status</option>
                  <option value="pending">Pending</option>
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
              <p className="text-gray-500">Loading bets...</p>
            ) : bets?.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-8">No bets tracked yet</p>
            ) : (
              <div className="space-y-3">
                {bets?.map(bet => (
                  <div key={bet.id} className="border dark:border-gray-700 rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary">{bet.sport}</Badge>
                          <Badge variant="outline">{bet.bet_type}</Badge>
                          <Badge variant={bet.status === 'pending' ? 'default' : bet.result === 'won' ? 'success' : 'destructive'}>
                            {bet.status === 'pending' ? 'Pending' : bet.result?.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="font-medium mt-2 dark:text-white">{bet.selection}</p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          {formatOdds(bet.odds)} | ${bet.stake.toFixed(2)} stake
                          {bet.sportsbook && ` | ${bet.sportsbook}`}
                        </p>
                      </div>
                      <div className="text-right">
                        {bet.status === 'settled' && bet.profit_loss !== null && (
                          <p className={`text-lg font-bold ${bet.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
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
                              Won
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => settleBetMutation.mutate({ betId: bet.id, result: 'lost' })}
                            >
                              Lost
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

        <div>
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Leaderboard</h2>
            {leaderboard?.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-center py-4">No entries yet</p>
            ) : (
              <div className="space-y-3">
                {leaderboard?.map((entry, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 border-b dark:border-gray-700 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold ${
                        idx === 0 ? 'bg-yellow-100 text-yellow-800' :
                        idx === 1 ? 'bg-gray-100 text-gray-800' :
                        idx === 2 ? 'bg-orange-100 text-orange-800' :
                        'bg-gray-50 text-gray-600'
                      }`}>
                        {entry.rank}
                      </span>
                      <span className="font-medium dark:text-white">{entry.display_name}</span>
                    </div>
                    <div className="text-right">
                      <p className={`font-bold ${entry.total_profit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatMoney(entry.total_profit)}
                      </p>
                      <p className="text-xs text-gray-500">{entry.roi_percentage.toFixed(1)}% ROI</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card className="p-6 mt-4">
            <h2 className="text-lg font-semibold mb-4 dark:text-white">Performance Stats</h2>
            {statsLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : stats ? (
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Total Bets</span>
                  <span className="font-medium dark:text-white">{stats.total_bets}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Won / Lost</span>
                  <span className="font-medium dark:text-white">{stats.winning_bets} / {stats.losing_bets}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Total Staked</span>
                  <span className="font-medium dark:text-white">${stats.total_staked.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Avg Odds</span>
                  <span className="font-medium dark:text-white">{formatOdds(stats.average_odds)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Best Win</span>
                  <span className="font-medium text-green-600">${stats.best_win.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Worst Loss</span>
                  <span className="font-medium text-red-600">-${Math.abs(stats.worst_loss).toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Best Streak</span>
                  <span className="font-medium dark:text-white">{stats.best_streak} wins</span>
                </div>
              </div>
            ) : null}
          </Card>
        </div>
      </div>
    </div>
  );
}
