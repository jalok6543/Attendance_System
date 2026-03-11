import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthContext } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { ClipboardCheck } from 'lucide-react';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  // Pre-wake backend on mount (Render free tier sleeps after 15 min)
  useEffect(() => {
    const origin = window.location.origin;
    const healthUrl = origin + '/health';
    fetch(healthUrl).catch(() => {});
  }, []);
  const { login, loginLoading } = useAuthContext();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login({ email, password });
      toast.success('Login successful');
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string }; status?: number }; message?: string; code?: string };
      const msg = e?.response?.data?.message || e?.message || 'Login failed';
      const isNetwork = !e?.response || e?.code === 'ERR_NETWORK' || e?.code === 'ECONNABORTED';
      const hint = isNetwork
        ? ' Backend may be starting (Render free tier). Wait 30–60 seconds and try again.'
        : '';
      setError(msg + hint);
      toast.error(msg + hint);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-xl shadow-lg border border-slate-200 p-8">
          <div className="flex justify-center mb-6">
            <div className="w-14 h-14 rounded-full bg-primary-100 flex items-center justify-center">
              <ClipboardCheck className="w-8 h-8 text-primary-600" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-center text-slate-800 mb-2">
            Attendance System
          </h1>
          <p className="text-slate-600 text-center text-sm mb-6">
            Sign in with your credentials
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-800 mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-900 placeholder:text-slate-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-800 mb-1.5">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-900 placeholder:text-slate-500 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            {error && (
              <p className="text-red-600 text-sm">{error}</p>
            )}
            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50"
            >
              {loginLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
