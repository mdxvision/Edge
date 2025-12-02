import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { Client, User } from '@/types';
import api from '@/lib/api';

interface AuthContextType {
  client: Client | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (clientId: number) => Promise<void>;
  loginWithToken: (sessionToken: string, refreshToken?: string) => Promise<void>;
  logout: () => void;
  updateClient: (data: Partial<Client>) => Promise<void>;
  createClient: (data: { name: string; bankroll: number; risk_profile: string }) => Promise<Client>;
  refreshUser: () => Promise<void>;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<Client | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUserData = async () => {
    try {
      const profile = await api.auth.me();
      setUser({
        id: profile.id,
        email: profile.email,
        username: profile.username,
        display_name: profile.display_name,
        preferred_currency: profile.preferred_currency,
        is_verified: profile.is_verified,
        is_age_verified: profile.is_age_verified,
        totp_enabled: profile.totp_enabled,
        created_at: profile.created_at,
      });
      return true;
    } catch {
      setUser(null);
      return false;
    }
  };

  const loadClientData = async () => {
    const savedClientId = localStorage.getItem('clientId');
    if (savedClientId) {
      try {
        const clientData = await api.clients.get(parseInt(savedClientId));
        setClient(clientData);
        return true;
      } catch {
        localStorage.removeItem('clientId');
      }
    }
    return false;
  };

  useEffect(() => {
    const sessionToken = localStorage.getItem('session_token');

    const loadData = async () => {
      if (sessionToken) {
        const userLoaded = await loadUserData();
        if (userLoaded) {
          await loadClientData();
        } else {
          localStorage.removeItem('session_token');
          localStorage.removeItem('refresh_token');
        }
      }
      setIsLoading(false);
    };

    loadData();
  }, []);

  const login = async (clientId: number) => {
    const clientData = await api.clients.get(clientId);
    setClient(clientData);
    localStorage.setItem('clientId', clientId.toString());
    await loadUserData();
  };

  const loginWithToken = async (sessionToken: string, refreshToken?: string) => {
    localStorage.setItem('session_token', sessionToken);
    if (refreshToken) {
      localStorage.setItem('refresh_token', refreshToken);
    }
    await loadUserData();
    await loadClientData();
  };

  const refreshSession = async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;

    try {
      const result = await api.auth.refresh(refreshToken);
      localStorage.setItem('session_token', result.session_token);
      localStorage.setItem('refresh_token', result.refresh_token);
      return true;
    } catch {
      logout();
      return false;
    }
  };

  const logout = async () => {
    try {
      await api.auth.logout();
    } catch {
      // Ignore logout errors
    }
    setClient(null);
    setUser(null);
    localStorage.removeItem('clientId');
    localStorage.removeItem('session_token');
    localStorage.removeItem('refresh_token');
  };

  const updateClient = async (data: Partial<Client>) => {
    if (!client) return;
    const updated = await api.clients.update(client.id, data);
    setClient(updated);
  };

  const createClient = async (data: { name: string; bankroll: number; risk_profile: string }) => {
    const newClient = await api.clients.create(data);
    setClient(newClient);
    localStorage.setItem('clientId', newClient.id.toString());
    return newClient;
  };

  const refreshUser = async () => {
    await loadUserData();
  };

  return (
    <AuthContext.Provider
      value={{
        client,
        user,
        isLoading,
        isAuthenticated: !!user && !!client,
        login,
        loginWithToken,
        logout,
        updateClient,
        createClient,
        refreshUser,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
