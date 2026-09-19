const API_BASE = '/api';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    credentials: 'include', // sends and receives HTTP-only cookies
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok || data.success === false) {
    const error: ApiError = data.error || {
      code: 'REQUEST_FAILED',
      message: data.message || `Request failed with status ${response.status}`,
    };
    const err = new Error(error.message);
    (err as any).code = error.code;
    (err as any).details = error.details;
    throw err;
  }

  return data as T;
}
