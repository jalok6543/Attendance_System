import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuthContext } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Layout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { Dashboard } from './pages/Dashboard';
import { FaceCapturePage } from './pages/FaceCapturePage';
import { StudentsPage } from './pages/StudentsPage';
import { ChangeRequestsPage } from './pages/ChangeRequestsPage';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function AppRoutes() {
  const { isAuthenticated } = useAuthContext();

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="face-capture" element={<ProtectedRoute roles={['admin', 'teacher']}><FaceCapturePage /></ProtectedRoute>} />
        <Route
          path="students"
          element={
            <ProtectedRoute roles={['admin', 'teacher']}>
              <StudentsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="change-requests"
          element={
            <ProtectedRoute roles={['admin', 'teacher']}>
              <ChangeRequestsPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <ToastProvider>
            <AppRoutes />
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
