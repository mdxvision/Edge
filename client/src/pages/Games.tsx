import { useEffect, useState } from 'react';
import { Card, Badge, Select } from '@/components/ui';
import api from '@/lib/api';
import type { Game, Sport } from '@/types';
import { SPORTS, SPORT_LABELS } from '@/types';
import { Trophy, Clock, MapPin, Search } from 'lucide-react';

export default function Games() {
  const [games, setGames] = useState<Game[]>([]);
  const [filteredGames, setFilteredGames] = useState<Game[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSport, setSelectedSport] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    async function fetchGames() {
      try {
        const data = await api.games.list();
        setGames(data);
        setFilteredGames(data);
      } catch (err) {
        console.error('Failed to fetch games:', err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchGames();
  }, []);

  useEffect(() => {
    let filtered = games;

    if (selectedSport !== 'all') {
      filtered = filtered.filter((game) => game.sport === selectedSport);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((game) => {
        const teams = [
          game.home_team_name,
          game.away_team_name,
          game.competitor1_name,
          game.competitor2_name,
          game.league,
          game.venue,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return teams.includes(query);
      });
    }

    setFilteredGames(filtered);
  }, [selectedSport, searchQuery, games]);

  const sportOptions = [
    { value: 'all', label: 'All Sports' },
    ...SPORTS.map((sport) => ({
      value: sport,
      label: SPORT_LABELS[sport as Sport],
    })),
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 bg-surface-200 dark:bg-surface-800 rounded w-48 animate-pulse" />
        <div className="grid gap-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-surface-200 dark:bg-surface-800 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
          Games
        </h1>
        <p className="text-surface-500 mt-1">
          Browse upcoming matchups across all sports
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
          <input
            type="text"
            placeholder="Search teams, leagues, venues..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
          />
        </div>
        <div className="w-full sm:w-48">
          <Select
            value={selectedSport}
            onChange={(e) => setSelectedSport(e.target.value)}
            options={sportOptions}
          />
        </div>
      </div>

      <div className="text-sm text-surface-500">
        Showing {filteredGames.length} of {games.length} games
      </div>

      <div className="grid gap-4">
        {filteredGames.length === 0 ? (
          <Card className="text-center py-12">
            <Trophy className="w-12 h-12 mx-auto text-surface-300 dark:text-surface-600 mb-4" />
            <p className="text-surface-500">No games found</p>
            <p className="text-sm text-surface-400 mt-1">
              Try adjusting your filters
            </p>
          </Card>
        ) : (
          filteredGames.map((game) => (
            <Card key={game.id} padding="md" className="hover:shadow-md transition-shadow">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant="primary">{SPORT_LABELS[game.sport as Sport] || game.sport}</Badge>
                    <span className="text-sm text-surface-500">{game.league}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-surface-900 dark:text-white">
                    {game.home_team_name || game.competitor1_name}
                    <span className="text-surface-400 mx-2">vs</span>
                    {game.away_team_name || game.competitor2_name}
                  </h3>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 text-sm text-surface-500">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>
                      {new Date(game.start_time).toLocaleDateString('en-US', {
                        weekday: 'short',
                        month: 'short',
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
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
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
