import { useEffect, useState, useCallback } from 'react';
import { Card, Badge, Button } from '@/components/ui';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import EmptyState from '@/components/ui/EmptyState';
import ErrorMessage from '@/components/ui/ErrorMessage';
import WeatherImpact from '@/components/WeatherImpact';
import H2HBadge from '@/components/H2HBadge';
import PickLoggerModal from '@/components/PickLoggerModal';
import api from '@/lib/api';
import {
  Trophy,
  Clock,
  MapPin,
  RefreshCw,
  Circle,
  Tv,
  TrendingUp,
  ArrowLeftRight,
  Moon,
  Plane,
  Check
} from 'lucide-react';

// Sport tab types
type SportTab = 'mlb' | 'nba' | 'nfl' | 'cbb' | 'soccer';

interface MLBGame {
  id: number;
  game_pk: number;
  status: string;
  game_date: string;
  game_time_display?: string;
  venue: string;
  away_team: {
    name: string;
    score: number | null;
    hits: number | null;
    errors: number | null;
  };
  home_team: {
    name: string;
    score: number | null;
    hits: number | null;
    errors: number | null;
  };
  weather?: string;
  inning?: number;
  inning_state?: string;
}

interface NBAGame {
  game_id: string;
  game_date: string;
  game_status: string;
  game_time_display?: string;
  arena: string;
  national_tv?: string;
  home_team: {
    id: number;
    name: string;
    score?: number | null;
  };
  away_team: {
    id: number;
    name: string;
    score?: number | null;
  };
  odds?: {
    spread: number | null;
    spread_odds: number | null;
    moneyline_home: number | null;
    moneyline_away: number | null;
    total: number | null;
    over_odds: number | null;
    under_odds: number | null;
  };
}

interface NFLGame {
  id: number;
  espn_id: string;
  status: string;
  game_date: string;
  game_time_display?: string;
  venue: string;
  week?: number;
  home_team: {
    name: string;
    score: number | null;
    record?: string;
  };
  away_team: {
    name: string;
    score: number | null;
    record?: string;
  };
  quarter?: number;
  time_remaining?: string;
  odds?: {
    spread: number | null;
    over_under: number | null;
  };
  broadcast?: string;
}

interface CBBGame {
  game_id?: string;
  espn_id?: string;
  id?: number;
  date?: string;
  game_date?: string;
  game_time_display?: string;
  name?: string;
  short_name?: string;
  status: string;
  status_detail?: string;
  venue?: string;
  broadcast?: string;
  home_team: {
    id?: string;
    name: string;
    abbreviation?: string;
    score?: number;
    rank?: number;
    record?: string;
  };
  away_team: {
    id?: string;
    name: string;
    abbreviation?: string;
    score?: number;
    rank?: number;
    record?: string;
  };
}

interface SoccerMatch {
  id: number;
  competition: string;
  matchday: number;
  status: string;
  match_date: string;
  game_time_display?: string;
  venue?: string;
  home_team: {
    name: string;
    score: number | null;
  };
  away_team: {
    name: string;
    score: number | null;
  };
}

const SPORT_CONFIG = {
  mlb: { name: 'MLB', icon: '⚾', color: 'bg-red-500' },
  nba: { name: 'NBA', icon: '🏀', color: 'bg-orange-500' },
  nfl: { name: 'NFL', icon: '🏈', color: 'bg-green-600' },
  cbb: { name: 'College Basketball', icon: '🏀', color: 'bg-blue-500' },
  soccer: { name: 'Soccer', icon: '⚽', color: 'bg-emerald-500' },
};

export default function Games() {
  const [activeTab, setActiveTab] = useState<SportTab>('nfl');
  const [mlbGames, setMlbGames] = useState<MLBGame[]>([]);
  const [nbaGames, setNbaGames] = useState<NBAGame[]>([]);
  const [nflGames, setNflGames] = useState<NFLGame[]>([]);
  const [cbbGames, setCbbGames] = useState<CBBGame[]>([]);
  const [soccerMatches, setSoccerMatches] = useState<SoccerMatch[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pick logger modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedPick, setSelectedPick] = useState<{
    sport: string;
    home_team: string;
    away_team: string;
    pick: string;
    pick_type: 'spread' | 'moneyline' | 'total';
    line_value?: number;
    odds: number;
    game_time: string;
    game_id: string;
  } | null>(null);
  const [loggedPicks, setLoggedPicks] = useState<Set<string>>(new Set());

  // Fetch logged picks on mount
  const fetchLoggedPicks = useCallback(async () => {
    try {
      const response = await fetch('/tracker/picks');
      if (response.ok) {
        const data = await response.json();
        const picks = data.picks || [];
        const loggedKeys = new Set<string>();
        picks.forEach((pick: { game_id: string; pick_type: string; pick: string }) => {
          const key = `${pick.game_id}_${pick.pick_type}_${pick.pick}`;
          loggedKeys.add(key);
        });
        setLoggedPicks(loggedKeys);
      }
    } catch (err) {
      console.error('Failed to fetch logged picks:', err);
    }
  }, []);

  useEffect(() => {
    fetchLoggedPicks();
  }, [fetchLoggedPicks]);

  const handlePickClick = (pickData: typeof selectedPick) => {
    if (!pickData) return;
    const pickKey = `${pickData.game_id}_${pickData.pick_type}_${pickData.pick}`;
    if (loggedPicks.has(pickKey)) return; // Already logged
    setSelectedPick(pickData);
    setIsModalOpen(true);
  };

  const handlePickLogged = (pickKey: string) => {
    setLoggedPicks(prev => new Set([...prev, pickKey]));
  };

  const isPickLogged = (gameId: string, pickType: string, pick: string) => {
    const key = `${gameId}_${pickType}_${pick}`;
    return loggedPicks.has(key);
  };

  const formatOdds = (odds: number | null | undefined) => {
    if (odds === null || odds === undefined) return '-110';
    return odds > 0 ? `+${odds}` : odds.toString();
  };

  const getTeamAbbreviation = (teamName: string) => {
    // Common team name to abbreviation mappings
    const abbreviations: Record<string, string> = {
      'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
      'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
      'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
      'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
      'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
      'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
      'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
      'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
      'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
      'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
      // NFL teams
      'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
      'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
      'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
      'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
      'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
      'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
      'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
      'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
      'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
      'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
      'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS',
    };
    return abbreviations[teamName] || teamName.substring(0, 3).toUpperCase();
  };

  const fetchMLBGames = useCallback(async () => {
    try {
      const response = await api.mlb.getTodaysGames();
      setMlbGames((response.games || []) as MLBGame[]);
    } catch (err) {
      console.error('Failed to fetch MLB games:', err);
      throw err;
    }
  }, []);

  const fetchNBAGames = useCallback(async () => {
    try {
      const response = await api.nba.getTodaysGames();
      setNbaGames((response.games || []) as NBAGame[]);
    } catch (err) {
      console.error('Failed to fetch NBA games:', err);
      throw err;
    }
  }, []);

  const fetchNFLGames = useCallback(async () => {
    try {
      const response = await api.nfl.getGames();
      setNflGames((response.games || []) as NFLGame[]);
    } catch (err) {
      console.error('Failed to fetch NFL games:', err);
      throw err;
    }
  }, []);

  const fetchCBBGames = useCallback(async () => {
    try {
      const response = await api.cbb.getTodaysGames();
      setCbbGames((response.games || []) as CBBGame[]);
    } catch (err) {
      console.error('Failed to fetch CBB games:', err);
      throw err;
    }
  }, []);

  const fetchSoccerMatches = useCallback(async () => {
    try {
      const response = await api.soccer.getTodaysMatches();
      setSoccerMatches((response.matches || []) as SoccerMatch[]);
    } catch (err) {
      console.error('Failed to fetch soccer matches:', err);
      throw err;
    }
  }, []);

  const fetchCurrentSport = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      switch (activeTab) {
        case 'mlb':
          await fetchMLBGames();
          break;
        case 'nba':
          await fetchNBAGames();
          break;
        case 'nfl':
          await fetchNFLGames();
          break;
        case 'cbb':
          await fetchCBBGames();
          break;
        case 'soccer':
          await fetchSoccerMatches();
          break;
      }
    } catch {
      setError('Unable to load games. Try again.');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, fetchMLBGames, fetchNBAGames, fetchNFLGames, fetchCBBGames, fetchSoccerMatches]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      switch (activeTab) {
        case 'mlb':
          await api.mlb.refresh();
          break;
        case 'nba':
          await api.nba.refresh();
          break;
        case 'nfl':
          await api.nfl.refresh();
          break;
        case 'cbb':
          await api.cbb.refresh();
          break;
        case 'soccer':
          await api.soccer.refresh();
          break;
      }
      await fetchCurrentSport();
    } catch {
      setError('Refresh failed. Try again.');
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchCurrentSport();
  }, [fetchCurrentSport]);

  const getStatusBadge = (status: string) => {
    const lowerStatus = status.toLowerCase();
    if (lowerStatus === 'live' || lowerStatus.includes('in_play') || lowerStatus.includes('in progress')) {
      return (
        <Badge variant="success" className="flex items-center gap-1">
          <Circle className="w-2 h-2 fill-current animate-pulse" />
          Live
        </Badge>
      );
    }
    if (lowerStatus.includes('final') || lowerStatus.includes('finished')) {
      return <Badge variant="neutral">Final</Badge>;
    }
    if (lowerStatus.includes('scheduled') || lowerStatus.includes('pre')) {
      return <Badge variant="outline">Scheduled</Badge>;
    }
    // Check if it looks like a time (e.g., "8:00 pm ET")
    if (lowerStatus.includes('pm') || lowerStatus.includes('am') || lowerStatus.includes(':')) {
      return <Badge variant="outline">Scheduled</Badge>;
    }
    return <Badge variant="outline">{status}</Badge>;
  };

  const renderMLBGames = () => (
    <div className="grid gap-4">
      {mlbGames.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            icon={Trophy}
            title="No MLB games today"
            description="Check back later for upcoming matchups."
          />
        </Card>
      ) : (
        mlbGames.map((game) => (
          <Card key={game.id || game.game_pk} padding="md" hover>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  {getStatusBadge(game.status)}
                  {game.inning && game.inning_state && (
                    <span className="text-sm font-medium text-surface-600 dark:text-surface-400">
                      {game.inning_state} {game.inning}
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">
                      {game.away_team.name}
                    </span>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.away_team.score ?? '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">
                      {game.home_team.name}
                    </span>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.home_team.score ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 text-sm text-surface-500 dark:text-surface-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{game.game_time_display || new Date(game.game_date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}</span>
                </div>
                {game.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate max-w-[200px]">{game.venue}</span>
                  </div>
                )}
                {/* Weather Impact for MLB */}
                {game.venue && (
                  <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-700">
                    <WeatherImpact
                      sport="mlb"
                      venue={game.venue}
                      gameDate={game.game_date?.split('T')[0]}
                      compact
                    />
                  </div>
                )}
                {/* H2H Badge for MLB */}
                <div className="flex items-center gap-1 flex-wrap mt-1">
                  <H2HBadge
                    sport="mlb"
                    team1={game.home_team.name}
                    team2={game.away_team.name}
                    compact
                  />
                </div>
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );

  const renderNBAGames = () => (
    <div className="grid gap-4">
      {nbaGames.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            icon={Trophy}
            title="No NBA games today"
            description="Check back later for upcoming matchups."
          />
        </Card>
      ) : (
        nbaGames.map((game) => (
          <Card key={game.game_id} padding="md" hover>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  {getStatusBadge(game.game_status)}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.away_team.name || `Team ${game.away_team.id}`}
                      </span>
                      {game.odds?.moneyline_away && (
                        <span className="text-xs text-surface-500">
                          ({game.odds.moneyline_away > 0 ? '+' : ''}{game.odds.moneyline_away})
                        </span>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.away_team.score ?? '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.home_team.name || `Team ${game.home_team.id}`}
                      </span>
                      {game.odds?.moneyline_home && (
                        <span className="text-xs text-surface-500">
                          ({game.odds.moneyline_home > 0 ? '+' : ''}{game.odds.moneyline_home})
                        </span>
                      )}
                      {game.odds?.spread && (
                        <Badge variant="outline" className="text-xs">
                          {game.odds.spread > 0 ? '+' : ''}{game.odds.spread}
                        </Badge>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.home_team.score ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 text-sm text-surface-500 dark:text-surface-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{game.game_time_display || game.game_status || game.game_date}</span>
                </div>
                {game.odds && (game.odds.spread !== null || game.odds.total !== null) && (
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    <span>
                      {game.odds.spread !== null && `Spread: ${game.odds.spread > 0 ? '+' : ''}${game.odds.spread}`}
                      {game.odds.spread !== null && game.odds.total !== null && ' | '}
                      {game.odds.total !== null && `O/U: ${game.odds.total}`}
                    </span>
                  </div>
                )}
                {game.national_tv && (
                  <div className="flex items-center gap-2">
                    <Tv className="w-4 h-4" />
                    <span>{game.national_tv}</span>
                  </div>
                )}
                {game.arena && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate max-w-[200px]">{game.arena}</span>
                  </div>
                )}
                {/* H2H Badge for NBA */}
                <div className="flex items-center gap-1 flex-wrap mt-1">
                  <H2HBadge
                    sport="nba"
                    team1={game.home_team.name || `Team ${game.home_team.id}`}
                    team2={game.away_team.name || `Team ${game.away_team.id}`}
                    compact
                  />
                </div>
              </div>
            </div>

            {/* Betting Buttons */}
            {game.odds && (
              <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700">
                <div className="flex flex-wrap gap-2">
                  {/* Away Spread */}
                  {game.odds.spread !== null && (() => {
                    const awaySpread = -(game.odds.spread!);
                    const pickStr = `${getTeamAbbreviation(game.away_team.name || '')} ${awaySpread > 0 ? '+' : ''}${awaySpread}`;
                    const logged = isPickLogged(game.game_id, 'spread', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'spread',
                          line_value: awaySpread,
                          odds: game.odds?.spread_odds || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.spread_odds)})`}
                      </button>
                    );
                  })()}

                  {/* Home Spread */}
                  {game.odds.spread !== null && (() => {
                    const homeSpread = game.odds.spread!;
                    const pickStr = `${getTeamAbbreviation(game.home_team.name || '')} ${homeSpread > 0 ? '+' : ''}${homeSpread}`;
                    const logged = isPickLogged(game.game_id, 'spread', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'spread',
                          line_value: homeSpread,
                          odds: game.odds?.spread_odds || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.spread_odds)})`}
                      </button>
                    );
                  })()}

                  {/* Over */}
                  {game.odds.total !== null && (() => {
                    const pickStr = `O ${game.odds.total}`;
                    const logged = isPickLogged(game.game_id, 'total', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'total',
                          line_value: game.odds?.total || undefined,
                          odds: game.odds?.over_odds || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.over_odds)})`}
                      </button>
                    );
                  })()}

                  {/* Under */}
                  {game.odds.total !== null && (() => {
                    const pickStr = `U ${game.odds.total}`;
                    const logged = isPickLogged(game.game_id, 'total', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'total',
                          line_value: game.odds?.total || undefined,
                          odds: game.odds?.under_odds || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.under_odds)})`}
                      </button>
                    );
                  })()}

                  {/* Away Moneyline */}
                  {game.odds.moneyline_away !== null && (() => {
                    const pickStr = `${getTeamAbbreviation(game.away_team.name || '')} ML`;
                    const logged = isPickLogged(game.game_id, 'moneyline', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'moneyline',
                          odds: game.odds?.moneyline_away || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.moneyline_away)})`}
                      </button>
                    );
                  })()}

                  {/* Home Moneyline */}
                  {game.odds.moneyline_home !== null && (() => {
                    const pickStr = `${getTeamAbbreviation(game.home_team.name || '')} ML`;
                    const logged = isPickLogged(game.game_id, 'moneyline', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NBA',
                          home_team: game.home_team.name || `Team ${game.home_team.id}`,
                          away_team: game.away_team.name || `Team ${game.away_team.id}`,
                          pick: pickStr,
                          pick_type: 'moneyline',
                          odds: game.odds?.moneyline_home || -110,
                          game_time: game.game_date,
                          game_id: game.game_id,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (${formatOdds(game.odds?.moneyline_home)})`}
                      </button>
                    );
                  })()}
                </div>
              </div>
            )}
          </Card>
        ))
      )}
    </div>
  );

  const renderNFLGames = () => (
    <div className="grid gap-4">
      {nflGames.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            icon={Trophy}
            title="No NFL games this week"
            description="Check back later for upcoming matchups."
          />
        </Card>
      ) : (
        nflGames.map((game) => (
          <Card key={game.id || game.espn_id} padding="md" hover>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  {getStatusBadge(game.status)}
                  {game.week && (
                    <Badge variant="outline">Week {game.week}</Badge>
                  )}
                  {game.quarter && game.time_remaining && (
                    <span className="text-sm font-medium text-surface-600 dark:text-surface-400">
                      Q{game.quarter} - {game.time_remaining}
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.away_team.name}
                      </span>
                      {game.away_team.record && (
                        <span className="text-xs text-surface-500">({game.away_team.record})</span>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.away_team.score ?? '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.home_team.name}
                      </span>
                      {game.home_team.record && (
                        <span className="text-xs text-surface-500">({game.home_team.record})</span>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.home_team.score ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 text-sm text-surface-500 dark:text-surface-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{game.game_time_display || new Date(game.game_date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}</span>
                </div>
                {game.odds && (game.odds.spread !== null || game.odds.over_under !== null) && (
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    <span>
                      {game.odds.spread && `Spread: ${game.odds.spread > 0 ? '+' : ''}${game.odds.spread}`}
                      {game.odds.spread && game.odds.over_under && ' | '}
                      {game.odds.over_under && `O/U: ${game.odds.over_under}`}
                    </span>
                  </div>
                )}
                {/* Line Movement & Situational Indicators */}
                {game.id && (
                  <div className="flex items-center gap-1 flex-wrap">
                    <H2HBadge
                      sport="nfl"
                      team1={game.home_team.name}
                      team2={game.away_team.name}
                      compact
                    />
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400">
                      <ArrowLeftRight className="w-3 h-3" />
                      Lines
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400">
                      <Moon className="w-3 h-3" />
                      Rest
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400">
                      <Plane className="w-3 h-3" />
                      Travel
                    </span>
                  </div>
                )}
                {game.broadcast && (
                  <div className="flex items-center gap-2">
                    <Tv className="w-4 h-4" />
                    <span>{game.broadcast}</span>
                  </div>
                )}
                {game.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate max-w-[200px]">{game.venue}</span>
                  </div>
                )}
                {/* Weather Impact */}
                {game.venue && (
                  <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-700">
                    <WeatherImpact
                      sport="nfl"
                      venue={game.venue}
                      gameDate={game.game_date?.split('T')[0]}
                      compact
                    />
                  </div>
                )}
              </div>
            </div>

            {/* NFL Betting Buttons */}
            {game.odds && (game.odds.spread !== null || game.odds.over_under !== null) && (
              <div className="mt-4 pt-4 border-t border-surface-200 dark:border-surface-700">
                <div className="flex flex-wrap gap-2">
                  {/* Away Spread */}
                  {game.odds.spread !== null && (() => {
                    const awaySpread = -(game.odds.spread!);
                    const pickStr = `${getTeamAbbreviation(game.away_team.name)} ${awaySpread > 0 ? '+' : ''}${awaySpread}`;
                    const gameId = game.espn_id || String(game.id);
                    const logged = isPickLogged(gameId, 'spread', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NFL',
                          home_team: game.home_team.name,
                          away_team: game.away_team.name,
                          pick: pickStr,
                          pick_type: 'spread',
                          line_value: awaySpread,
                          odds: -110,
                          game_time: game.game_date,
                          game_id: gameId,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (-110)`}
                      </button>
                    );
                  })()}

                  {/* Home Spread */}
                  {game.odds.spread !== null && (() => {
                    const homeSpread = game.odds.spread!;
                    const pickStr = `${getTeamAbbreviation(game.home_team.name)} ${homeSpread > 0 ? '+' : ''}${homeSpread}`;
                    const gameId = game.espn_id || String(game.id);
                    const logged = isPickLogged(gameId, 'spread', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NFL',
                          home_team: game.home_team.name,
                          away_team: game.away_team.name,
                          pick: pickStr,
                          pick_type: 'spread',
                          line_value: homeSpread,
                          odds: -110,
                          game_time: game.game_date,
                          game_id: gameId,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (-110)`}
                      </button>
                    );
                  })()}

                  {/* Over */}
                  {game.odds.over_under !== null && (() => {
                    const pickStr = `O ${game.odds.over_under}`;
                    const gameId = game.espn_id || String(game.id);
                    const logged = isPickLogged(gameId, 'total', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NFL',
                          home_team: game.home_team.name,
                          away_team: game.away_team.name,
                          pick: pickStr,
                          pick_type: 'total',
                          line_value: game.odds?.over_under || undefined,
                          odds: -110,
                          game_time: game.game_date,
                          game_id: gameId,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (-110)`}
                      </button>
                    );
                  })()}

                  {/* Under */}
                  {game.odds.over_under !== null && (() => {
                    const pickStr = `U ${game.odds.over_under}`;
                    const gameId = game.espn_id || String(game.id);
                    const logged = isPickLogged(gameId, 'total', pickStr);
                    return (
                      <button
                        onClick={() => handlePickClick({
                          sport: 'NFL',
                          home_team: game.home_team.name,
                          away_team: game.away_team.name,
                          pick: pickStr,
                          pick_type: 'total',
                          line_value: game.odds?.over_under || undefined,
                          odds: -110,
                          game_time: game.game_date,
                          game_id: gameId,
                        })}
                        disabled={logged}
                        className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                          logged
                            ? 'bg-green-500/20 text-green-400 cursor-not-allowed'
                            : 'bg-surface-700 hover:bg-surface-600 text-white'
                        }`}
                      >
                        {logged ? <><Check className="w-3 h-3 inline mr-1" />Logged</> : `${pickStr} (-110)`}
                      </button>
                    );
                  })()}
                </div>
              </div>
            )}
          </Card>
        ))
      )}
    </div>
  );

  const renderCBBGames = () => (
    <div className="grid gap-4">
      {cbbGames.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            icon={Trophy}
            title="No college basketball games today"
            description="Check back later for upcoming matchups."
          />
        </Card>
      ) : (
        cbbGames.map((game, idx) => (
          <Card key={game.game_id || game.espn_id || idx} padding="md" hover>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  {getStatusBadge(game.status)}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {game.away_team.rank && game.away_team.rank <= 25 && (
                        <span className="text-primary-500 font-semibold">#{game.away_team.rank}</span>
                      )}
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.away_team.name}
                      </span>
                      {game.away_team.record && (
                        <span className="text-xs text-surface-500">({game.away_team.record})</span>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.status?.toLowerCase().includes('progress') || game.status?.toLowerCase().includes('final')
                        ? (game.away_team.score ?? '-')
                        : '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {game.home_team.rank && game.home_team.rank <= 25 && (
                        <span className="text-primary-500 font-semibold">#{game.home_team.rank}</span>
                      )}
                      <span className="font-medium text-surface-900 dark:text-white">
                        {game.home_team.name}
                      </span>
                      {game.home_team.record && (
                        <span className="text-xs text-surface-500">({game.home_team.record})</span>
                      )}
                    </div>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {game.status?.toLowerCase().includes('progress') || game.status?.toLowerCase().includes('final')
                        ? (game.home_team.score ?? '-')
                        : '-'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 text-sm text-surface-500 dark:text-surface-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{game.game_time_display || game.status_detail || new Date(game.game_date || game.date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}</span>
                </div>
                {game.broadcast && (
                  <div className="flex items-center gap-2">
                    <Tv className="w-4 h-4" />
                    <span>{game.broadcast}</span>
                  </div>
                )}
                {game.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate max-w-[200px]">{game.venue}</span>
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );

  const renderSoccerMatches = () => (
    <div className="grid gap-4">
      {soccerMatches.length === 0 ? (
        <Card padding="lg">
          <EmptyState
            icon={Trophy}
            title="No soccer matches today"
            description="Check back later for upcoming fixtures."
          />
        </Card>
      ) : (
        soccerMatches.map((match) => (
          <Card key={match.id} padding="md" hover>
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  {getStatusBadge(match.status)}
                  <Badge variant="outline">{match.competition}</Badge>
                  {match.matchday && (
                    <span className="text-sm text-surface-500 dark:text-surface-400">
                      Matchday {match.matchday}
                    </span>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">
                      {match.home_team.name}
                    </span>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {match.home_team.score ?? '-'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-surface-900 dark:text-white">
                      {match.away_team.name}
                    </span>
                    <span className="text-xl font-bold text-surface-900 dark:text-white">
                      {match.away_team.score ?? '-'}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-2 text-sm text-surface-500 dark:text-surface-400">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4" />
                  <span>{match.game_time_display || new Date(match.match_date).toLocaleDateString('en-US', {
                    weekday: 'short',
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}</span>
                </div>
                {match.venue && (
                  <div className="flex items-center gap-2">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate max-w-[200px]">{match.venue}</span>
                  </div>
                )}
                {/* Weather Impact for Soccer */}
                {match.venue && (
                  <div className="mt-2 pt-2 border-t border-surface-200 dark:border-surface-700">
                    <WeatherImpact
                      sport="soccer"
                      venue={match.venue}
                      gameDate={match.match_date?.split('T')[0]}
                      compact
                    />
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-[40vh]">
          <LoadingSpinner size="lg" text="Loading games..." />
        </div>
      );
    }

    if (error) {
      return (
        <div className="flex items-center justify-center min-h-[40vh]">
          <ErrorMessage
            message={error}
            variant="fullpage"
            onRetry={fetchCurrentSport}
          />
        </div>
      );
    }

    switch (activeTab) {
      case 'mlb':
        return renderMLBGames();
      case 'nba':
        return renderNBAGames();
      case 'nfl':
        return renderNFLGames();
      case 'cbb':
        return renderCBBGames();
      case 'soccer':
        return renderSoccerMatches();
      default:
        return null;
    }
  };

  const getGameCount = () => {
    switch (activeTab) {
      case 'mlb':
        return mlbGames.length;
      case 'nba':
        return nbaGames.length;
      case 'nfl':
        return nflGames.length;
      case 'cbb':
        return cbbGames.length;
      case 'soccer':
        return soccerMatches.length;
      default:
        return 0;
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-display text-surface-900 dark:text-white">
            Live Scoreboard
          </h1>
          <p className="text-lg text-surface-500 dark:text-surface-400 mt-2">
            Real-time scores. Every league.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Refreshing...' : 'Refresh Data'}
        </Button>
      </div>

      {/* Sport Tabs */}
      <div className="border-b border-surface-200 dark:border-surface-700">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {(Object.keys(SPORT_CONFIG) as SportTab[]).map((sport) => (
            <button
              key={sport}
              onClick={() => setActiveTab(sport)}
              className={`
                flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap
                ${activeTab === sport
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-surface-500 hover:text-surface-700 hover:border-surface-300 dark:text-surface-400 dark:hover:text-surface-300'
                }
              `}
            >
              <span>{SPORT_CONFIG[sport].icon}</span>
              <span>{SPORT_CONFIG[sport].name}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Results count */}
      <p className="text-sm text-surface-500 dark:text-surface-400">
        {getGameCount()} {activeTab === 'soccer' ? 'matches' : 'games'}
        {activeTab === 'nba' && nbaGames.some(g => g.game_status?.toLowerCase() === 'live') && (
          <span className="ml-2 text-green-500 font-medium">
            ({nbaGames.filter(g => g.game_status?.toLowerCase() === 'live').length} live)
          </span>
        )}
      </p>

      {/* Games Content */}
      {renderContent()}

      {/* Pick Logger Modal */}
      {selectedPick && (
        <PickLoggerModal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setSelectedPick(null);
          }}
          onSuccess={handlePickLogged}
          pickData={selectedPick}
        />
      )}
    </div>
  );
}
