export interface User {
  id: number;
  email: string;
  name: string;
  bankroll: number;
  risk_profile: 'conservative' | 'balanced' | 'aggressive';
  created_at: string;
}

export interface Client {
  id: number;
  name: string;
  bankroll: number;
  risk_profile: 'conservative' | 'balanced' | 'aggressive';
  created_at: string;
}

export interface Game {
  id: number;
  sport: string;
  home_team_id: number | null;
  away_team_id: number | null;
  home_team_name: string | null;
  away_team_name: string | null;
  competitor1_id: number | null;
  competitor2_id: number | null;
  competitor1_name: string | null;
  competitor2_name: string | null;
  start_time: string;
  venue: string;
  league: string;
}

export interface Recommendation {
  id: number;
  client_id: number;
  sport: string;
  game_info: string;
  market_type: string;
  selection: string;
  sportsbook: string;
  american_odds: number;
  line_value: number | null;
  model_probability: number;
  implied_probability: number;
  edge: number;
  expected_value: number;
  suggested_stake: number;
  explanation: string;
  created_at: string;
}

export interface RecommendationResponse {
  client_id: number;
  client_name: string;
  recommendations: Recommendation[];
  total_recommended_stake: number;
}

export interface Team {
  id: number;
  sport: string;
  name: string;
  short_name: string;
  rating: number;
}

export interface Competitor {
  id: number;
  sport: string;
  name: string;
  rating: number;
}

export type Sport = 
  | 'NFL' | 'NBA' | 'MLB' | 'NHL' 
  | 'NCAA_FOOTBALL' | 'NCAA_BASKETBALL' 
  | 'SOCCER' | 'CRICKET' | 'RUGBY' 
  | 'TENNIS' | 'GOLF' | 'MMA' | 'BOXING' 
  | 'MOTORSPORTS' | 'ESPORTS';

export const SPORTS: Sport[] = [
  'NFL', 'NBA', 'MLB', 'NHL',
  'NCAA_FOOTBALL', 'NCAA_BASKETBALL',
  'SOCCER', 'CRICKET', 'RUGBY',
  'TENNIS', 'GOLF', 'MMA', 'BOXING',
  'MOTORSPORTS', 'ESPORTS'
];

export const SPORT_LABELS: Record<Sport, string> = {
  NFL: 'NFL',
  NBA: 'NBA',
  MLB: 'MLB',
  NHL: 'NHL',
  NCAA_FOOTBALL: 'NCAA Football',
  NCAA_BASKETBALL: 'NCAA Basketball',
  SOCCER: 'Soccer',
  CRICKET: 'Cricket',
  RUGBY: 'Rugby',
  TENNIS: 'Tennis',
  GOLF: 'Golf',
  MMA: 'MMA',
  BOXING: 'Boxing',
  MOTORSPORTS: 'Motorsports',
  ESPORTS: 'Esports'
};

export interface BacktestResult {
  id: number;
  sport: string;
  model: string;
  period: string;
  accuracy: number;
  roi: number | null;
  bets: number;
  brier_score: number | null;
  created: string;
}

export interface ModelStatus {
  is_fitted: boolean;
  teams_tracked: number;
  k_factor: number;
  home_advantage: number;
  last_update: string | null;
}

export interface TeamRating {
  id: number;
  name: string;
  short_name: string | null;
  rating: number;
  model_rating: number | null;
}

export interface DFSProjection {
  player_id: number;
  player_name: string;
  position: string;
  team_id: number;
  team_name?: string;
  salary: number;
  projected_points: number;
  floor: number;
  ceiling: number;
  std_dev: number;
  value_score: number;
  ownership_projection: number;
  leverage_score: number;
  confidence: number;
}

export interface DFSLineup {
  id: number;
  sport: string;
  platform: string;
  slate_date: string;
  total_salary: number;
  salary_remaining: number;
  projected_points: number;
  projected_ownership: number | null;
  lineup_type: string;
  player_ids: number[];
  positions: string[];
  actual_points: number | null;
  finish_position: number | null;
  is_submitted: boolean;
  created_at: string;
}

export interface OptimizeResult {
  success: boolean;
  lineup?: DFSProjection[];
  lineup_id?: number;
  total_salary?: number;
  salary_remaining?: number;
  projected_points?: number;
  projected_ownership?: number;
  lineup_type?: string;
  correlation_analysis?: {
    total_correlation: number;
    lineup_rating: string;
    stacks: Array<{ team_name: string; size: number; positions: string[] }>;
    recommendation: string;
  };
  error?: string;
}

export interface DFSStack {
  name: string;
  positions: string[];
  correlation: number;
  notes: string;
}
