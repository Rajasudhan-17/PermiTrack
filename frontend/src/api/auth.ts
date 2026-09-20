import { client, setApiToken, clearApiToken, setActiveRole, clearActiveRole } from './client';

export interface LoginResponse {
  message: string;
  token: string;
  user: {
    id: number;
    username: string;
    full_name: string;
    role: string;
  };
}

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const res = await client.post<LoginResponse>('/auth/login', { username, password });
    if (res.token) {
      setApiToken(res.token);
    }
    return res;
  },

  switchRole: async (role: string): Promise<{ message: string; active_role: string; user: any }> => {
    const res = await client.post<{ message: string; active_role: string; user: any }>('/auth/switch-role', { role });
    if (res.active_role) {
      setActiveRole(res.active_role);
    }
    return res;
  },

  logout: async (): Promise<{ message: string }> => {
    try {
      const res = await client.post<{ message: string }>('/auth/logout');
      return res;
    } finally {
      clearApiToken();
      clearActiveRole();
    }
  },

  forgotPassword: (emailOrUsername: string) =>
    client.post<{ message: string; email?: string; masked_email?: string }>('/auth/forgot-password', {
      email_or_username: emailOrUsername,
    }),

  verifyOtp: (payload: { email_or_username: string; otp: string; new_password: string }) =>
    client.post<{ message: string }>('/auth/verify-otp', payload),
};
