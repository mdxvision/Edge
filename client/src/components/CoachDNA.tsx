import { useState } from 'react';
import { clsx } from 'clsx';
import { ChevronDown, ChevronUp, Brain, TrendingUp, TrendingDown, Target } from 'lucide-react';
import Badge from '@/components/ui/Badge';

interface ApplicableSituation {
  situation: string;
  record: string;
  win_pct: number;
  edge: string;  // Formatted string like "+10.5%"
  sample_size?: number;
}

interface CoachEdge {
  coach: {
    id: number;
    name: string;
    team: string | null;
    career_ats: string;
  };
  applicable_situations: ApplicableSituation[];
  combined_edge: string;
  combined_edge_value: number;
  confidence: number;
  recommendation: string;
}

interface CoachDNAProps {
  edge: CoachEdge;
  compact?: boolean;
  className?: string;
}

export default function CoachDNA({ edge, compact = false, className }: CoachDNAProps) {
  const [expanded, setExpanded] = useState(false);

  const edgeValue = edge.combined_edge_value;
  const isPositiveEdge = edgeValue >= 0;
  const isStrongEdge = Math.abs(edgeValue) >= 5;
  const confidencePercent = Math.round(edge.confidence * 100);

  // Determine edge color
  const getEdgeColor = () => {
    if (Math.abs(edgeValue) < 2) return 'neutral';
    if (edgeValue >= 5) return 'success';
    if (edgeValue >= 2) return 'primary';
    if (edgeValue <= -5) return 'danger';
    return 'warning';
  };

  const edgeColor = getEdgeColor();

  // Compact badge version for pick cards
  if (compact) {
    return (
      <button
        onClick={() => setExpanded(!expanded)}
        className={clsx(
          'group flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all',
          'bg-surface-50 dark:bg-surface-800/50',
          'hover:bg-surface-100 dark:hover:bg-surface-800',
          'border border-surface-200 dark:border-surface-700',
          className
        )}
      >
        <Brain className="w-4 h-4 text-primary-500" />
        <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
          Coach DNA:
        </span>
        <span className={clsx(
          'text-sm font-bold',
          edgeColor === 'success' && 'text-success-600 dark:text-success-400',
          edgeColor === 'danger' && 'text-danger-600 dark:text-danger-400',
          edgeColor === 'primary' && 'text-primary-600 dark:text-primary-400',
          edgeColor === 'warning' && 'text-warning-600 dark:text-warning-400',
          edgeColor === 'neutral' && 'text-surface-600 dark:text-surface-400'
        )}>
          {edge.combined_edge}
        </span>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-surface-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-surface-400" />
        )}
      </button>
    );
  }

  return (
    <div className={clsx(
      'rounded-xl border overflow-hidden transition-all',
      'bg-white dark:bg-surface-900',
      'border-surface-200 dark:border-surface-800',
      className
    )}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            'bg-primary-50 dark:bg-primary-500/10'
          )}>
            <Brain className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-surface-900 dark:text-white">
                {edge.coach.name}
              </span>
              {edge.coach.team && (
                <span className="text-sm text-surface-500 dark:text-surface-400">
                  {edge.coach.team}
                </span>
              )}
            </div>
            <p className="text-sm text-surface-500 dark:text-surface-400">
              Career ATS: {edge.coach.career_ats}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Edge Display */}
          <div className="text-right">
            <div className={clsx(
              'text-2xl font-bold',
              edgeColor === 'success' && 'text-success-600 dark:text-success-400',
              edgeColor === 'danger' && 'text-danger-600 dark:text-danger-400',
              edgeColor === 'primary' && 'text-primary-600 dark:text-primary-400',
              edgeColor === 'warning' && 'text-warning-600 dark:text-warning-400',
              edgeColor === 'neutral' && 'text-surface-600 dark:text-surface-400'
            )}>
              {edge.combined_edge}
            </div>
            <p className="text-xs text-surface-500 dark:text-surface-400">
              Combined Edge
            </p>
          </div>

          {expanded ? (
            <ChevronUp className="w-5 h-5 text-surface-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-surface-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-surface-200 dark:border-surface-800">
          {/* Confidence Meter */}
          <div className="pt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Confidence
              </span>
              <span className="text-sm font-bold text-surface-900 dark:text-white">
                {confidencePercent}%
              </span>
            </div>
            <div className="h-2 bg-surface-100 dark:bg-surface-800 rounded-full overflow-hidden">
              <div
                className={clsx(
                  'h-full rounded-full transition-all',
                  confidencePercent >= 70 && 'bg-success-500',
                  confidencePercent >= 50 && confidencePercent < 70 && 'bg-primary-500',
                  confidencePercent >= 30 && confidencePercent < 50 && 'bg-warning-500',
                  confidencePercent < 30 && 'bg-surface-400'
                )}
                style={{ width: `${confidencePercent}%` }}
              />
            </div>
          </div>

          {/* Recommendation */}
          <div className={clsx(
            'p-3 rounded-lg',
            isStrongEdge && isPositiveEdge && 'bg-success-50 dark:bg-success-500/10',
            isStrongEdge && !isPositiveEdge && 'bg-danger-50 dark:bg-danger-500/10',
            !isStrongEdge && 'bg-surface-50 dark:bg-surface-800/50'
          )}>
            <div className="flex items-center gap-2">
              <Target className={clsx(
                'w-4 h-4',
                isStrongEdge && isPositiveEdge && 'text-success-600 dark:text-success-400',
                isStrongEdge && !isPositiveEdge && 'text-danger-600 dark:text-danger-400',
                !isStrongEdge && 'text-surface-600 dark:text-surface-400'
              )} />
              <span className={clsx(
                'font-semibold',
                isStrongEdge && isPositiveEdge && 'text-success-700 dark:text-success-300',
                isStrongEdge && !isPositiveEdge && 'text-danger-700 dark:text-danger-300',
                !isStrongEdge && 'text-surface-700 dark:text-surface-300'
              )}>
                {edge.recommendation}
              </span>
            </div>
          </div>

          {/* Applicable Situations */}
          {edge.applicable_situations.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-surface-700 dark:text-surface-300 mb-3">
                The Edge - Situational Breakdown
              </h4>
              <div className="space-y-2">
                {edge.applicable_situations.map((situation, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-2 rounded-lg bg-surface-50 dark:bg-surface-800/50"
                  >
                    <div className="flex items-center gap-2">
                      {situation.edge.startsWith('+') ? (
                        <TrendingUp className="w-4 h-4 text-success-500" />
                      ) : situation.edge.startsWith('-') ? (
                        <TrendingDown className="w-4 h-4 text-danger-500" />
                      ) : (
                        <div className="w-4 h-4" />
                      )}
                      <span className="text-sm font-medium text-surface-900 dark:text-white">
                        {situation.situation}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-surface-500 dark:text-surface-400">
                        {situation.record}
                      </span>
                      <Badge
                        variant={
                          situation.win_pct >= 55 ? 'success' :
                          situation.win_pct >= 50 ? 'primary' :
                          situation.win_pct >= 45 ? 'warning' : 'danger'
                        }
                        size="sm"
                      >
                        {situation.edge}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Compact badge component for inline use
export function CoachDNABadge({
  edge,
  onClick,
  className
}: {
  edge: number;
  onClick?: () => void;
  className?: string;
}) {
  const isPositive = edge >= 0;
  const isStrong = Math.abs(edge) >= 5;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-colors',
        isStrong && isPositive && 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-400',
        isStrong && !isPositive && 'bg-danger-50 text-danger-700 dark:bg-danger-500/15 dark:text-danger-400',
        !isStrong && isPositive && 'bg-primary-50 text-primary-700 dark:bg-primary-500/15 dark:text-primary-400',
        !isStrong && !isPositive && 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-400',
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
    >
      <Brain className="w-3 h-3" />
      <span>Coach DNA: {edge >= 0 ? '+' : ''}{edge.toFixed(1)}%</span>
    </button>
  );
}
