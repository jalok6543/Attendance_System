import axios from 'axios';

// In production, always use relative /api/v1 so Vercel proxy handles it (avoids dup paths from env)
const API_BASE = import.meta.env.PROD
  ? '/api/v1'
  : (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1');

export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000, // 60s - Render free tier needs ~30-60s to wake from sleep
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // FormData needs multipart boundary - remove json Content-Type so browser sets it
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }, { timeout: 60000 }),
  me: () => api.get('/auth/me'),
};

export const studentsApi = {
  list: (classFilter?: string) =>
    api.get('/students', { params: classFilter ? { class: classFilter } : {} }),
  get: (id: string) => api.get(`/students/${id}`),
  create: (data: {
    name: string;
    email: string;
    roll_number: string;
    parent_phone: string;
    class: string;
  }) => api.post('/students', data),
  registerWithFace: (formData: FormData) =>
    api.post('/students/register-with-face', formData, { timeout: 60000 }),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/students/${id}`, data),
  delete: (id: string) => api.delete(`/students/${id}`),
};

export const dashboardApi = {
  getStats: (reportDate?: string) =>
    api.get('/attendance/dashboard-stats', { params: reportDate ? { report_date: reportDate } : {} }),
  getLowAttendancePreview: (year?: number, month?: number) =>
    api.get('/attendance/low-attendance-preview', { params: { year, month } }),
  sendLowAttendanceAlertsBulk: (studentIds: string[], year?: number, month?: number) =>
    api.post('/attendance/send-low-attendance-alerts-bulk', { student_ids: studentIds }, { params: { year, month } }),
  getAnalyticsChart: (startDate: string, endDate: string, subjectId?: string) =>
    api.get('/attendance/analytics-chart', {
      params: { start_date: startDate, end_date: endDate, ...(subjectId ? { subject_id: subjectId } : {}) },
    }),
  getAttendanceReport: (startDate: string, endDate: string, subjectId?: string, expectedClasses?: number, threshold?: number) =>
    api.get('/attendance/attendance-report', {
      params: { start_date: startDate, end_date: endDate, ...(subjectId ? { subject_id: subjectId } : {}), ...(expectedClasses ? { expected_classes: expectedClasses } : {}), ...(threshold ? { threshold: threshold } : {}) },
    }),
  sendLowAttendanceAlerts: (year: number, month: number) =>
    api.post('/attendance/send-low-attendance-alerts', null, { params: { year, month } }),
  sendCustomAttendanceMessage: (year: number, month: number, threshold: number, message: string) =>
    api.post('/attendance/send-custom-attendance-message', { year, month, threshold, message }),
};

export const attendanceApi = {
  checkIn: (studentId: string, subjectId: string, confidenceScore: number) =>
    api.post('/attendance/check-in', {
      student_id: studentId,
      subject_id: subjectId,
      confidence_score: confidenceScore,
    }),
  checkOut: (studentId: string, subjectId: string) =>
    api.post('/attendance/check-out', null, {
      params: { student_id: studentId, subject_id: subjectId },
    }),
  getStudent: (studentId: string, params?: { subject_id?: string; start_date?: string; end_date?: string }) =>
    api.get(`/attendance/student/${studentId}`, { params }),
  getStudentDetailedReport: (studentId: string, startDate?: string, endDate?: string) =>
    api.get(`/attendance/student/${studentId}/detailed-report`, {
      params: { start_date: startDate, end_date: endDate },
    }),
  getDailyReport: (subjectId: string, reportDate: string) =>
    api.get('/attendance/daily-report', { params: { subject_id: subjectId, report_date: reportDate } }),
};

export const subjectsApi = {
  list: () => api.get('/subjects'),
  get: (id: string) => api.get(`/subjects/${id}`),
  create: (data: { name: string; teacher_id: string }) => api.post('/subjects', data),
};

export const teachersApi = {
  list: () => api.get('/teachers'),
  ensure: () => api.post('/teachers/ensure'),
};

export const changeRequestsApi = {
  list: (status?: string) =>
    api.get('/student-change-requests', { params: status ? { status } : {} }),
  getPendingCount: () => api.get('/student-change-requests/pending-count'),
  create: (data: { student_id: string; proposed_changes: Record<string, string>; message: string }) =>
    api.post('/student-change-requests', data),
  approve: (requestId: string) => api.post(`/student-change-requests/${requestId}/approve`),
  reject: (requestId: string) => api.post(`/student-change-requests/${requestId}/reject`),
};

/* Face/ML endpoints need longer timeout (processing can take 20–30s) */
const FACE_API_TIMEOUT = 30000;

export const faceApi = {
  register: (studentId: string, image: File) => {
    const form = new FormData();
    form.append('image', image);
    return api.post(`/face/register/${studentId}`, form, { timeout: FACE_API_TIMEOUT });
  },
  verify: (image: File, subjectId?: string) => {
    const form = new FormData();
    form.append('image', image);
    return api.post('/face/verify', form, {
      params: subjectId ? { subject_id: subjectId } : {},
      timeout: FACE_API_TIMEOUT,
    });
  },
  verifyMulti: (image: File) => {
    const form = new FormData();
    form.append('image', image);
    return api.post('/face/verify-multi', form, { timeout: FACE_API_TIMEOUT });
  },
  verifyMultiStable: (images: File[]) => {
    const form = new FormData();
    images.forEach((img, i) => form.append(`image${i + 1}`, img));
    return api.post('/face/verify-multi-stable', form, { timeout: FACE_API_TIMEOUT });
  },
};
