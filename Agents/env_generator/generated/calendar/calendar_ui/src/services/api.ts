import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";

const TOKEN_STORAGE_KEY = "auth_token";

// Prefer env var, fallback to same-origin /api (matching AuthContext default)
const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined"
    ? `${window.location.origin}/api`
    : "/api");

export class ApiError<T = unknown> extends Error {
  public status: number;
  public details?: T;

  constructor(status: number, message: string, details?: T) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach Authorization header from localStorage on every request
api.interceptors.request.use((config: AxiosRequestConfig) => {
  if (typeof window === "undefined") {
    return config;
  }

  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token && config.headers) {
    // FastAPI expects `Authorization: Bearer <token>`
    (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
  }

  return config;
});

// Optional response interceptor stub (can be extended for global error handling)
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // Here you could inspect error.response?.status and, for example,
    // trigger a global logout on 401/403 via a callback or event system.
    return Promise.reject(error);
  },
);

// ========= Types aligned with AuthContext and typical calendar APIs =========

export interface User {
  id: string;
  email: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

// Calendar / event-related types (adjust to backend schemas if needed)
export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  start: string; // ISO datetime
  end: string; // ISO datetime
  all_day?: boolean;
}

export interface CreateEventPayload {
  title: string;
  description?: string;
  start: string;
  end: string;
  all_day?: boolean;
}

export interface UpdateEventPayload {
  title?: string;
  description?: string;
  start?: string;
  end?: string;
  all_day?: boolean;
}

// ========= Low-level request helper (wraps axios and normalizes errors) =====

async function request<T = unknown>(
  config: AxiosRequestConfig,
): Promise<T> {
  try {
    const response: AxiosResponse<T> = await api.request<T>(config);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status ?? 0;
      const data = error.response?.data as
        | { detail?: string }
        | undefined;
      const message =
        data?.detail ||
        error.message ||
        "Request failed. Please try again.";
      throw new ApiError(status, message, data);
    }

    throw new ApiError(0, "Unexpected error occurred", error as unknown);
  }
}

// ====================== Auth API ============================================

export const authApi = {
  login: (credentials: LoginCredentials): Promise<AuthResponse> =>
    request<AuthResponse>({
      url: "/auth/login",
      method: "POST",
      data: credentials,
    }),

  register: (payload: RegisterPayload): Promise<AuthResponse | { id: string }> =>
    request<AuthResponse | { id: string }>({
      url: "/auth/register",
      method: "POST",
      data: payload,
    }),

  me: (): Promise<User> =>
    request<User>({
      url: "/auth/me",
      method: "GET",
    }),
};

// ====================== Calendar / Events API ===============================

export const calendarApi = {
  listEvents: (): Promise<CalendarEvent[]> =>
    request<CalendarEvent[]>({
      url: "/events",
      method: "GET",
    }),

  getEvent: (id: string): Promise<CalendarEvent> =>
    request<CalendarEvent>({
      url: `/events/${encodeURIComponent(id)}`,
      method: "GET",
    }),

  createEvent: (payload: CreateEventPayload): Promise<CalendarEvent> =>
    request<CalendarEvent>({
      url: "/events",
      method: "POST",
      data: payload,
    }),

  updateEvent: (
    id: string,
    payload: UpdateEventPayload,
  ): Promise<CalendarEvent> =>
    request<CalendarEvent>({
      url: `/events/${encodeURIComponent(id)}`,
      method: "PATCH",
      data: payload,
    }),

  deleteEvent: (id: string): Promise<void> =>
    request<void>({
      url: `/events/${encodeURIComponent(id)}`,
      method: "DELETE",
    }),
};

export { api };