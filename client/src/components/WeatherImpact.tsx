import { useState, useEffect } from 'react';
import { Card, Badge } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import api from '@/lib/api';
import {
  Sun,
  Cloud,
  CloudRain,
  CloudSnow,
  Wind,
  Thermometer,
  Droplets,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
} from 'lucide-react';

interface WeatherData {
  temperature_f: number;
  humidity: number;
  wind_speed_mph: number;
  wind_direction: string;
  conditions: string;
  precipitation_in?: number;
  snowfall_in?: number;
  weather_type?: string;
}

interface WeatherImpactData {
  total_adjustment: number;
  recommendation: string;
  confidence: number;
  factors: string[];
  hr_factor?: number;
  scoring_factor?: number;
  pass_yards_factor?: number;
  rush_yards_factor?: number;
  turnover_factor?: number;
  goals_factor?: number;
}

interface WeatherImpactResponse {
  sport: string;
  venue: string;
  team?: string;
  game_time?: string;
  kickoff?: string;
  dome_type: string;
  weather: WeatherData;
  impact: WeatherImpactData;
  summary: string;
}

interface WeatherImpactProps {
  sport: 'mlb' | 'nfl' | 'cfb' | 'soccer';
  venue: string;
  gameDate?: string;
  gameHour?: number;
  compact?: boolean;
}

const getWeatherIcon = (conditions: string) => {
  const lower = conditions.toLowerCase();
  if (lower.includes('snow')) return <CloudSnow className="w-6 h-6 text-blue-300" />;
  if (lower.includes('rain') || lower.includes('drizzle')) return <CloudRain className="w-6 h-6 text-blue-400" />;
  if (lower.includes('cloud') || lower.includes('overcast')) return <Cloud className="w-6 h-6 text-gray-400" />;
  return <Sun className="w-6 h-6 text-yellow-400" />;
};

const getRecommendationBadge = (recommendation: string, confidence: number) => {
  const confPercent = Math.round(confidence * 100);

  switch (recommendation) {
    case 'OVER':
      return (
        <Badge variant="success" className="flex items-center gap-1">
          <TrendingUp className="w-3 h-3" />
          OVER ({confPercent}%)
        </Badge>
      );
    case 'LEAN_OVER':
      return (
        <Badge variant="success" className="flex items-center gap-1 opacity-80">
          <TrendingUp className="w-3 h-3" />
          Lean Over
        </Badge>
      );
    case 'UNDER':
      return (
        <Badge variant="danger" className="flex items-center gap-1">
          <TrendingDown className="w-3 h-3" />
          UNDER ({confPercent}%)
        </Badge>
      );
    case 'LEAN_UNDER':
      return (
        <Badge variant="danger" className="flex items-center gap-1 opacity-80">
          <TrendingDown className="w-3 h-3" />
          Lean Under
        </Badge>
      );
    default:
      return (
        <Badge variant="neutral" className="flex items-center gap-1">
          <Minus className="w-3 h-3" />
          Neutral
        </Badge>
      );
  }
};

export default function WeatherImpact({
  sport,
  venue,
  gameDate,
  gameHour = 19,
  compact = false,
}: WeatherImpactProps) {
  const [data, setData] = useState<WeatherImpactResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchWeatherImpact = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await api.weather.getImpact(sport, venue, gameDate, gameHour);
        setData(response);
      } catch (err) {
        console.error('Failed to fetch weather impact:', err);
        setError('Unable to load weather data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchWeatherImpact();
  }, [sport, venue, gameDate, gameHour]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <LoadingSpinner size="sm" />
      </div>
    );
  }

  if (error || !data) {
    return null; // Silently fail for weather
  }

  // Dome venue - no impact
  if (data.dome_type === 'dome') {
    if (compact) return null;
    return (
      <div className="flex items-center gap-2 text-sm text-surface-500">
        <span>Dome game - no weather impact</span>
      </div>
    );
  }

  const { weather, impact } = data;
  const hasSignificantImpact = Math.abs(impact.total_adjustment) >= 0.75;

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          {getWeatherIcon(weather.conditions)}
          <span className="text-sm font-medium">{Math.round(weather.temperature_f)}°F</span>
        </div>
        {weather.wind_speed_mph > 10 && (
          <div className="flex items-center gap-1 text-sm text-surface-500">
            <Wind className="w-4 h-4" />
            <span>{Math.round(weather.wind_speed_mph)} mph</span>
          </div>
        )}
        {hasSignificantImpact && getRecommendationBadge(impact.recommendation, impact.confidence)}
      </div>
    );
  }

  return (
    <Card padding="md" className="bg-gradient-to-br from-surface-50 to-surface-100 dark:from-surface-800 dark:to-surface-900">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-surface-900 dark:text-white flex items-center gap-2">
            {getWeatherIcon(weather.conditions)}
            Weather Impact
          </h3>
          {getRecommendationBadge(impact.recommendation, impact.confidence)}
        </div>

        {/* Weather Conditions */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="flex items-center gap-2">
            <Thermometer className="w-5 h-5 text-red-400" />
            <div>
              <p className="text-xs text-surface-500">Temp</p>
              <p className="font-semibold text-surface-900 dark:text-white">
                {Math.round(weather.temperature_f)}°F
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Wind className="w-5 h-5 text-blue-400" />
            <div>
              <p className="text-xs text-surface-500">Wind</p>
              <p className="font-semibold text-surface-900 dark:text-white">
                {Math.round(weather.wind_speed_mph)} mph {weather.wind_direction}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Droplets className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-xs text-surface-500">Humidity</p>
              <p className="font-semibold text-surface-900 dark:text-white">
                {weather.humidity}%
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Cloud className="w-5 h-5 text-gray-400" />
            <div>
              <p className="text-xs text-surface-500">Conditions</p>
              <p className="font-semibold text-surface-900 dark:text-white text-sm">
                {weather.conditions}
              </p>
            </div>
          </div>
        </div>

        {/* Impact Summary */}
        {hasSignificantImpact && (
          <div className="bg-white dark:bg-surface-800 rounded-lg p-3 border border-surface-200 dark:border-surface-700">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium text-surface-900 dark:text-white">
                Weather Edge Detected
              </span>
            </div>
            <p className="text-sm text-surface-600 dark:text-surface-400">
              {data.summary}
            </p>
          </div>
        )}

        {/* Impact Factors */}
        {impact.factors.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-surface-500 uppercase tracking-wide">
              Impact Factors
            </p>
            <ul className="space-y-1">
              {impact.factors.map((factor, idx) => (
                <li
                  key={idx}
                  className="text-sm text-surface-600 dark:text-surface-400 flex items-start gap-2"
                >
                  <span className="text-primary-500 mt-0.5">•</span>
                  {factor}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Adjustment Badge */}
        <div className="flex items-center justify-between pt-2 border-t border-surface-200 dark:border-surface-700">
          <span className="text-sm text-surface-500">
            Projected Adjustment
          </span>
          <span
            className={`text-lg font-bold ${
              impact.total_adjustment > 0
                ? 'text-green-500'
                : impact.total_adjustment < 0
                ? 'text-red-500'
                : 'text-surface-500'
            }`}
          >
            {impact.total_adjustment > 0 ? '+' : ''}
            {impact.total_adjustment.toFixed(1)} {sport === 'mlb' ? 'runs' : sport === 'soccer' ? 'goals' : 'pts'}
          </span>
        </div>
      </div>
    </Card>
  );
}

// Compact inline weather badge for game cards
export function WeatherBadge({
  temperature,
  conditions,
  windSpeed,
  recommendation,
}: {
  temperature: number;
  conditions: string;
  windSpeed: number;
  recommendation?: string;
}) {
  const hasWeatherImpact = recommendation && recommendation !== 'NEUTRAL';

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="flex items-center gap-1 text-surface-500 dark:text-surface-400">
        {getWeatherIcon(conditions)}
        <span>{Math.round(temperature)}°F</span>
        {windSpeed > 10 && (
          <>
            <Wind className="w-3 h-3 ml-1" />
            <span>{Math.round(windSpeed)}</span>
          </>
        )}
      </div>
      {hasWeatherImpact && (
        <span
          className={`px-1.5 py-0.5 rounded text-xs font-medium ${
            recommendation?.includes('OVER')
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
          }`}
        >
          {recommendation?.includes('LEAN') ? 'Lean ' : ''}
          {recommendation?.includes('OVER') ? 'O' : 'U'}
        </span>
      )}
    </div>
  );
}
