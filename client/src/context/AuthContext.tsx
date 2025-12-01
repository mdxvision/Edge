import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { Client } from '@/types';
import api from '@/lib/api';

interface AuthContextType {
  client: Client | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (clientId: number) => Promise<void>;
  logout: () => void;
  updateClient: (data: Partial<Client>) => Promise<void>;
  createClient: (data: { name: string; bankroll: number; risk_profile: string }) => Promise<Client>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [client, setClient] = useState<Client | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedClientId = localStorage.getItem('clientId');
    if (savedClientId) {
      api.clients.get(parseInt(savedClientId))
        .then(setClient)
        .catch(() => {
          localStorage.removeItem('clientId');
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (clientId: number) => {
    const clientData = await api.clients.get(clientId);
    setClient(clientData);
    localStorage.setItem('clientId', clientId.toString());
  };

  const logout = () => {
    setClient(null);
    localStorage.removeItem('clientId');
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

  return (
    <AuthContext.Provider
      value={{
        client,
        isLoading,
        isAuthenticated: !!client,
        login,
        logout,
        updateClient,
        createClient,
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
