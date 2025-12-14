import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  ReactNode,
} from "react";
import axios, { AxiosError } from "axios";

interface User {
  id: string;
  email: string;
  full_name?: string;
}

interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_STORAGE_KEY = "auth_token";
const API_BASE_URL = "/api"; // adjust if backend is served from a different base path

const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token && config.headers) {
    // FastAPI expects `Authorization: Bearer <token>`
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(
    typeof window !== "undefined" ? localStorage.getItem(TOKEN_STORAGE_KEY) : null,
  );
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Initialize auth state from stored token and fetch current user if possible
  useEffect(() => {
    const initializeAuth = async () => {
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await api.get<User>("/auth/me");
        setUser(response.data);
      } catch {
        // Token might be invalid/expired
        localStorage.removeItem(TOKEN_STORAGE_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    void initializeAuth();
  }, [token]);

  const handleAuthError = (err: unknown, defaultMessage: string): never => {
    let message = defaultMessage;

    if (axios.isAxiosError(err)) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      if (axiosError.response?.data?.detail) {
        message = axiosError.response.data.detail;
      } else if (axiosError.message) {
        message = axiosError.message;
      }
    } else if (err instanceof Error && err.message) {
      message = err.message;
    }

    setError(message);
    throw new Error(message);
  };

  const login = async (email: string, password: string): Promise<void> => {
    setError(null);
    try {
      const response = await api.post<AuthResponse>("/auth/login", {
        email,
        password,
      } as LoginCredentials);

      const { access_token, user: userData } = response.data;

      localStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      setToken(access_token);
      if (userData) {
        setUser(userData);
      } else {
        // Fallback: fetch user info if not included in login response
        try {
          const meResponse = await api.get<User>("/auth/me");
          setUser(meResponse.data);
        } catch {
          setUser(null);
        }
      }
    } catch (err) {
      handleAuthError(err, "Login failed");
    }
  };

  const register = async (payload: RegisterPayload): Promise<void> => {
    setError(null);
    try {
      await api.post("/auth/register", payload);
      // Auto-login after successful registration
      await login(payload.email, payload.password);
    } catch (err) {
      handleAuthError(err, "Registration failed");
    }
  };

  const logout = (): void => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
    setError(null);
  };

  const clearError = (): void => {
    setError(null);
  };

  const value: AuthContextType = useMemo(
    () => ({
      user,
      token,
      isAuthenticated: Boolean(token),
      isLoading,
      error,
      login,
      register,
      logout,
      clearError,
    }),
    [user, token, isLoading, error],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
tsx

export default AuthProvider;
export default AuthProvider;
export { AuthProvider };