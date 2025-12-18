import React, { useEffect, useState } from 'react';
import { Card, Badge, Button } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import ErrorMessage from '@/components/ui/ErrorMessage';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';
import {
  TrendingUp,
  Target,
  Percent,
  DollarSign,
  BarChart3,
  CheckCircle2,
  XCircle,
  Clock,
  Download,
  RefreshCw,
  Flame,
  Snowflake,
  Activity,
  ChevronDown,
  ChevronUp,
  Thermometer,
  Wind,
  Cloud
} from 'lucide-react';

interface TrackerStats {
  total_picks: number;
  wins: number;
  losses: number;
  pushes: number;
  win_rate: number;
  expected_rate: number;
  edge: number;
  roi: number;
  units_won: number;
  total_wagered: number;
  p_value: number;
  confidence_interval: [number, number];
  is_significant: boolean;
  sample_size_needed: number;
  current_sample: number;
  current_confidence: number;
}

interface StreakAnalysis {
  current_streak: number;
  current_streak_type: string | null;
  longest_win_streak: number;
  longest_loss_streak: number;
  max_drawdown: number;
  max_drawdown_picks: number;
}

interface FactorData {
  total_picks: number;
  wins_when_high: number;
  total_when_high: number;
  win_rate_high: number;
  wins_when_low: number;
  total_when_low: number;
  win_rate_low: number;
  correlation: number;
  predictive_value: string;
}

interface FactorScore {
  score: number;
  detail?: string;
}

interface Pick {
  id: string;
  sport: string;
  home_team: string;
  away_team: string;
  pick: string;
  odds: number;
  confidence: number;
  status: string;
  units_wagered: number;
  units_result: number | null;
  created_at: string;
  settled_at: string | null;
  result_score?: string;
  factors?: Record<string, FactorScore>;
  weather_data?: {
    temp_f?: number;
    wind_mph?: number;
    condition?: string;
    is_dome?: boolean;
  };
}

interface BankrollPoint {
  timestamp: string;
  balance: number;
  total_picks: number;
  roi: number;
  win_rate: number;
}

interface TrackerSummary {
  validation_status: string;
  stats: TrackerStats;
  streaks: StreakAnalysis;
  by_sport: Record<string, any>;
  by_confidence: Record<string, any>;
  recent_picks: Pick[];
  current_bankroll: number;
  bankroll_history: BankrollPoint[];
}

interface FactorAnalysis {
  total_analyzed: number;
  factors: Record<string, FactorData>;
}

const FACTOR_NAMES: Record<string, string> = {
  coach_dna: 'Coach DNA',
  referee: 'Referee/Official',
  weather: 'Weather',
  line_movement: 'Line Movement',
  rest: 'Rest Days',
  travel: 'Travel',
  situational: 'Situational',
  public_betting: 'Public Betting'
};

export default function EdgeTracker() {
  const [summary, setSummary] = useState<TrackerSummary | null>(null);
  const [factors, setFactors] = useState<FactorAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSettling, setIsSettling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPicks, setExpandedPicks] = useState<Set<string>>(new Set());

  const togglePickExpanded = (pickId: string) => {
    setExpandedPicks(prev => {
      const next = new Set(prev);
      if (next.has(pickId)) {
        next.delete(pickId);
      } else {
        next.add(pickId);
      }
      return next;
    });
  };

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [summaryRes, factorsRes] = await Promise.all([
        fetch('/api/tracker/summary'),
        fetch('/api/tracker/factors')
      ]);

      if (summaryRes.ok) {
        setSummary(await summaryRes.json());
      }
      if (factorsRes.ok) {
        setFactors(await factorsRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch tracker data:', err);
      setError('Failed to load tracker data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAutoSettle = async () => {
    setIsSettling(true);
    try {
      const res = await fetch('/api/tracker/auto-settle', { method: 'POST' });
      if (res.ok) {
        await fetchData();
      }
    } catch (err) {
      console.error('Auto-settle failed:', err);
    } finally {
      setIsSettling(false);
    }
  };

  const handleExport = async () => {
    window.open('/api/tracker/export?format=csv', '_blank');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text="Loading tracker data..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <ErrorMessage message={error} onRetry={fetchData} />
      </div>
    );
  }

  const stats = summary?.stats;
  const streaks = summary?.streaks;

  // Format bankroll data for chart
  const bankrollData = summary?.bankroll_history?.map((point, index) => ({
    name: index === 0 ? 'Start' : `Pick ${point.total_picks}`,
    balance: point.balance,
    roi: point.roi
  })) || [];

  // Validation status badge
  const getValidationBadge = (status: string) => {
    switch (status) {
      case 'VALIDATED':
        return <Badge variant="success" className="text-sm px-3 py-1">Edge Validated</Badge>;
      case 'PROMISING':
        return <Badge variant="warning" className="text-sm px-3 py-1">Promising Edge</Badge>;
      case 'NEEDS_MORE_DATA':
        return <Badge variant="neutral" className="text-sm px-3 py-1">Needs More Data</Badge>;
      case 'NO_EDGE':
        return <Badge variant="danger" className="text-sm px-3 py-1">No Edge Detected</Badge>;
      default:
        return <Badge variant="neutral" className="text-sm px-3 py-1">Insufficient Data</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Edge Validation Tracker</h1>
          <p className="text-gray-400 mt-1">Prove your edge before scaling up</p>
        </div>
        <div className="flex items-center gap-3">
          {summary && getValidationBadge(summary.validation_status)}
          <Button
            variant="outline"
            size="sm"
            onClick={handleAutoSettle}
            disabled={isSettling}
          >
            {isSettling ? <LoadingSpinner size="sm" /> : <RefreshCw className="h-4 w-4 mr-2" />}
            Auto-Settle
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Stats Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Target className="h-4 w-4" />
            Total Picks
          </div>
          <div className="text-2xl font-bold text-white">{stats?.total_picks || 0}</div>
          <div className="text-xs text-gray-500 mt-1">
            {stats?.wins || 0}W - {stats?.losses || 0}L - {stats?.pushes || 0}P
          </div>
        </Card>

        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Percent className="h-4 w-4" />
            Win Rate
          </div>
          <div className={`text-2xl font-bold ${(stats?.win_rate || 0) > 52.4 ? 'text-green-400' : 'text-white'}`}>
            {stats?.win_rate?.toFixed(1) || 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            vs {stats?.expected_rate?.toFixed(1) || 52.4}% expected
          </div>
        </Card>

        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <TrendingUp className="h-4 w-4" />
            Edge
          </div>
          <div className={`text-2xl font-bold ${(stats?.edge || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {(stats?.edge || 0) > 0 ? '+' : ''}{stats?.edge?.toFixed(1) || 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Win rate - expected
          </div>
        </Card>

        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <DollarSign className="h-4 w-4" />
            ROI
          </div>
          <div className={`text-2xl font-bold ${(stats?.roi || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {(stats?.roi || 0) > 0 ? '+' : ''}{stats?.roi?.toFixed(1) || 0}%
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {(stats?.units_won || 0) > 0 ? '+' : ''}{stats?.units_won?.toFixed(2) || 0} units
          </div>
        </Card>

        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Activity className="h-4 w-4" />
            P-Value
          </div>
          <div className={`text-2xl font-bold ${stats?.is_significant ? 'text-green-400' : 'text-yellow-400'}`}>
            {stats?.p_value?.toFixed(3) || 'N/A'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {stats?.is_significant ? 'Significant (p < 0.05)' : 'Not significant'}
          </div>
        </Card>

        <Card className="p-4 bg-gray-800/50 border-gray-700">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <BarChart3 className="h-4 w-4" />
            Confidence
          </div>
          <div className="text-2xl font-bold text-white">{stats?.current_confidence?.toFixed(0) || 0}%</div>
          <div className="text-xs text-gray-500 mt-1">
            {stats?.current_sample || 0}/{stats?.sample_size_needed || 384} picks
          </div>
        </Card>
      </div>

      {/* Bankroll Chart & Streaks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bankroll Chart */}
        <Card className="lg:col-span-2 p-6 bg-gray-800/50 border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Bankroll History</h3>
          <div className="h-64">
            {bankrollData.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={bankrollData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} />
                  <YAxis stroke="#9CA3AF" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1F2937',
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                  />
                  <defs>
                    <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <Area
                    type="monotone"
                    dataKey="balance"
                    stroke="#10B981"
                    fill="url(#balanceGradient)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <BarChart3 className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Log picks to see bankroll history</p>
                </div>
              </div>
            )}
          </div>
          <div className="flex items-center justify-between mt-4 text-sm">
            <div className="text-gray-400">Starting: 100.0 units</div>
            <div className={`font-semibold ${(summary?.current_bankroll || 100) >= 100 ? 'text-green-400' : 'text-red-400'}`}>
              Current: {summary?.current_bankroll?.toFixed(2) || '100.00'} units
            </div>
          </div>
        </Card>

        {/* Streak Analysis */}
        <Card className="p-6 bg-gray-800/50 border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Streak Analysis</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Current Streak</span>
              <div className="flex items-center gap-2">
                {streaks?.current_streak_type === 'win' ? (
                  <Flame className="h-4 w-4 text-green-400" />
                ) : streaks?.current_streak_type === 'loss' ? (
                  <Snowflake className="h-4 w-4 text-blue-400" />
                ) : null}
                <span className={`font-bold ${
                  streaks?.current_streak_type === 'win' ? 'text-green-400' :
                  streaks?.current_streak_type === 'loss' ? 'text-red-400' : 'text-white'
                }`}>
                  {streaks?.current_streak || 0} {streaks?.current_streak_type || ''}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-gray-400">Longest Win Streak</span>
              <span className="font-bold text-green-400">{streaks?.longest_win_streak || 0}</span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-gray-400">Longest Loss Streak</span>
              <span className="font-bold text-red-400">{streaks?.longest_loss_streak || 0}</span>
            </div>

            <div className="border-t border-gray-700 pt-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Max Drawdown</span>
                <span className="font-bold text-red-400">-{streaks?.max_drawdown?.toFixed(1) || 0}%</span>
              </div>
              <div className="text-xs text-gray-500 mt-1">
                Over {streaks?.max_drawdown_picks || 0} picks
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Statistical Significance Meter */}
      <Card className="p-6 bg-gray-800/50 border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Statistical Significance Progress</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">Progress to 95% confidence</span>
            <span className="text-white font-medium">
              {stats?.current_sample || 0} / {stats?.sample_size_needed || 384} picks
            </span>
          </div>
          <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                stats?.is_significant ? 'bg-green-500' : 'bg-blue-500'
              }`}
              style={{
                width: `${Math.min(100, ((stats?.current_sample || 0) / (stats?.sample_size_needed || 384)) * 100)}%`
              }}
            />
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">
              {stats?.is_significant
                ? 'Statistically significant! Your edge is real.'
                : `Need ${(stats?.sample_size_needed || 384) - (stats?.current_sample || 0)} more picks for 95% confidence`
              }
            </span>
            <span className="text-gray-400">
              CI: [{stats?.confidence_interval?.[0]?.toFixed(1) || 0}% - {stats?.confidence_interval?.[1]?.toFixed(1) || 100}%]
            </span>
          </div>
        </div>

        {/* Milestones */}
        <div className="grid grid-cols-4 gap-4 mt-6">
          <div className={`text-center p-3 rounded-lg ${(stats?.total_picks || 0) >= 50 ? 'bg-green-900/30' : 'bg-gray-700/30'}`}>
            <div className={`text-lg font-bold ${(stats?.total_picks || 0) >= 50 ? 'text-green-400' : 'text-gray-500'}`}>50</div>
            <div className="text-xs text-gray-400">Initial Data</div>
          </div>
          <div className={`text-center p-3 rounded-lg ${(stats?.total_picks || 0) >= 100 ? 'bg-green-900/30' : 'bg-gray-700/30'}`}>
            <div className={`text-lg font-bold ${(stats?.total_picks || 0) >= 100 ? 'text-green-400' : 'text-gray-500'}`}>100</div>
            <div className="text-xs text-gray-400">Min Analysis</div>
          </div>
          <div className={`text-center p-3 rounded-lg ${(stats?.total_picks || 0) >= 200 ? 'bg-green-900/30' : 'bg-gray-700/30'}`}>
            <div className={`text-lg font-bold ${(stats?.total_picks || 0) >= 200 ? 'text-green-400' : 'text-gray-500'}`}>200</div>
            <div className="text-xs text-gray-400">Real Money Ready</div>
          </div>
          <div className={`text-center p-3 rounded-lg ${stats?.is_significant ? 'bg-green-900/30' : 'bg-gray-700/30'}`}>
            <div className={`text-lg font-bold ${stats?.is_significant ? 'text-green-400' : 'text-gray-500'}`}>{stats?.sample_size_needed || 384}</div>
            <div className="text-xs text-gray-400">95% Confident</div>
          </div>
        </div>
      </Card>

      {/* Factor Performance */}
      {factors && factors.factors && Object.keys(factors.factors).length > 0 && (
        <Card className="p-6 bg-gray-800/50 border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Factor Performance Analysis</h3>
          <p className="text-sm text-gray-400 mb-4">
            Analyzing {factors.total_analyzed} settled picks to identify which factors predict wins
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3 font-medium">Factor</th>
                  <th className="pb-3 font-medium text-center">Picks</th>
                  <th className="pb-3 font-medium text-center">Win Rate (High)</th>
                  <th className="pb-3 font-medium text-center">Win Rate (Low)</th>
                  <th className="pb-3 font-medium text-center">Correlation</th>
                  <th className="pb-3 font-medium text-center">Predictive Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(factors.factors).map(([key, factor]) => (
                  <tr key={key} className="border-b border-gray-700/50">
                    <td className="py-3 font-medium text-white">{FACTOR_NAMES[key] || key}</td>
                    <td className="py-3 text-center text-gray-300">{factor.total_picks}</td>
                    <td className="py-3 text-center">
                      <span className={factor.win_rate_high > 52.4 ? 'text-green-400' : 'text-gray-300'}>
                        {factor.win_rate_high.toFixed(1)}%
                      </span>
                      <span className="text-gray-500 text-xs ml-1">({factor.total_when_high})</span>
                    </td>
                    <td className="py-3 text-center">
                      <span className={factor.win_rate_low < 50 ? 'text-red-400' : 'text-gray-300'}>
                        {factor.win_rate_low.toFixed(1)}%
                      </span>
                      <span className="text-gray-500 text-xs ml-1">({factor.total_when_low})</span>
                    </td>
                    <td className="py-3 text-center">
                      <span className={factor.correlation > 0.2 ? 'text-green-400' : factor.correlation > 0.1 ? 'text-yellow-400' : 'text-gray-400'}>
                        {factor.correlation.toFixed(3)}
                      </span>
                    </td>
                    <td className="py-3 text-center">
                      <Badge
                        variant={
                          factor.predictive_value === 'HIGH' ? 'success' :
                          factor.predictive_value === 'MEDIUM' ? 'warning' :
                          factor.predictive_value === 'LOW' ? 'neutral' : 'danger'
                        }
                        className="text-xs"
                      >
                        {factor.predictive_value}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Stats by Sport & Confidence */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Sport */}
        {summary?.by_sport && Object.keys(summary.by_sport).length > 0 && (
          <Card className="p-6 bg-gray-800/50 border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Performance by Sport</h3>
            <div className="space-y-3">
              {Object.entries(summary.by_sport).map(([sport, data]: [string, any]) => (
                <div key={sport} className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                  <div>
                    <div className="font-medium text-white">{sport}</div>
                    <div className="text-xs text-gray-400">{data.total_picks} picks</div>
                  </div>
                  <div className="text-right">
                    <div className={`font-bold ${data.win_rate > 52.4 ? 'text-green-400' : 'text-gray-300'}`}>
                      {data.win_rate.toFixed(1)}%
                    </div>
                    <div className={`text-xs ${data.units_won > 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {data.units_won > 0 ? '+' : ''}{data.units_won.toFixed(2)}u
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* By Confidence Tier */}
        {summary?.by_confidence && Object.keys(summary.by_confidence).length > 0 && (
          <Card className="p-6 bg-gray-800/50 border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Performance by Confidence</h3>
            <div className="space-y-3">
              {Object.entries(summary.by_confidence).map(([tier, data]: [string, any]) => (
                <div key={tier} className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                  <div>
                    <div className="font-medium text-white capitalize">{tier.replace('_', ' ')}</div>
                    <div className="text-xs text-gray-400">{data.confidence_range} confidence</div>
                  </div>
                  <div className="text-right">
                    <div className={`font-bold ${data.win_rate > 52.4 ? 'text-green-400' : 'text-gray-300'}`}>
                      {data.win_rate.toFixed(1)}%
                    </div>
                    <div className="text-xs text-gray-400">{data.total_picks} picks</div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>

      {/* Recent Picks */}
      <Card className="p-6 bg-gray-800/50 border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Recent Picks</h3>
        {summary?.recent_picks && summary.recent_picks.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3 font-medium w-8"></th>
                  <th className="pb-3 font-medium">Date</th>
                  <th className="pb-3 font-medium">Sport</th>
                  <th className="pb-3 font-medium">Pick</th>
                  <th className="pb-3 font-medium text-center">Odds</th>
                  <th className="pb-3 font-medium text-center">Confidence</th>
                  <th className="pb-3 font-medium text-center">Units</th>
                  <th className="pb-3 font-medium text-center">Result</th>
                </tr>
              </thead>
              <tbody>
                {summary.recent_picks.map((pick) => (
                  <React.Fragment key={pick.id}>
                    <tr
                      className="border-b border-gray-700/50 cursor-pointer hover:bg-gray-700/30 transition-colors"
                      onClick={() => togglePickExpanded(pick.id)}
                    >
                      <td className="py-3 text-gray-400">
                        {expandedPicks.has(pick.id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </td>
                      <td className="py-3 text-gray-300">
                        {new Date(pick.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3">
                        <Badge variant="neutral" className="text-xs">{pick.sport}</Badge>
                      </td>
                      <td className="py-3 text-white">
                        <div>{pick.pick}</div>
                        <div className="text-xs text-gray-500">{pick.away_team} @ {pick.home_team}</div>
                      </td>
                      <td className="py-3 text-center text-gray-300">
                        {pick.odds > 0 ? '+' : ''}{pick.odds}
                      </td>
                      <td className="py-3 text-center">
                        <span className={`font-medium ${
                          pick.confidence >= 80 ? 'text-green-400' :
                          pick.confidence >= 70 ? 'text-yellow-400' : 'text-gray-400'
                        }`}>
                          {pick.confidence.toFixed(0)}%
                        </span>
                      </td>
                      <td className="py-3 text-center text-gray-300">{pick.units_wagered.toFixed(1)}</td>
                      <td className="py-3 text-center">
                        {pick.status === 'pending' ? (
                          <Badge variant="neutral" className="text-xs">
                            <Clock className="h-3 w-3 mr-1" />
                            Pending
                          </Badge>
                        ) : pick.status === 'won' ? (
                          <Badge variant="success" className="text-xs">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            +{pick.units_result?.toFixed(2)}u
                          </Badge>
                        ) : pick.status === 'lost' ? (
                          <Badge variant="danger" className="text-xs">
                            <XCircle className="h-3 w-3 mr-1" />
                            {pick.units_result?.toFixed(2)}u
                          </Badge>
                        ) : (
                          <Badge variant="neutral" className="text-xs">Push</Badge>
                        )}
                      </td>
                    </tr>
                    {/* Expanded Factor Breakdown */}
                    {expandedPicks.has(pick.id) && (
                      <tr key={`${pick.id}-expanded`} className="bg-gray-900/50">
                        <td colSpan={8} className="px-4 py-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* 8 Factor Breakdown */}
                            <div>
                              <h4 className="text-sm font-semibold text-white mb-3">8-Factor Breakdown</h4>
                              {pick.factors ? (
                                <div className="grid grid-cols-2 gap-2">
                                  {Object.entries(FACTOR_NAMES).map(([key, label]) => {
                                    const factor = pick.factors?.[key];
                                    const score = factor?.score ?? 50;
                                    // Color coding: Red (<50), Yellow (50-65), Green (>65)
                                    const getScoreColor = (s: number) => {
                                      if (s > 65) return 'text-green-400';
                                      if (s >= 50) return 'text-yellow-400';
                                      return 'text-red-400';
                                    };
                                    const getBarColor = (s: number) => {
                                      if (s > 65) return 'bg-green-500';
                                      if (s >= 50) return 'bg-yellow-500';
                                      return 'bg-red-500';
                                    };
                                    return (
                                      <div key={key} className="bg-gray-800/50 rounded p-2">
                                        <div className="flex justify-between items-center mb-1">
                                          <span className="text-xs text-gray-400">{label}</span>
                                          <span className={`text-xs font-medium ${getScoreColor(score)}`}>
                                            {score.toFixed(0)}
                                          </span>
                                        </div>
                                        <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                                          <div
                                            className={`h-full rounded-full ${getBarColor(score)}`}
                                            style={{ width: `${score}%` }}
                                          />
                                        </div>
                                        {factor?.detail && (
                                          <div className="text-xs text-gray-500 mt-1 truncate" title={factor.detail}>
                                            {factor.detail}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              ) : (
                                <div className="text-sm text-gray-500 italic">
                                  No factor data available for this pick
                                </div>
                              )}
                            </div>

                            {/* Weather & Game Details */}
                            <div>
                              <h4 className="text-sm font-semibold text-white mb-3">Game Details</h4>
                              <div className="space-y-3">
                                {/* Result Score */}
                                {pick.result_score && (
                                  <div className="bg-gray-800/50 rounded p-3">
                                    <div className="text-xs text-gray-400 mb-1">Final Score</div>
                                    <div className="text-white font-medium">{pick.result_score}</div>
                                  </div>
                                )}

                                {/* Weather Data */}
                                {pick.weather_data && (
                                  <div className="bg-gray-800/50 rounded p-3">
                                    <div className="text-xs text-gray-400 mb-2">Weather at Game Time</div>
                                    {pick.weather_data.is_dome ? (
                                      <div className="text-gray-300">Indoor / Dome Stadium</div>
                                    ) : (
                                      <div className="flex items-center gap-4 text-sm">
                                        {pick.weather_data.temp_f !== undefined && (
                                          <div className="flex items-center gap-1">
                                            <Thermometer className="h-4 w-4 text-blue-400" />
                                            <span className="text-gray-300">{pick.weather_data.temp_f}°F</span>
                                          </div>
                                        )}
                                        {pick.weather_data.wind_mph !== undefined && (
                                          <div className="flex items-center gap-1">
                                            <Wind className="h-4 w-4 text-cyan-400" />
                                            <span className="text-gray-300">{pick.weather_data.wind_mph} mph</span>
                                          </div>
                                        )}
                                        {pick.weather_data.condition && (
                                          <div className="flex items-center gap-1">
                                            <Cloud className="h-4 w-4 text-gray-400" />
                                            <span className="text-gray-300">{pick.weather_data.condition}</span>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                )}

                                {/* Settled Date */}
                                {pick.settled_at && (
                                  <div className="bg-gray-800/50 rounded p-3">
                                    <div className="text-xs text-gray-400 mb-1">Settled</div>
                                    <div className="text-gray-300 text-sm">
                                      {new Date(pick.settled_at).toLocaleString()}
                                    </div>
                                  </div>
                                )}

                                {/* No extra data */}
                                {!pick.result_score && !pick.weather_data && !pick.settled_at && (
                                  <div className="text-sm text-gray-500 italic">
                                    Game not yet completed
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Target className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>No picks logged yet. Start tracking to validate your edge!</p>
          </div>
        )}
      </Card>
    </div>
  );
}
