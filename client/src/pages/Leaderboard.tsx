import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Card from '@/components/ui/Card';
import Select from '@/components/ui/Select';
import Badge from '@/components/ui/Badge';
import { api } from '@/lib/api';

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
    if (rank === 1) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300';
    if (rank === 2) return 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    if (rank === 3) return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300';
    return 'bg-surface-100 text-surface-600 dark:bg-surface-800 dark:text-surface-400';
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Leaderboard</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">See how you stack up against other bettors</p>
        </div>
        <Select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="total_profit">Total Profit</option>
          <option value="roi">ROI %</option>
          <option value="weekly">Weekly Profit</option>
          <option value="monthly">Monthly Profit</option>
          <option value="streak">Current Streak</option>
        </Select>
      </div>

      <Card className="p-6">
        {isLoading ? (
          <p className="text-gray-500 text-center py-8">Loading leaderboard...</p>
        ) : leaderboard?.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 dark:text-gray-400 mb-2">No entries yet</p>
            <p className="text-sm text-gray-400 dark:text-gray-500">
              Track at least 10 bets to appear on the leaderboard
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b dark:border-gray-700">
                  <th className="pb-3 pr-4">Rank</th>
                  <th className="pb-3 pr-4">Bettor</th>
                  <th className="pb-3 pr-4 text-center">Bets</th>
                  <th className="pb-3 pr-4 text-center">Win Rate</th>
                  <th className="pb-3 pr-4 text-right">Profit</th>
                  <th className="pb-3 pr-4 text-right">ROI</th>
                  <th className="pb-3 text-center">Streak</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard?.map((entry) => (
                  <tr key={entry.rank} className="border-b dark:border-gray-700 last:border-0">
                    <td className="py-4 pr-4">
                      <span
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${getRankStyle(
                          entry.rank
                        )}`}
                      >
                        {entry.rank}
                      </span>
                    </td>
                    <td className="py-4 pr-4">
                      <span className="font-medium text-gray-900 dark:text-white">{entry.display_name}</span>
                    </td>
                    <td className="py-4 pr-4 text-center text-gray-600 dark:text-gray-300">
                      {entry.total_bets}
                    </td>
                    <td className="py-4 pr-4 text-center">
                      <span className="text-gray-600 dark:text-gray-300">
                        {entry.total_bets > 0
                          ? ((entry.winning_bets / entry.total_bets) * 100).toFixed(1)
                          : 0}
                        %
                      </span>
                    </td>
                    <td className="py-4 pr-4 text-right">
                      <span
                        className={`font-bold ${
                          entry.total_profit >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {formatMoney(entry.total_profit)}
                      </span>
                    </td>
                    <td className="py-4 pr-4 text-right">
                      <span
                        className={`font-medium ${
                          entry.roi_percentage >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}
                      >
                        {entry.roi_percentage.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-4 text-center">
                      {entry.current_streak > 0 ? (
                        <Badge variant="success">{entry.current_streak}W</Badge>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4 dark:text-white">How Rankings Work</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 dark:text-gray-400">
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1">Eligibility</p>
            <p>Track at least 10 settled bets to appear on the leaderboard</p>
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1">Privacy</p>
            <p>Your display name is shown (set in Profile). Email is never shared.</p>
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1">Updates</p>
            <p>Rankings update automatically when bets are settled</p>
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1">Opt Out</p>
            <p>You can hide your profile from the leaderboard in Settings</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
