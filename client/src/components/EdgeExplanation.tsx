import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  X,
  TrendingUp,
  TrendingDown,
  Star,
  Info,
  Zap,
  Target,
  ArrowLeftRight,
  Moon,
  Cloud,
  User,
  Users,
  MessageCircle,
  BarChart3
} from 'lucide-react';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface FactorBreakdown {
  factor: string;
  edge: number;
  direction: string;
  signal: string;
  weight: string;
  contribution: string;
}

interface ExplanationData {
  game_id: number;
  game: string;
  sport: string;
  predicted_side: string;
  total_edge: string;
  confidence: number;
  confidence_label: string;
  recommendation: string;
  star_rating: number;
  factor_breakdown: FactorBreakdown[];
  analysis: {
    confirming_factors: number;
    conflicting_factors: number;
    alignment_score: number;
  };
  explanation: string;
  methodology: {
    description: string;
    weights: Record<string, string>;
  };
}

interface EdgeExplanationProps {
  gameId: number;
  isOpen: boolean;
  onClose: () => void;
}

const FACTOR_ICONS: Record<string, typeof TrendingUp> = {
  'Line Movement': ArrowLeftRight,
  'Coach Dna': User,
  'Situational': Moon,
  'Weather': Cloud,
  'Officials': Users,
  'Public Fade': TrendingDown,
  'Historical Elo': BarChart3,
  'Social Sentiment': MessageCircle,
};

export default function EdgeExplanation({ gameId, isOpen, onClose }: EdgeExplanationProps) {
  const [data, setData] = useState<ExplanationData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && gameId) {
      fetchExplanation();
    }
  }, [isOpen, gameId]);

  const fetchExplanation = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/predictions/explain/${gameId}`);
      if (!response.ok) throw new Error('Failed to fetch');
      const jsonData = await response.json();
      setData(jsonData);
    } catch (err) {
      console.error('Failed to fetch explanation:', err);
      setError('Unable to load explanation');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative min-h-screen flex items-center justify-center p-4">
        <div className="relative w-full max-w-2xl bg-white dark:bg-surface-900 rounded-2xl shadow-2xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between p-5 border-b border-surface-200 dark:border-surface-700">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-primary-100 dark:bg-primary-500/20 text-primary-600 dark:text-primary-400">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-surface-900 dark:text-white">
                  Edge Breakdown
                </h2>
                {data && (
                  <p className="text-sm text-surface-500 dark:text-surface-400">
                    {data.game}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-surface-500 hover:text-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-5 max-h-[70vh] overflow-y-auto">
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" text="Analyzing factors..." />
              </div>
            )}

            {error && (
              <div className="text-center py-12">
                <p className="text-danger-500 mb-4">{error}</p>
                <Button variant="outline" onClick={fetchExplanation}>
                  Try Again
                </Button>
              </div>
            )}

            {data && (
              <div className="space-y-6">
                {/* Prediction Summary */}
                <div className="p-4 bg-gradient-to-r from-primary-50 to-success-50 dark:from-primary-500/10 dark:to-success-500/10 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <Badge variant="primary">{data.sport}</Badge>
                    </div>
                    <div className="flex items-center gap-0.5">
                      {Array(5).fill(0).map((_, i) => (
                        <Star
                          key={i}
                          className={clsx(
                            'w-4 h-4',
                            i < data.star_rating
                              ? 'fill-warning-400 text-warning-400'
                              : 'text-surface-300 dark:text-surface-600'
                          )}
                        />
                      ))}
                    </div>
                  </div>
                  <h3 className="text-xl font-bold text-surface-900 dark:text-white mb-1">
                    {data.predicted_side}
                  </h3>
                  <div className="flex items-center gap-4 mt-2">
                    <div>
                      <span className="text-sm text-surface-500 dark:text-surface-400">Edge: </span>
                      <span className="font-bold text-success-600 dark:text-success-400">{data.total_edge}</span>
                    </div>
                    <div>
                      <span className="text-sm text-surface-500 dark:text-surface-400">Confidence: </span>
                      <span className="font-bold text-surface-900 dark:text-white">
                        {Math.round(data.confidence * 100)}%
                      </span>
                    </div>
                    <div>
                      <span className={clsx(
                        'px-2 py-1 rounded-full text-xs font-bold',
                        data.recommendation === 'STRONG BET' ? 'bg-success-500 text-white' :
                        data.recommendation === 'BET' ? 'bg-success-400 text-white' :
                        data.recommendation === 'LEAN' ? 'bg-primary-500 text-white' :
                        'bg-surface-400 text-white'
                      )}>
                        {data.recommendation}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Explanation */}
                <div className="flex items-start gap-3 p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
                  <Info className="w-5 h-5 text-primary-500 mt-0.5 shrink-0" />
                  <p className="text-sm text-surface-600 dark:text-surface-400">
                    {data.explanation}
                  </p>
                </div>

                {/* Factor Breakdown */}
                <div>
                  <h4 className="text-sm font-semibold text-surface-900 dark:text-white mb-3 flex items-center gap-2">
                    <BarChart3 className="w-4 h-4" />
                    Factor Analysis
                    <span className="font-normal text-surface-500">
                      ({data.analysis.confirming_factors} confirming, {data.analysis.conflicting_factors} conflicting)
                    </span>
                  </h4>

                  <div className="space-y-2">
                    {data.factor_breakdown.map((factor) => {
                      const Icon = FACTOR_ICONS[factor.factor] || TrendingUp;

                      return (
                        <div
                          key={factor.factor}
                          className="flex items-center gap-3 p-3 bg-white dark:bg-surface-800 rounded-lg border border-surface-200 dark:border-surface-700"
                        >
                          <div className={clsx(
                            'p-2 rounded-lg',
                            factor.edge > 2 ? 'bg-success-100 dark:bg-success-500/20 text-success-600 dark:text-success-400' :
                            factor.edge > 0.5 ? 'bg-primary-100 dark:bg-primary-500/20 text-primary-600 dark:text-primary-400' :
                            'bg-surface-100 dark:bg-surface-700 text-surface-500'
                          )}>
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-surface-900 dark:text-white text-sm">
                                {factor.factor}
                              </span>
                              <span className="text-xs text-surface-500">
                                {factor.weight}
                              </span>
                            </div>
                            <p className="text-xs text-surface-500 dark:text-surface-400 truncate">
                              {factor.signal}
                            </p>
                          </div>
                          <div className="text-right shrink-0">
                            <Badge
                              variant={
                                factor.direction === 'home' || factor.direction === 'over' ? 'success' :
                                factor.direction === 'away' || factor.direction === 'under' ? 'danger' :
                                'neutral'
                              }
                              className="text-xs mb-1"
                            >
                              {factor.direction}
                            </Badge>
                            <p className={clsx(
                              'text-sm font-bold',
                              factor.edge > 2 ? 'text-success-600 dark:text-success-400' :
                              factor.edge > 0.5 ? 'text-primary-600 dark:text-primary-400' :
                              'text-surface-500'
                            )}>
                              +{factor.edge.toFixed(1)}%
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Alignment Score */}
                <div className="p-4 bg-surface-50 dark:bg-surface-800/50 rounded-xl">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                      Signal Alignment
                    </span>
                    <span className="text-sm font-bold text-surface-900 dark:text-white">
                      {Math.round(data.analysis.alignment_score * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-3 bg-surface-200 dark:bg-surface-700 rounded-full overflow-hidden">
                    <div
                      className={clsx(
                        'h-full rounded-full transition-all',
                        data.analysis.alignment_score >= 0.7 ? 'bg-success-500' :
                        data.analysis.alignment_score >= 0.5 ? 'bg-warning-500' :
                        'bg-danger-500'
                      )}
                      style={{ width: `${data.analysis.alignment_score * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-surface-500 dark:text-surface-400 mt-2">
                    Higher alignment = more factors agreeing on direction
                  </p>
                </div>

                {/* Methodology */}
                <div className="border-t border-surface-200 dark:border-surface-700 pt-4">
                  <h4 className="text-xs font-semibold text-surface-500 dark:text-surface-400 uppercase tracking-wider mb-3">
                    Methodology
                  </h4>
                  <p className="text-sm text-surface-600 dark:text-surface-400 mb-3">
                    {data.methodology.description}
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(data.methodology.weights).map(([factor, weight]) => (
                      <div
                        key={factor}
                        className="text-xs text-surface-500 dark:text-surface-400"
                      >
                        <span className="font-medium">{factor.replace(/_/g, ' ')}:</span> {weight.split(' - ')[0]}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-5 border-t border-surface-200 dark:border-surface-700 bg-surface-50 dark:bg-surface-800/50">
            <div className="flex items-center justify-end gap-3">
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
              {data && (
                <Button onClick={() => {/* Track bet logic */}}>
                  <Target className="w-4 h-4" />
                  Track This Bet
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
