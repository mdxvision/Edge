import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { Card, Badge, Button } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import ErrorMessage from '@/components/ui/ErrorMessage';
import api from '@/lib/api';
import {
  ArrowLeft,
  Clock,
  MapPin,
  Cloud,
  TrendingUp,
  TrendingDown,
  Target,
  History,
  BarChart3,
  Thermometer,
  Wind,
  Droplets,
  AlertTriangle,
  DollarSign,
  Percent,
  Activity
} from 'lucide-react';

interface GameData {
  id: string;
  sport: string;
  home_team: string;
  away_team: string;
  start_time: string;
  venue?: string;
  league?: string;
}

interface OddsData {
  moneyline_home: number;
  moneyline_away: number;
  spread_home: number;
  spread_away: number;
  total: number;
  over_odds: number;
  under_odds: number;
}

interface WeatherData {
  temperature: number;
  wind_speed: number;
  precipitation_chance: number;
  conditions: string;
  impact_score: number;
  recommendation?: string;
}

interface FactorData {
  name: string;
  score: number;
  description: string;
  direction: 'home' | 'away' | 'neutral';
}

export default function GameDetail() {
  const { gameId } = useParams<{ gameId: string }>();
  const [searchParams] = useSearchParams();
  const sport = searchParams.get('sport') || 'NFL';
  const navigate = useNavigate();

  const [game, setGame] = useState<GameData | null>(null);
  const [odds, setOdds] = useState<OddsData | null>(null);
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [factors, setFactors] = useState<FactorData[]>([]);
  const [prediction, setPrediction] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGameData = async () => {
      if (!gameId) return;
      setIsLoading(true);
      setError(null);

      try {
        // Fetch game details based on sport
        let gameData: GameData | null = null;

        // Try to get game from appropriate API
        if (sport === 'NFL') {
          const nflData = await api.nfl.getGames();
          const found = nflData?.games?.find((g: any) => g.id === gameId || g.game_id === gameId);
          if (found) {
            gameData = {
              id: found.id || found.game_id,
              sport: 'NFL',
              home_team: found.home_team?.name || 'Home Team',
              away_team: found.away_team?.name || 'Away Team',
              start_time: found.game_date || found.date,
              venue: found.venue?.name,
              league: 'NFL'
            };
          }
        } else if (sport === 'NBA') {
          const nbaData = await api.nba.getTodaysGames();
          const found = nbaData?.games?.find((g: any) => g.game_id === gameId);
          if (found) {
            gameData = {
              id: found.game_id,
              sport: 'NBA',
              home_team: found.home_team?.name || 'Home Team',
              away_team: found.away_team?.name || 'Away Team',
              start_time: found.game_date || found.date,
              venue: found.arena,
              league: 'NBA'
            };
          }
        }

        // If no specific game found, create placeholder
        if (!gameData) {
          gameData = {
            id: gameId,
            sport: sport,
            home_team: 'Home Team',
            away_team: 'Away Team',
            start_time: new Date().toISOString(),
            league: sport
          };
        }

        setGame(gameData);

        // Set sample odds (API integration can be added later)
        setOdds({
          moneyline_home: -150,
          moneyline_away: 130,
          spread_home: -3.5,
          spread_away: 3.5,
          total: 47.5,
          over_odds: -110,
          under_odds: -110
        });

        // Set weather for outdoor sports
        if (['NFL', 'MLB', 'CFB'].includes(sport)) {
          setWeather({
            temperature: 45,
            wind_speed: 12,
            precipitation_chance: 20,
            conditions: 'Partly Cloudy',
            impact_score: 0.15,
            recommendation: 'Slight under lean due to wind'
          });
        }

        // Set betting factors
        setFactors([
          { name: 'Line Movement', score: 72, description: 'Sharp money on home team', direction: 'home' },
          { name: 'Situational', score: 65, description: 'Home team on extra rest', direction: 'home' },
          { name: 'Public Fade', score: 58, description: '68% public on away', direction: 'home' },
          { name: 'Weather', score: 55, description: 'Wind favors under', direction: 'neutral' },
          { name: 'H2H History', score: 60, description: 'Home 4-1 ATS last 5', direction: 'home' },
        ]);

        // Set prediction
        setPrediction({
          home_win_prob: 0.58,
          predicted_spread: -4.2,
          predicted_total: 46.8,
          edge: 0.042,
          confidence: 0.72,
          recommendation: 'Home -3.5'
        });

      } catch (err) {
        console.error('Failed to fetch game data:', err);
        setError('Could not load game details');
      } finally {
        setIsLoading(false);
      }
    };

    fetchGameData();
  }, [gameId, sport]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner size="lg" text="Loading game..." />
      </div>
    );
  }

  if (error || !game) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <ErrorMessage
          message={error || 'Game not found'}
          variant="fullpage"
          onRetry={() => navigate(-1)}
        />
      </div>
    );
  }

  const formatOdds = (odds: number) => {
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </Button>
      </div>

      {/* Game Header Card */}
      <Card padding="lg">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-4">
              <Badge variant="primary" size="md">{game.sport}</Badge>
              {game.league && <Badge variant="neutral">{game.league}</Badge>}
            </div>
            <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 dark:text-white">
              {game.away_team} @ {game.home_team}
            </h1>
            <div className="flex flex-wrap items-center gap-4 mt-3 text-gray-600 dark:text-slate-400">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>
                  {new Date(game.start_time).toLocaleDateString(undefined, {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric'
                  })} at {new Date(game.start_time).toLocaleTimeString(undefined, {
                    hour: 'numeric',
                    minute: '2-digit'
                  })}
                </span>
              </div>
              {game.venue && (
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  <span>{game.venue}</span>
                </div>
              )}
            </div>
          </div>

          {/* Quick Prediction */}
          {prediction && (
            <div className="bg-emerald-50 dark:bg-emerald-500/10 rounded-xl p-4 lg:p-6 text-center lg:text-right">
              <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300 mb-1">
                Model Pick
              </p>
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {prediction.recommendation}
              </p>
              <p className="text-sm text-emerald-600 dark:text-emerald-400 mt-1">
                {(prediction.confidence * 100).toFixed(0)}% confidence · +{(prediction.edge * 100).toFixed(1)}% edge
              </p>
            </div>
          )}
        </div>
      </Card>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Odds */}
        <div className="lg:col-span-2 space-y-6">
          {/* Current Odds */}
          <Card padding="none">
            <div className="p-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-emerald-500" />
                Current Odds
              </h2>
            </div>
            {odds && (
              <div className="p-4">
                <div className="grid grid-cols-3 gap-4">
                  {/* Moneyline */}
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-2">Moneyline</p>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">{game.away_team.split(' ').pop()}</span>
                        <span className="font-bold text-gray-900 dark:text-white">{formatOdds(odds.moneyline_away)}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">{game.home_team.split(' ').pop()}</span>
                        <span className="font-bold text-gray-900 dark:text-white">{formatOdds(odds.moneyline_home)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Spread */}
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-2">Spread</p>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">{game.away_team.split(' ').pop()}</span>
                        <span className="font-bold text-gray-900 dark:text-white">{odds.spread_away > 0 ? '+' : ''}{odds.spread_away}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">{game.home_team.split(' ').pop()}</span>
                        <span className="font-bold text-gray-900 dark:text-white">{odds.spread_home > 0 ? '+' : ''}{odds.spread_home}</span>
                      </div>
                    </div>
                  </div>

                  {/* Total */}
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm font-medium text-gray-600 dark:text-slate-400 mb-2">Total</p>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">Over</span>
                        <span className="font-bold text-gray-900 dark:text-white">{odds.total} ({formatOdds(odds.over_odds)})</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600 dark:text-slate-400">Under</span>
                        <span className="font-bold text-gray-900 dark:text-white">{odds.total} ({formatOdds(odds.under_odds)})</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Betting Factors */}
          <Card padding="none">
            <div className="p-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-500" />
                Edge Factors
              </h2>
            </div>
            <div className="divide-y divide-gray-100 dark:divide-slate-700">
              {factors.map((factor, idx) => (
                <div key={idx} className="p-4 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-white">{factor.name}</span>
                      {factor.direction === 'home' && (
                        <TrendingUp className="w-4 h-4 text-emerald-500" />
                      )}
                      {factor.direction === 'away' && (
                        <TrendingDown className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                    <p className="text-sm text-gray-600 dark:text-slate-400 mt-0.5">{factor.description}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-24 h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          factor.score >= 70 ? 'bg-emerald-500' :
                          factor.score >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${factor.score}%` }}
                      />
                    </div>
                    <span className="font-bold text-gray-900 dark:text-white w-8 text-right">{factor.score}</span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {/* Model Prediction */}
          {prediction && (
            <Card padding="none">
              <div className="p-4 border-b border-gray-200 dark:border-slate-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Activity className="w-5 h-5 text-emerald-500" />
                  Model Prediction
                </h2>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm text-gray-600 dark:text-slate-400 mb-1">Win Probability</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {(prediction.home_win_prob * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-500">{game.home_team.split(' ').pop()}</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm text-gray-600 dark:text-slate-400 mb-1">Predicted Spread</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {prediction.predicted_spread > 0 ? '+' : ''}{prediction.predicted_spread.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 dark:bg-slate-800 rounded-lg">
                    <p className="text-sm text-gray-600 dark:text-slate-400 mb-1">Predicted Total</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {prediction.predicted_total.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg">
                    <p className="text-sm text-emerald-600 dark:text-emerald-400 mb-1">Edge</p>
                    <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                      +{(prediction.edge * 100).toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Right Column - Weather & Quick Stats */}
        <div className="space-y-6">
          {/* Weather Card */}
          {weather && (
            <Card padding="none">
              <div className="p-4 border-b border-gray-200 dark:border-slate-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Cloud className="w-5 h-5 text-blue-500" />
                  Weather Impact
                </h2>
              </div>
              <div className="p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Thermometer className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600 dark:text-slate-400">Temperature</span>
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">{weather.temperature}°F</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Wind className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600 dark:text-slate-400">Wind</span>
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">{weather.wind_speed} mph</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Droplets className="w-4 h-4 text-gray-500" />
                    <span className="text-gray-600 dark:text-slate-400">Precipitation</span>
                  </div>
                  <span className="font-medium text-gray-900 dark:text-white">{weather.precipitation_chance}%</span>
                </div>
                <div className="pt-3 border-t border-gray-200 dark:border-slate-700">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-600 dark:text-slate-400">Impact Score</span>
                    <span className={`font-bold ${
                      weather.impact_score > 0.3 ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'
                    }`}>
                      {(weather.impact_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {weather.recommendation && (
                    <p className="text-sm text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-800 p-2 rounded">
                      {weather.recommendation}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* Quick Actions */}
          <Card padding="md">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <Button variant="primary" className="w-full justify-center">
                <Target className="w-4 h-4 mr-2" />
                Add to Tracker
              </Button>
              <Button variant="secondary" className="w-full justify-center">
                <Percent className="w-4 h-4 mr-2" />
                Calculate Bet Size
              </Button>
              <Button variant="ghost" className="w-full justify-center">
                <History className="w-4 h-4 mr-2" />
                View H2H History
              </Button>
            </div>
          </Card>

          {/* Disclaimer */}
          <div className="p-4 bg-amber-50 dark:bg-amber-500/10 rounded-lg border border-amber-200 dark:border-amber-500/20">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-amber-800 dark:text-amber-300">Simulation Only</p>
                <p className="text-xs text-amber-700 dark:text-amber-400 mt-1">
                  For educational purposes. Not financial advice.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
