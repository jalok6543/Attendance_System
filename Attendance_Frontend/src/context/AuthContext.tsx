import { createContext, useContext, useEffect, useRef, type ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

const IDLE_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

type AuthContextType = ReturnType<typeof useAuth>;

const AuthContext = createContext<AuthContextType | null>(null);

function useIdleLogout(logout: () => void, isActive: boolean) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoutRef = useRef(logout);
  logoutRef.current = logout;

  useEffect(() => {
    if (!isActive) {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    const resetTimer = () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => logoutRef.current(), IDLE_TIMEOUT_MS);
    };

    resetTimer();

    const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart'];
    events.forEach((e) => window.addEventListener(e, resetTimer));
    return () => {
      events.forEach((e) => window.removeEventListener(e, resetTimer));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isActive]);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  useIdleLogout(auth.logout, auth.isAuthenticated);
  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}
