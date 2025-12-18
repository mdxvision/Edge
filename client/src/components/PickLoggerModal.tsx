import { useState } from 'react';
import { X, Target, TrendingUp } from 'lucide-react';
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

interface PickLoggerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (pickKey: string) => void;
  pickData: PickData;
}

export default function PickLoggerModal({
  isOpen,
  onClose,
  onSuccess,
  pickData
}: PickLoggerModalProps) {
  const [confidence, setConfidence] = useState(70);
  const [units, setUnits] = useState(1.0);
  const [isLogging, setIsLogging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleLogPick = async () => {
    setIsLogging(true);
    setError(null);

    try {
      const response = await fetch('/tracker/picks', {
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
          odds: pickData.odds,
          confidence: confidence,
          units_wagered: units,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to log pick');
      }

      // Generate unique key for this pick
      const pickKey = `${pickData.game_id}_${pickData.pick_type}_${pickData.pick}`;

      // Show success toast
      showToast('Pick logged successfully!');

      // Notify parent of success
      onSuccess(pickKey);

      // Close modal
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to log pick');
    } finally {
      setIsLogging(false);
    }
  };

  const showToast = (message: string) => {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 z-50 animate-slide-up';
    toast.innerHTML = `
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
      </svg>
      <span>${message}</span>
    `;
    document.body.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  };

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  const getConfidenceColor = () => {
    if (confidence >= 80) return 'text-green-400';
    if (confidence >= 70) return 'text-yellow-400';
    return 'text-orange-400';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface-800 border border-surface-700 rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-surface-700">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-primary-500/10">
              <Target className="w-5 h-5 text-primary-400" />
            </div>
            <h2 className="text-lg font-semibold text-white">Log Pick</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-700 transition-colors"
          >
            <X className="w-5 h-5 text-surface-400" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5">
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
            <Badge variant="outline" className="text-xs">
              {pickData.pick_type.charAt(0).toUpperCase() + pickData.pick_type.slice(1)}
            </Badge>
          </div>

          {/* Confidence Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-surface-300">
                Confidence
              </label>
              <span className={`text-lg font-bold ${getConfidenceColor()}`}>
                {confidence}%
              </span>
            </div>
            <input
              type="range"
              min="50"
              max="100"
              value={confidence}
              onChange={(e) => setConfidence(Number(e.target.value))}
              className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <div className="flex justify-between text-xs text-surface-500">
              <span>50%</span>
              <span>75%</span>
              <span>100%</span>
            </div>
          </div>

          {/* Units Slider */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-surface-300">
                Units
              </label>
              <span className="text-lg font-bold text-white">
                {units.toFixed(1)}u
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="5"
              step="0.5"
              value={units}
              onChange={(e) => setUnits(Number(e.target.value))}
              className="w-full h-2 bg-surface-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <div className="flex justify-between text-xs text-surface-500">
              <span>0.5u</span>
              <span>2.5u</span>
              <span>5.0u</span>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-5 border-t border-surface-700">
          <Button
            variant="secondary"
            onClick={onClose}
            className="flex-1"
            disabled={isLogging}
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleLogPick}
            className="flex-1"
            isLoading={isLogging}
          >
            <TrendingUp className="w-4 h-4" />
            Log Pick
          </Button>
        </div>
      </div>
    </div>
  );
}
