import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from 'axios';

// ===== Types aligned with backend schemas =====

// These interfaces mirror calendar_api/schemas.py based on typical patterns.
// Adjust as needed if backend schemas change.

export interface UserBase {
  email: string;
  full_name?: string | null;
}

export interface UserCreate extends UserBase {
  password: string;
}

export interface UserLogin {
  email: string;
  password: string;
}

export interface UserResponse extends UserBase {
  id: number;
  created_at: string; // ISO datetime string
  updated_at?: string | null;
}

export interface Token {
  access_token: string;
  token_type: 'bearer' | string;
  user: UserResponse;
}

export interface HealthResponse {
  status: string;
}

// ===== API Error Wrapper =====

export class ApiError<T = unknown> extends Error {
  public status: number;
  public details?: T;

  constructor(status: number, message: string, details?: T) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// ===== Axios Instance Configuration =====

// Prefer an explicit env var but default to the FastAPI dev port.
// The backend in main.py does not use a /api prefix, so we keep baseURL
// as the root and let the dev server proxy /api -> backend if configured.
const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// LocalStorage key used to store the auth token.
// Keep this consistent with your AuthContext implementation.
const AUTH_TOKEN_STORAGE_KEY = 'auth_token';

// Optional external token getter; if not provided, localStorage is used.
let externalTokenGetter: (() => string | null) | null = null;

export const setAuthTokenGetter = (getter: () => string | null): void => {
  externalTokenGetter = getter;
};

const getAuthToken = (): string | null => {
  if (externalTokenGetter) {
    return externalTokenGetter();
  }

  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const stored = window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
    return stored || null;
  } catch {
    return null;
  }
};

const api: AxiosInstance = axios.create({
  baseURL: '/api', // assume frontend dev server proxies /api -> API_BASE_URL
  withCredentials: false,
});

// Attach Authorization header if token is available
api.interceptors.request.use(
  (config: AxiosRequestConfig): AxiosRequestConfig => {
    const token = getAuthToken();
    if (token && config.headers) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (config.headers as any).Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error),
);

// Basic response error normalization
api.interceptors.response.use(
  (response: AxiosResponse): AxiosResponse => response,
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data: any = error.response.data;
      const message =
        (data && (data.detail || data.message)) ||
        error.message ||
        'Request failed';
      throw new ApiError(status, message, data);
    }

    if (error.request) {
      throw new ApiError(0, 'Network error or no response from server');
    }

    throw new ApiError(0, error.message || 'Unknown Axios error');
  },
);

// ===== Generic request helper (optional but useful) =====

export async function request<T = unknown>(
  config: AxiosRequestConfig,
): Promise<T> {
  const response = await api.request<T>(config);
  return response.data;
}

// ===== Auth API =====

export const authApi = {
  /**
   * POST /auth/register
   * Body: UserCreate
   * Response: UserResponse
   */
  register: (data: UserCreate): Promise<UserResponse> =>
    request<UserResponse>({
      method: 'POST',
      url: '/auth/register',
      data,
    }),

  /**
   * POST /auth/login
   * Body: UserLogin
   * Response: Token
   */
  login: (data: UserLogin): Promise<Token> =>
    request<Token>({
      method: 'POST',
      url: '/auth/login',
      data,
    }),

  /**
   * GET /auth/me
   * Requires Authorization header (handled by interceptor).
   * Response: UserResponse
   */
  me: (): Promise<UserResponse> =>
    request<UserResponse>({
      method: 'GET',
      url: '/auth/me',
    }),
};

// ===== Misc / Health API =====

export const systemApi = {
  health: (): Promise<HealthResponse> =>
    request<HealthResponse>({
      method: 'GET',
      url: '/health',
    }),
};

export default api;