import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import { api } from '@/lib/api';
import { Trophy, Medal, Award, Info } from 'lucide-react';

export default function Leaderboard() {
  const [sortBy, setSortBy] = useState('total_profit');

  const { data: leaderboard, isLoading } = useQuery({
    queryKey: ['leaderboard', sortBy],
    queryFn: () => api.tracking.getLeaderboard(sortBy, 50),
  });

  const formatMoney = (amount: number) => {
    return amount >= 0 ? `+$${amount.toFixed(2)}` : `-$${Math.abs(amount).toFixed(2)}`;
  };

  const getRankStyle = (rank: number) => {
    if (rank === 1) return 'bg-warning-100 text-warning-700 dark:bg-warning-500/20 dark:text-warning-400';
    if (rank === 2) return 'bg-surface-200 text-surface-700 dark:bg-surface-700 dark:text-surface-300';
    if (rank === 3) return 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400';
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400';
  };

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Trophy className="w-4 h-4" />;
    if (rank === 2) return <Medal className="w-4 h-4" />;
    if (rank === 3) return <Award className="w-4 h-4" />;
    return null;
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">Leaderboard</h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            The best. Ranked.
          </p>
        </div>
        <div className="w-full sm:w-56">
          <Select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="total_profit">Total Profit</option>
            <option value="roi">ROI %</option>
            <option value="weekly">Weekly Profit</option>
            <option value="monthly">Monthly Profit</option>
            <option value="streak">Current Streak</option>
          </Select>
        </div>
      </div>

      {/* Leaderboard Table */}
      <Card padding="lg">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <LoadingSpinner size="lg" text="Analyzing..." />
          </div>
        ) : leaderboard?.length === 0 ? (
          <EmptyState
            icon={Trophy}
            title="No entries yet"
            description="Track 10+ bets to rank."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-surface-500 dark:text-surface-400 border-b border-surface-200 dark:border-surface-700">
                  <th className="pb-4 pr-4 font-medium">Rank</th>
                  <th className="pb-4 pr-4 font-medium">Bettor</th>
                  <th className="pb-4 pr-4 text-center font-medium">Bets</th>
                  <th className="pb-4 pr-4 text-center font-medium">Precision</th>
                  <th className="pb-4 pr-4 text-right font-medium">Profit</th>
                  <th className="pb-4 pr-4 text-right font-medium">ROI</th>
                  <th className="pb-4 text-center font-medium">Streak</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard?.map((entry) => (
                  <tr key={entry.rank} className="border-b border-surface-200 dark:border-surface-700 last:border-0">
                    <td className="py-4 pr-4">
                      <span
                        className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm ${getRankStyle(
                          entry.rank
                        )}`}
                      >
                        {getRankIcon(entry.rank) || entry.rank}
                      </span>
                    </td>
                    <td className="py-4 pr-4">
                      <span className="font-semibold text-surface-900 dark:text-white">{entry.display_name}</span>
                    </td>
                    <td className="py-4 pr-4 text-center text-surface-600 dark:text-surface-400">
                      {entry.total_bets}
                    </td>
                    <td className="py-4 pr-4 text-center">
                      <span className="text-surface-600 dark:text-surface-400">
                        {entry.total_bets > 0
                          ? ((entry.winning_bets / entry.total_bets) * 100).toFixed(1)
                          : 0}
                        %
                      </span>
                    </td>
                    <td className="py-4 pr-4 text-right">
                      <span
                        className={`font-bold ${
                          entry.total_profit >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
                        }`}
                      >
                        {formatMoney(entry.total_profit)}
                      </span>
                    </td>
                    <td className="py-4 pr-4 text-right">
                      <span
                        className={`font-medium ${
                          entry.roi_percentage >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'
                        }`}
                      >
                        {entry.roi_percentage.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-4 text-center">
                      {entry.current_streak > 0 ? (
                        <Badge variant="success">{entry.current_streak}W</Badge>
                      ) : (
                        <span className="text-surface-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* How Rankings Work */}
      <Card padding="lg" className="border-primary-200 dark:border-primary-500/30 bg-primary-50/50 dark:bg-primary-500/5">
        <div className="flex items-start gap-3">
          <Info className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
          <div>
            <h2 className="text-h2 text-primary-900 dark:text-primary-100 mb-4">How Rankings Work</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100 mb-1">Eligibility</p>
                <p className="text-primary-700 dark:text-primary-300">Track at least 10 settled bets to appear on the leaderboard</p>
              </div>
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100 mb-1">Privacy</p>
                <p className="text-primary-700 dark:text-primary-300">Your display name is shown (set in Profile). Email is never shared.</p>
              </div>
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100 mb-1">Updates</p>
                <p className="text-primary-700 dark:text-primary-300">Rankings update automatically when bets are settled</p>
              </div>
              <div>
                <p className="font-medium text-primary-900 dark:text-primary-100 mb-1">Opt Out</p>
                <p className="text-primary-700 dark:text-primary-300">You can hide your profile from the leaderboard in Settings</p>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
