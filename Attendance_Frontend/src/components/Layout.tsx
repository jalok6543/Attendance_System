import { useEffect, useState, useRef } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { LogOut, LayoutDashboard, Camera, Users, User, ChevronDown, ClipboardCheck, ClipboardList } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuthContext } from '../context/AuthContext';
import { useRealtime } from '../hooks/useRealtime';
import { dashboardApi, studentsApi, subjectsApi, teachersApi, changeRequestsApi } from '../services/api';

export function Layout() {
  const { user, logout } = useAuthContext();
  const queryClient = useQueryClient();
  useRealtime();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setProfileOpen(false);
      }
    };
    if (profileOpen) document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [profileOpen]);

  useEffect(() => {
    if (user?.role === 'admin' || user?.role === 'teacher') {
      queryClient.prefetchQuery({ queryKey: ['dashboard-stats'], queryFn: () => dashboardApi.getStats().then((r) => r.data) });
      queryClient.prefetchQuery({ queryKey: ['students'], queryFn: () => studentsApi.list().then((r) => r.data) });
      queryClient.prefetchQuery({ queryKey: ['subjects'], queryFn: () => subjectsApi.list().then((r) => r.data) });
      queryClient.prefetchQuery({ queryKey: ['teachers'], queryFn: () => teachersApi.list().then((r) => r.data) });
    }
    if (user?.role === 'admin') {
      queryClient.prefetchQuery({
        queryKey: ['change-requests-pending'],
        queryFn: () => changeRequestsApi.getPendingCount().then((r) => ({ count: (r.data as { count?: number })?.count ?? 0 })),
      });
    }
    if (user?.role === 'admin' || user?.role === 'teacher') {
      queryClient.prefetchQuery({
        queryKey: ['change-requests'],
        queryFn: () => changeRequestsApi.list().then((r) => r.data ?? []),
      });
    }
  }, [user?.role, queryClient]);
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const { data: pendingCountData } = useQuery({
    queryKey: ['change-requests-pending'],
    queryFn: async () => {
      const r = await changeRequestsApi.getPendingCount();
      const body = r.data as { count?: number };
      return { count: typeof body?.count === 'number' ? body.count : 0 };
    },
    enabled: user?.role === 'admin',
    staleTime: 20_000,
    refetchInterval: 45_000,
  });
  const pendingCount = pendingCountData?.count ?? 0;

  const navLinks = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    ...(user?.role === 'admin' || user?.role === 'teacher'
      ? [{ to: '/face-capture', icon: Camera, label: 'Attendance' }]
      : []),
    ...(user?.role === 'admin' || user?.role === 'teacher'
      ? [{ to: '/students', icon: Users, label: 'Students' }]
      : []),
    ...(user?.role === 'admin' || user?.role === 'teacher'
      ? [{ to: '/change-requests', icon: ClipboardList, label: 'Requests', badge: user?.role === 'admin' ? pendingCount : undefined }]
      : []),
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex-1 flex items-center">
              <Link to="/" className="flex items-center gap-2 text-slate-800 font-semibold">
                <ClipboardCheck className="w-6 h-6 text-primary-600" />
                Attendance System
              </Link>
            </div>
            <nav className="flex items-center justify-center gap-6 flex-1">
              {navLinks.map(({ to, icon: Icon, label, badge }) => (
                <Link
                  key={to}
                  to={to}
                  className={`relative flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-300 ease-out overflow-visible ${
                    location.pathname === to ? 'bg-primary-50 text-primary-700' : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{label}</span>
                  {typeof badge === 'number' && badge > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[20px] h-5 px-1.5 flex items-center justify-center rounded-full bg-destructive-500 text-white text-xs font-bold shadow-sm">
                      {badge > 99 ? '99+' : badge}
                    </span>
                  )}
                </Link>
              ))}
            </nav>
            <div className="flex-1 flex justify-end">
              <div className="relative" ref={profileRef}>
              <button
                onClick={() => setProfileOpen((o) => !o)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                  <User className="w-4 h-4 text-primary-600" />
                </div>
                <span className="text-sm font-medium text-slate-700">{user?.name}</span>
                <ChevronDown className={`w-4 h-4 text-slate-500 transition-transform ${profileOpen ? 'rotate-180' : ''}`} />
              </button>
              {profileOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-slate-200 shadow-lg py-2 z-20">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-sm font-medium text-slate-800">{user?.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {user?.role === 'admin' ? 'Administrator' : user?.role === 'teacher' ? 'Teacher' : user?.role}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setProfileOpen(false);
                      handleLogout();
                    }}
                    className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-left text-slate-700 hover:bg-destructive-50 hover:text-destructive-600 transition-colors"
                  >
                    <LogOut className="w-4 h-4 shrink-0" />
                    Logout
                  </button>
                </div>
              )}
              </div>
            </div>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div key={location.pathname} className="animate-page-enter">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
