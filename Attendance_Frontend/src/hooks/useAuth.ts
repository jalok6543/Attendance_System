import { useMutation } from '@tanstack/react-query';
import { authApi } from '../services/api';

export function useAuth() {
  const userStr = localStorage.getItem('user');
  const user = userStr ? JSON.parse(userStr) : null;
  const token = localStorage.getItem('token');

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.login(email, password),
    onSuccess: (res) => {
      const { access_token, user: u } = res.data;
      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(u));
    },
  });

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  };

  return {
    user,
    token,
    isAuthenticated: !!token,
    login: loginMutation.mutateAsync,
    loginLoading: loginMutation.isPending,
    logout,
  };
}
