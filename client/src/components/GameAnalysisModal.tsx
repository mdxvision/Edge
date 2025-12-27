import { useState, useEffect } from 'react';
import { X, Search, TrendingUp, AlertCircle, CheckCircle, Clock, Loader2 } from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';

interface PickData {
  sport: string;
  home_team: string;
  away_team: string;
  pick: string;
  pick_type: 'spread' | 'moneyline' | 'total';
  line_value?: number;
  odds: number;
  game_time: string;
  game_id: string;
}

interface FactorData {
  score: number;
  status: 'live' | 'pending';
  details: string;
}

interface AnalysisResult {
  game_id: string;
  sport: string;
  home_team: string;
  away_team: string;
  pick: string;
  pick_type: string;
  factors: Record<string, FactorData>;
  data_quality: number;
  overall_edge: number;
  confidence: number;
  recommendation: string;
  meets_threshold: boolean;
  weather_data?: Record<string, unknown>;
}

interface GameAnalysisModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProceedToLog: () => void;
  pickData: PickData;
}

const FACTOR_LABELS: Record<string, { name: string; icon: string }> = {
  coach_dna: { name: 'Coach DNA', icon: '🎯' },
  referee: { name: 'Referee Tendencies', icon: '👨‍⚖️' },
  weather: { name: 'Weather Impact', icon: '🌤️' },
  line_movement: { name: 'Line Movement', icon: '📊' },
  rest: { name: 'Rest Days', icon: '😴' },
  travel: { name: 'Travel Distance', icon: '✈️' },
  situational: { name: 'Situational ATS', icon: '📈' },
  public_betting: { name: 'Public Betting', icon: '👥' },
};

export default function GameAnalysisModal({
  isOpen,
  onClose,
  onProceedToLog,
  pickData
}: GameAnalysisModalProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    if (isOpen && pickData) {
      analyzeGame();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, pickData?.game_id, pickData?.pick]);

  const analyzeGame = async () => {
    setIsLoading(true);
    setError(null);
    setAnalysis(null);

    try {
      const response = await fetch('/api/tracker/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          game_id: pickData.game_id,
          sport: pickData.sport,
          home_team: pickData.home_team,
          away_team: pickData.away_team,
          game_time: pickData.game_time,
          pick_type: pickData.pick_type,
          pick: pickData.pick,
          line_value: pickData.line_value,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        const errorMsg = typeof data.detail === 'string'
          ? data.detail
          : data.detail?.msg || JSON.stringify(data.detail) || 'Failed to analyze game';
        throw new Error(errorMsg);
      }

      const data = await response.json();
      setAnalysis(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze game');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  const getScoreColor = (score: number) => {
    if (score >= 65) return 'text-green-400';
    if (score >= 55) return 'text-yellow-400';
    if (score >= 45) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 65) return 'bg-green-500/20';
    if (score >= 55) return 'bg-yellow-500/20';
    if (score >= 45) return 'bg-orange-500/20';
    return 'bg-red-500/20';
  };

  const getQualityColor = (percentage: number) => {
    if (percentage >= 75) return 'text-green-400';
    if (percentage >= 60) return 'text-yellow-400';
    return 'text-red-400';
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface-800 border border-surface-700 rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10">
              <Search className="w-5 h-5 text-blue-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">Game Analysis</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5 text-surface-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Pick Details */}
          <div className="bg-surface-900/50 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <Badge variant="primary">{pickData.sport}</Badge>
              <span className="text-sm text-surface-400">
                {new Date(pickData.game_time).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit'
                })}
              </span>
            </div>
            <div className="text-sm text-surface-400">
              {pickData.away_team} @ {pickData.home_team}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-lg font-bold text-white">{pickData.pick}</span>
              <span className="text-lg font-semibold text-primary-400">
                {formatOdds(pickData.odds)}
              </span>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-10 h-10 text-primary-400 animate-spin mb-4" />
              <p className="text-surface-400">Analyzing 8 factors...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{typeof error === 'string' ? error : 'An error occurred'}</span>
            </div>
          )}

          {/* Analysis Results */}
          {analysis && (
            <>
              {/* Recommendation Banner */}
              <div className={`p-4 rounded-xl border ${
                analysis.overall_edge >= 60
                  ? 'bg-green-500/10 border-green-500/20'
                  : analysis.overall_edge >= 50
                  ? 'bg-yellow-500/10 border-yellow-500/20'
                  : 'bg-red-500/10 border-red-500/20'
              }`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-surface-400">Recommendation</p>
                    <p className="text-xl font-bold text-white">{analysis.recommendation}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-surface-400">Confidence</p>
                    <p className={`text-2xl font-bold ${getScoreColor(analysis.confidence)}`}>
                      {analysis.confidence}%
                    </p>
                  </div>
                </div>
              </div>

              {/* Data Quality & Edge Score */}
              <div className="grid grid-cols-2 gap-3">
                <div className={`p-4 rounded-xl border ${
                  analysis.meets_threshold
                    ? 'bg-green-500/10 border-green-500/20'
                    : 'bg-yellow-500/10 border-yellow-500/20'
                }`}>
                  <div className="flex items-center gap-2 mb-1">
                    {analysis.meets_threshold ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <Clock className="w-4 h-4 text-yellow-400" />
                    )}
                    <span className="text-sm text-surface-400">Data Quality</span>
                  </div>
                  <p className={`text-2xl font-bold ${getQualityColor(analysis.data_quality)}`}>
                    {analysis.data_quality.toFixed(0)}%
                  </p>
                </div>
                <div className="p-4 rounded-xl bg-surface-900/50 border border-surface-700">
                  <p className="text-sm text-surface-400 mb-1">Overall Edge</p>
                  <p className={`text-2xl font-bold ${getScoreColor(analysis.overall_edge)}`}>
                    {analysis.overall_edge}
                  </p>
                </div>
              </div>

              {!analysis.meets_threshold && (
                <div className="p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-sm text-yellow-400">
                  Minimum 60% data quality required to log pick (5 of 8 factors must have live data)
                </div>
              )}

              {/* 8-Factor Breakdown */}
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-surface-400 uppercase tracking-wide">
                  8-Factor Breakdown
                </h3>
                <div className="grid gap-2">
                  {Object.entries(analysis.factors).map(([key, factor]) => {
                    const isLive = factor.status === 'live';
                    const label = FACTOR_LABELS[key] || { name: key, icon: '📊' };

                    return (
                      <div
                        key={key}
                        className={`p-3 rounded-xl border transition-colors ${
                          isLive
                            ? 'bg-surface-900/50 border-surface-700'
                            : 'bg-surface-900/30 border-surface-700/50'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{label.icon}</span>
                            <span className="font-medium text-white">{label.name}</span>
                            {!isLive && (
                              <Badge variant="outline" className="text-xs text-yellow-400 border-yellow-400/30">
                                Pending
                              </Badge>
                            )}
                          </div>
                          <div className={`px-3 py-1 rounded-lg font-bold ${getScoreBgColor(factor.score)} ${getScoreColor(factor.score)}`}>
                            {typeof factor.score === 'number' ? Math.round(factor.score) : 50}
                          </div>
                        </div>
                        <p className={`text-sm ${isLive ? 'text-surface-400' : 'text-surface-500'}`}>
                          {typeof factor.details === 'string' ? factor.details : 'Analysis pending'}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Score Legend */}
              <div className="flex items-center justify-center gap-6 text-xs text-surface-500">
                <span><span className="inline-block w-3 h-3 rounded bg-green-500/20 mr-1"></span> 65+ Favorable</span>
                <span><span className="inline-block w-3 h-3 rounded bg-yellow-500/20 mr-1"></span> 55-64 Neutral</span>
                <span><span className="inline-block w-3 h-3 rounded bg-orange-500/20 mr-1"></span> 45-54 Caution</span>
                <span><span className="inline-block w-3 h-3 rounded bg-red-500/20 mr-1"></span> &lt;45 Unfavorable</span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-surface-700">
          <Button
            variant="secondary"
            onClick={onClose}
            className="flex-1"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={() => analysis && onProceedToLog()}
            className="flex-1"
            disabled={isLoading || !analysis || !analysis.meets_threshold}
          >
            <TrendingUp className="w-4 h-4" />
            {analysis && !analysis.meets_threshold
              ? 'Insufficient Data'
              : 'Log Pick'
            }
          </Button>
        </div>
      </div>
    </div>
  );
}
