const BASE_URL = '/api';

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('session_token');

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    let message = `HTTP error ${response.status}`;
    if (error.detail) {
      if (typeof error.detail === 'string') {
        message = error.detail;
      } else if (Array.isArray(error.detail)) {
        message = error.detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
      }
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Auth
  auth: {
    login: (data: { email?: string; identifier?: string; password: string; totp_code?: string }) =>
      request<{ access_token: string; refresh_token: string; user: any; requires_2fa?: boolean }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          email_or_username: data.email || data.identifier,
          password: data.password,
          ...(data.totp_code && { totp_code: data.totp_code })
        }),
      }),
    register: (data: { email: string; username: string; password: string }) =>
      request<{ access_token: string; refresh_token: string; user: any }>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    me: () => request<any>('/auth/me'),
    logout: () => request<void>('/auth/logout', { method: 'POST' }),
    refresh: (refreshToken: string) =>
      request<{ access_token: string; refresh_token: string }>('/auth/refresh', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken }),
      }),
  },

  // Clients
  clients: {
    get: (id: number) => request<any>(`/clients/${id}`),
    create: (data: any) =>
      request<any>('/clients', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: any) =>
      request<any>(`/clients/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  },

  // Recommendations
  recommendations: {
    latest: (clientId: number, limit = 20) =>
      request<any[]>(`/clients/${clientId}/recommendations/latest?limit=${limit}`),
    run: (clientId: number, params: { sports?: string[]; min_edge?: number }) =>
      request<any>(`/clients/${clientId}/recommendations/run`, {
        method: 'POST',
        body: JSON.stringify(params),
      }),
  },

  // Games
  games: {
    list: (sport?: string, limit = 50) =>
      request<any[]>(`/games${sport ? `?sport=${sport}&` : '?'}limit=${limit}`),
    sports: () => request<string[]>('/games/sports'),
  },

  // Tracking
  tracking: {
    getStats: () => request<any>('/tracking/stats'),
    getBets: (status?: string, sport?: string) => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      if (sport) params.append('sport', sport);
      return request<any[]>(`/tracking/bets?${params}`);
    },
    getLeaderboard: (sortBy: string, limit: number) =>
      request<any[]>(`/tracking/leaderboard?sort_by=${sortBy}&limit=${limit}`),
    placeBet: (data: any) =>
      request<any>('/tracking/bets', { method: 'POST', body: JSON.stringify(data) }),
    settleBet: (betId: number, result: string) =>
      request<any>(`/tracking/bets/${betId}/settle`, {
        method: 'POST',
        body: JSON.stringify({ result }),
      }),
  },

  // Billing
  billing: {
    getPlans: () => request<any[]>('/billing/plans'),
    getSubscription: () => request<any>('/billing/subscription'),
    createCheckout: (priceId: string, billingPeriod: string) =>
      request<{ url: string }>('/billing/checkout', {
        method: 'POST',
        body: JSON.stringify({ price_id: priceId, billing_period: billingPeriod }),
      }),
    createPortal: () => request<{ url: string }>('/billing/portal', { method: 'POST' }),
  },

  // Alerts
  alerts: {
    list: () => request<any[]>('/alerts'),
    getTypes: () => request<string[]>('/alerts/types'),
    create: (data: any) =>
      request<any>('/alerts', { method: 'POST', body: JSON.stringify(data) }),
    toggle: (alertId: number) =>
      request<any>(`/alerts/${alertId}/toggle`, { method: 'POST' }),
    delete: (alertId: number) =>
      request<void>(`/alerts/${alertId}`, { method: 'DELETE' }),
  },

  // Webhooks
  webhooks: {
    list: () => request<any[]>('/webhooks'),
    create: (data: any) =>
      request<any>('/webhooks', { method: 'POST', body: JSON.stringify(data) }),
    delete: (webhookId: number) =>
      request<void>(`/webhooks/${webhookId}`, { method: 'DELETE' }),
  },

  // Telegram
  telegram: {
    getStatus: () => request<any>('/telegram/status'),
    generateLinkCode: () => request<{ code: string }>('/telegram/link', { method: 'POST' }),
    unlink: () => request<void>('/telegram/unlink', { method: 'POST' }),
  },

  // Historical / Models
  historical: {
    getModelStatus: () => request<any>('/historical/models/status'),
    getBacktestResults: () => request<any[]>('/historical/backtests'),
    getTeamRatings: (sport: string) => request<any[]>(`/historical/ratings/${sport}`),
    seedData: (seasons: number) =>
      request<any>('/historical/seed', {
        method: 'POST',
        body: JSON.stringify({ seasons }),
      }),
    trainModels: () => request<any>('/historical/train', { method: 'POST' }),
    runBacktest: (sport: string, seasons: number, minEdge: number) =>
      request<any>('/historical/backtest', {
        method: 'POST',
        body: JSON.stringify({ sport, seasons, min_edge: minEdge }),
      }),
  },

  // Coaches
  coaches: {
    getSituationsList: () => request<any[]>('/coaches/situations'),
    getLeaderboard: (metric: string, situation: string, minGames: number) =>
      request<any[]>(
        `/coaches/leaderboard?metric=${metric}&situation=${situation}&min_games=${minGames}`
      ),
  },

  // Sports APIs
  mlb: {
    getTodaysGames: () => {
      // Use local date, not UTC
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      return request<any>(`/mlb/games?start_date=${today}`);
    },
    refresh: () => request<any>('/mlb/refresh', { method: 'POST' }),
  },
  nba: {
    getTodaysGames: () => {
      // Use local date, not UTC (toISOString returns UTC which can be next day after 7pm EST)
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      return request<any>(`/nba/games?start_date=${today}`);
    },
    refresh: () => request<any>('/nba/refresh', { method: 'POST' }),
  },
  nfl: {
    getGames: () => request<any>('/nfl/games'),
    refresh: () => request<any>('/nfl/refresh', { method: 'POST' }),
  },
  cbb: {
    getTodaysGames: () => {
      // Use local date, not UTC
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      return request<any>(`/cbb/games?start_date=${today}`);
    },
    refresh: () => request<any>('/cbb/refresh', { method: 'POST' }),
  },
  soccer: {
    getTodaysMatches: () => {
      // Use local date, not UTC
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      return request<any>(`/soccer/matches?date=${today}`);
    },
    refresh: () => request<any>('/soccer/refresh', { method: 'POST' }),
  },

  // Parlays
  parlays: {
    analyze: (legs: Array<{ selection: string; odds: number; probability: number }>) =>
      request<any>('/parlays/analyze', {
        method: 'POST',
        body: JSON.stringify({ legs }),
      }),
    list: () => request<any[]>('/parlays'),
    create: (data: any) =>
      request<any>('/parlays', { method: 'POST', body: JSON.stringify(data) }),
  },

  // Security
  security: {
    get2FAStatus: () => request<any>('/security/2fa/status'),
    getSessions: () => request<any[]>('/security/sessions'),
    getAuditLogs: (limit: number) => request<any[]>(`/security/audit?limit=${limit}`),
    setup2FA: () => request<{ secret: string; qr_code: string }>('/security/2fa/setup', { method: 'POST' }),
    enable2FA: (code: string) =>
      request<{ backup_codes: string[] }>('/security/2fa/enable', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    disable2FA: (code: string) =>
      request<void>('/security/2fa/disable', {
        method: 'POST',
        body: JSON.stringify({ code }),
      }),
    revokeSession: (sessionId: number) =>
      request<void>(`/security/sessions/${sessionId}`, { method: 'DELETE' }),
    revokeAllSessions: () =>
      request<void>('/security/sessions', { method: 'DELETE' }),
  },

  // DFS
  dfs: {
    getProjections: (sport: string, platform: string, limit: number) =>
      request<any[]>(`/dfs/projections?sport=${sport}&platform=${platform}&limit=${limit}`),
    getStacks: (sport: string) => request<any[]>(`/dfs/stacks?sport=${sport}`),
    getLineups: (clientId: number, sport: string) =>
      request<any[]>(`/dfs/lineups?client_id=${clientId}&sport=${sport}`),
    optimize: (clientId: number, params: any) =>
      request<any>('/dfs/optimize', {
        method: 'POST',
        body: JSON.stringify({ client_id: clientId, ...params }),
      }),
    deleteLineup: (clientId: number, lineupId: number) =>
      request<void>(`/dfs/lineups/${lineupId}?client_id=${clientId}`, { method: 'DELETE' }),
  },

  // Account
  account: {
    forgotPassword: (email: string) =>
      request<void>('/account/forgot-password', {
        method: 'POST',
        body: JSON.stringify({ email }),
      }),
    resetPassword: (token: string, password: string) =>
      request<void>('/account/reset-password', {
        method: 'POST',
        body: JSON.stringify({ token, password }),
      }),
    updateProfile: (data: any) =>
      request<any>('/account/profile', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    verifyAge: (data: { date_of_birth: string }) =>
      request<any>('/account/verify-age', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // H2H
  h2h: {
    getSummary: (sport: string, team1: string, team2: string) =>
      request<any>(`/h2h/${sport}/${encodeURIComponent(team1)}/${encodeURIComponent(team2)}/summary`),
  },

  // Weather
  weather: {
    getImpact: (sport: string, venue: string, date: string, hour: number) => {
      // Map sport to correct endpoint
      const sportLower = sport.toLowerCase();
      const endpoint = sportLower === 'nba' ? 'mlb' : sportLower; // NBA uses indoor, fallback to mlb format
      return request<any>(
        `/weather/impact/${endpoint}?venue=${encodeURIComponent(venue)}&game_date=${date}&game_hour=${hour}`
      );
    },
  },
};

export default api;
