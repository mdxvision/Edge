import { useState, type ChangeEvent } from 'react';
import { Card, Button } from '@/components/ui';
import Input from '@/components/ui/Input';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import {
  Target,
  Plus,
  TrendingUp,
  DollarSign,
  Check,
  AlertCircle
} from 'lucide-react';

interface Game {
  id: string;
  home_team: string | { name: string };
  away_team: string | { name: string };
  game_time?: string;
  game_date?: string;
  odds?: {
    spread?: number;
    total?: number;
    moneyline_home?: number;
    moneyline_away?: number;
  };
}

interface FactorScore {
  score: number;
  detail: string;
}

interface PickLoggerProps {
  game?: Game;
  defaultSport?: string;
  onPickLogged?: () => void;
}

const DEFAULT_FACTORS: Record<string, FactorScore> = {
  coach_dna: { score: 50, detail: '' },
  referee: { score: 50, detail: '' },
  weather: { score: 50, detail: '' },
  line_movement: { score: 50, detail: '' },
  rest: { score: 50, detail: '' },
  travel: { score: 50, detail: '' },
  situational: { score: 50, detail: '' },
  public_betting: { score: 50, detail: '' }
};

const FACTOR_LABELS: Record<string, string> = {
  coach_dna: 'Coach DNA',
  referee: 'Referee',
  weather: 'Weather',
  line_movement: 'Line Movement',
  rest: 'Rest Days',
  travel: 'Travel',
  situational: 'Situational',
  public_betting: 'Public %'
};

export default function PickLogger({ game, defaultSport = 'NFL', onPickLogged }: PickLoggerProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [sport, setSport] = useState(defaultSport);
  const [homeTeam, setHomeTeam] = useState(
    typeof game?.home_team === 'string' ? game.home_team : game?.home_team?.name || ''
  );
  const [awayTeam, setAwayTeam] = useState(
    typeof game?.away_team === 'string' ? game.away_team : game?.away_team?.name || ''
  );
  const [gameTime] = useState(game?.game_time || game?.game_date || new Date().toISOString());
  const [pickType, setPickType] = useState<'spread' | 'moneyline' | 'total'>('spread');
  const [pick, setPick] = useState('');
  const [lineValue, setLineValue] = useState<number | ''>('');
  const [odds, setOdds] = useState(-110);
  const [confidence, setConfidence] = useState(70);
  const [factors, setFactors] = useState<Record<string, FactorScore>>(DEFAULT_FACTORS);
  const [showFactors, setShowFactors] = useState(false);

  const handleFactorChange = (factorName: string, score: number) => {
    setFactors(prev => ({
      ...prev,
      [factorName]: { ...prev[factorName], score }
    }));
  };

  const calculateRecommendedUnits = (): number => {
    if (confidence >= 90) return 3.0;
    if (confidence >= 80) return 2.0;
    if (confidence >= 70) return 1.5;
    if (confidence >= 60) return 1.0;
    return 0.5;
  };

  const handleSubmit = async () => {
    if (!homeTeam || !awayTeam || !pick) {
      setError('Please fill in all required fields');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await fetch('/api/tracker/picks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          game_id: game?.id || `manual_${Date.now()}`,
          sport: sport.toUpperCase(),
          home_team: homeTeam,
          away_team: awayTeam,
          game_time: gameTime,
          pick_type: pickType,
          pick,
          pick_team: pickType !== 'total' ? pick.split(' ')[0] : undefined,
          line_value: lineValue || undefined,
          odds,
          confidence,
          factors
        })
      });

      if (response.ok) {
        setSuccess(true);
        // Reset form
        setPick('');
        setLineValue('');
        setConfidence(70);
        setFactors(DEFAULT_FACTORS);

        setTimeout(() => {
          setSuccess(false);
          setIsExpanded(false);
        }, 2000);

        onPickLogged?.();
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to log pick');
      }
    } catch (err) {
      setError('Failed to log pick. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isExpanded) {
    return (
      <Button
        variant="outline"
        className="w-full border-dashed border-gray-600 hover:border-blue-500 hover:bg-blue-500/10"
        onClick={() => setIsExpanded(true)}
      >
        <Plus className="h-4 w-4 mr-2" />
        Log Pick
      </Button>
    );
  }

  return (
    <Card className="p-4 bg-gray-800/70 border-gray-700">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-blue-400" />
            <span className="font-semibold text-white">Log Pick</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(false)}
            className="text-gray-400 hover:text-white"
          >
            Cancel
          </Button>
        </div>

        {/* Sport & Teams */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Sport</label>
            <select
              value={sport}
              onChange={(e) => setSport(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="NFL">NFL</option>
              <option value="NBA">NBA</option>
              <option value="MLB">MLB</option>
              <option value="NHL">NHL</option>
              <option value="CBB">CBB</option>
              <option value="NCAAF">NCAAF</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Away Team</label>
            <Input
              value={awayTeam}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setAwayTeam(e.target.value)}
              placeholder="Away team"
              className="text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Home Team</label>
            <Input
              value={homeTeam}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setHomeTeam(e.target.value)}
              placeholder="Home team"
              className="text-sm"
            />
          </div>
        </div>

        {/* Pick Type & Pick */}
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Pick Type</label>
            <select
              value={pickType}
              onChange={(e) => setPickType(e.target.value as any)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="spread">Spread</option>
              <option value="moneyline">Moneyline</option>
              <option value="total">Total</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Pick</label>
            <Input
              value={pick}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setPick(e.target.value)}
              placeholder={
                pickType === 'spread' ? 'Chiefs -3' :
                pickType === 'total' ? 'Over 45.5' : 'Chiefs ML'
              }
              className="text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Line Value</label>
            <Input
              type="number"
              step="0.5"
              value={lineValue}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setLineValue(e.target.value ? parseFloat(e.target.value) : '')}
              placeholder="-3 or 45.5"
              className="text-sm"
            />
          </div>
        </div>

        {/* Odds & Confidence */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">American Odds</label>
            <Input
              type="number"
              value={odds}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setOdds(parseInt(e.target.value) || -110)}
              placeholder="-110"
              className="text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Confidence: {confidence}%
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={confidence}
              onChange={(e) => setConfidence(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
          </div>
        </div>

        {/* Recommended Units */}
        <div className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400">
            <DollarSign className="h-4 w-4" />
            <span className="text-sm">Recommended Units</span>
          </div>
          <span className="font-bold text-white">{calculateRecommendedUnits().toFixed(1)}u</span>
        </div>

        {/* Factor Scores (Collapsible) */}
        <div>
          <button
            onClick={() => setShowFactors(!showFactors)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <TrendingUp className="h-4 w-4" />
            <span>{showFactors ? 'Hide' : 'Show'} Factor Scores</span>
          </button>

          {showFactors && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              {Object.entries(factors).map(([key, factor]) => (
                <div key={key} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">{FACTOR_LABELS[key]}</span>
                    <span className={`font-medium ${
                      factor.score >= 70 ? 'text-green-400' :
                      factor.score >= 50 ? 'text-yellow-400' : 'text-red-400'
                    }`}>
                      {factor.score}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={factor.score}
                    onChange={(e) => handleFactorChange(key, parseInt(e.target.value))}
                    className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Error/Success Messages */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-900/30 text-red-400 rounded-lg text-sm">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}

        {success && (
          <div className="flex items-center gap-2 p-3 bg-green-900/30 text-green-400 rounded-lg text-sm">
            <Check className="h-4 w-4" />
            Pick logged successfully!
          </div>
        )}

        {/* Submit Button */}
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting || !pick}
          className="w-full"
        >
          {isSubmitting ? (
            <LoadingSpinner size="sm" />
          ) : (
            <>
              <Plus className="h-4 w-4 mr-2" />
              Log Pick ({calculateRecommendedUnits().toFixed(1)}u at {odds > 0 ? '+' : ''}{odds})
            </>
          )}
        </Button>
      </div>
    </Card>
  );
}
