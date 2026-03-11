import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import { CheckCircle, XCircle } from 'lucide-react';

type ToastType = 'success' | 'error' | 'duplicate' | 'attendance_success' | 'attendance_already_marked' | 'attendance_error' | 'face_not_registered';

interface Toast {
  id: number;
  type: ToastType;
  message: string;
  subtext?: string;
}

type ToastContextType = {
  success: (message: string) => void;
  error: (message: string) => void;
  duplicateFace: (message: string) => void;
  attendanceSuccess: (studentName: string) => void;
  attendanceAlreadyMarked: (studentName: string) => void;
  attendanceError: (message: string) => void;
  faceNotRegistered: (message?: string) => void;
};

const ToastContext = createContext<ToastContextType | null>(null);

const AUTO_DISMISS_MS = 4000;
const ATTENDANCE_POPUP_MS = 3000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextIdRef = useRef(0);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const success = useCallback((message: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'success', message }]);
    setTimeout(() => removeToast(id), AUTO_DISMISS_MS);
  }, [removeToast]);

  const error = useCallback((message: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'error', message }]);
    setTimeout(() => removeToast(id), AUTO_DISMISS_MS);
  }, [removeToast]);

  const duplicateFace = useCallback((message: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'duplicate', message }]);
    setTimeout(() => removeToast(id), AUTO_DISMISS_MS);
  }, [removeToast]);

  const attendanceSuccess = useCallback((studentName: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'attendance_success', message: studentName, subtext: 'Attendance marked successfully' }]);
    setTimeout(() => removeToast(id), ATTENDANCE_POPUP_MS);
  }, [removeToast]);

  const attendanceAlreadyMarked = useCallback((studentName: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'attendance_already_marked', message: studentName, subtext: 'Attendance already marked today' }]);
    setTimeout(() => removeToast(id), ATTENDANCE_POPUP_MS);
  }, [removeToast]);

  const attendanceError = useCallback((message: string) => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'attendance_error', message }]);
    setTimeout(() => removeToast(id), ATTENDANCE_POPUP_MS);
  }, [removeToast]);

  const faceNotRegistered = useCallback((message = 'This face is not registered in our database.') => {
    const id = nextIdRef.current++;
    setToasts((prev) => [...prev, { id, type: 'face_not_registered', message }]);
    setTimeout(() => removeToast(id), ATTENDANCE_POPUP_MS);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ success, error, duplicateFace, attendanceSuccess, attendanceAlreadyMarked, attendanceError, faceNotRegistered }}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-start gap-2 px-3 py-2.5 rounded-lg shadow-md border-l-4 pointer-events-auto max-w-xs ${
                t.type === 'success'
                ? 'bg-green-50 border-green-200 border-l-green-500 text-green-800'
                : t.type === 'duplicate' || t.type === 'attendance_error' || t.type === 'face_not_registered'
                  ? 'bg-destructive-100 border-destructive-200 border-l-destructive-500 text-destructive-900'
                    : t.type === 'attendance_success'
                      ? 'bg-[#E6F9ED] border-green-200 border-l-green-500 text-green-900'
                      : t.type === 'attendance_already_marked'
                        ? 'bg-amber-100 border-amber-200 border-l-amber-500 text-amber-900'
                        : 'bg-destructive-50 border-destructive-200 border-l-destructive-500 text-destructive-800'
            }`}
          >
            {t.type === 'success' || t.type === 'attendance_success' ? (
              <CheckCircle className="w-5 h-5 flex-shrink-0 text-green-600 mt-0.5" />
            ) : t.type === 'attendance_already_marked' ? (
              <XCircle className="w-5 h-5 flex-shrink-0 text-amber-700 mt-0.5" />
            ) : t.type === 'duplicate' || t.type === 'attendance_error' || t.type === 'face_not_registered' ? (
              <XCircle className="w-5 h-5 flex-shrink-0 text-destructive-700 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 flex-shrink-0 text-destructive-600 mt-0.5" />
            )}
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="text-sm font-bold">{t.message}</span>
              {t.subtext && <span className="text-xs opacity-90">{t.subtext}</span>}
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
