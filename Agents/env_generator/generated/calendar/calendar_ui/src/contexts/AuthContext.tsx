import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

interface User {
  id: string;
  email: string;
  name?: string | null;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

const TOKEN_STORAGE_KEY = "auth_token";

const getApiBaseUrl = (): string => {
  // Prefer an environment variable if available, otherwise default to same-origin /api
  if (typeof import.meta !== "undefined" && (import.meta as any).env) {
    const envBase =
      (import.meta as any).env.VITE_API_BASE_URL ||
      (import.meta as any).env.API_BASE_URL;
    if (envBase) {
      return envBase.replace(/\/+$/, "");
    }
  }
  return "/api";
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") {
      return null;
    }
    return window.localStorage.getItem(TOKEN_STORAGE_KEY);
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const apiBaseUrl = getApiBaseUrl();

  useEffect(() => {
    const initAuth = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${apiBaseUrl}/auth/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!response.ok) {
          if (typeof window !== "undefined") {
            window.localStorage.removeItem(TOKEN_STORAGE_KEY);
          }
          setToken(null);
          setUser(null);
        } else {
          const userData: User = await response.json();
          setUser(userData);
        }
      } catch {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(TOKEN_STORAGE_KEY);
        }
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    void initAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, apiBaseUrl]);

  const login = async (email: string, password: string): Promise<void> => {
    const response = await fetch(`${apiBaseUrl}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message =
        (data && (data.detail as string | undefined)) || "Login failed";
      throw new Error(message);
    }

    const accessToken: string | undefined = data.access_token;
    if (!accessToken) {
      throw new Error("Invalid response from server: missing access token");
    }

    if (typeof window !== "undefined") {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    }
    setToken(accessToken);

    // If backend also returns user object, set it; otherwise fetch /me
    if (data.user) {
      setUser(data.user as User);
    } else {
      try {
        const meResponse = await fetch(`${apiBaseUrl}/auth/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        });
        if (meResponse.ok) {
          const userData: User = await meResponse.json();
          setUser(userData);
        }
      } catch {
        // If /me fails, still consider user authenticated with token
      }
    }
  };

  const register = async (
    email: string,
    password: string,
    name?: string
  ): Promise<void> => {
    const response = await fetch(`${apiBaseUrl}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password, name }),
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const message =
        (data && (data.detail as string | undefined)) ||
        "Registration failed";
      throw new Error(message);
    }

    // Auto-login after successful registration
    await login(email, password);
  };

  const logout = (): void => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
    setToken(null);
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!token,
    isLoading,
    login,
    register,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
tsx
tsx
tsx