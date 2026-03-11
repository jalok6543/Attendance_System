import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuthContext } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { BarChart3, Users, Calendar, Activity, TrendingUp, Download, MessageSquare, Send } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import * as XLSX from 'xlsx';
import { dashboardApi, studentsApi, subjectsApi } from '../services/api';
import { useToast } from '../context/ToastContext';

type DashboardStats = {
  today_count: number;
  total_students: number;
  attendance_rate: number;
  active_sessions: number;
};

function formatDateForInput(d: Date) {
  return d.toISOString().slice(0, 10);
}

export function Dashboard() {
  const { user } = useAuthContext();
  const role = user?.role || 'student';
  const now = new Date();
  const defaultEnd = new Date(now);
  const defaultStart = new Date(now);
  defaultStart.setDate(defaultStart.getDate() - 6);
  const [chartStartDate, setChartStartDate] = useState(formatDateForInput(defaultStart));
  const [chartEndDate, setChartEndDate] = useState(formatDateForInput(defaultEnd));
  const [chartSubjectId, setChartSubjectId] = useState<string>('');

  const toast = useToast();
  const prevMonthNum = now.getMonth() === 0 ? 12 : now.getMonth();
  const prevYearNum = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
  const [alertYear, setAlertYear] = useState(prevYearNum);
  const [alertMonth, setAlertMonth] = useState(prevMonthNum);

  const { data: subjects = [] } = useQuery({
    queryKey: ['subjects'],
    queryFn: () => subjectsApi.list().then((r) => r.data || []),
    staleTime: 60_000,
  });

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async (): Promise<DashboardStats> => {
      try {
        const res = await dashboardApi.getStats();
        return res.data as DashboardStats;
      } catch {
        try {
          const studentsRes = await studentsApi.list();
          const students = (studentsRes.data as unknown[]) ?? [];
          return {
            today_count: 0,
            total_students: students.length,
            attendance_rate: 0,
            active_sessions: 0,
          };
        } catch {
          return { today_count: 0, total_students: 0, attendance_rate: 0, active_sessions: 0 };
        }
      }
    },
    staleTime: 20_000,
    refetchInterval: 60_000,
  });

  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['attendance-analytics', chartStartDate, chartEndDate, chartSubjectId || null],
    queryFn: async () => {
      try {
        const res = await dashboardApi.getAnalyticsChart(
          chartStartDate,
          chartEndDate,
          chartSubjectId || undefined
        );
        return res.data as { data: { name: string; label: string; present: number; absent: number }[] };
      } catch {
        return { data: [] };
      }
    },
    staleTime: 20_000,
    refetchInterval: 60_000,
  });

  const previewMutation = useMutation({
    mutationFn: () =>
      dashboardApi.getLowAttendancePreview(alertYear, alertMonth).then((r) => r.data as {
        low_attendance: { student_id: string; student_name: string; percentage: number; has_phone: boolean }[];
        low_attendance_count: number;
        month: number;
        year: number;
      }),
    onError: () => toast.error('Failed to fetch low attendance list'),
  });

  const sendAlertsMutation = useMutation({
    mutationFn: () => {
      const preview = previewMutation.data;
      if (
        preview &&
        preview.low_attendance_count > 0 &&
        preview.low_attendance.filter((s) => s.has_phone).length > 0 &&
        !window.confirm(
          `Send SMS to ${preview.low_attendance.filter((s) => s.has_phone).length} parents?`
        )
      ) {
        return Promise.reject(new Error('Cancelled'));
      }
      return dashboardApi.sendLowAttendanceAlerts(alertYear, alertMonth).then((r) => r.data as {
        sent: number;
        low_attendance_count: number;
        low_attendance: { student_name: string; percentage: number }[];
      });
    },
    onSuccess: (data) => {
      if (data.sent > 0) {
        toast.success(`Sent ${data.sent} SMS to parents`);
      } else if (data.low_attendance_count === 0) {
        toast.success('No students with low attendance for this month');
      } else {
        toast.error('SMS sending failed. Check Fast2SMS configuration.');
      }
    },
    onError: (err) => {
      if ((err as Error)?.message !== 'Cancelled') toast.error('Failed to send SMS alerts');
    },
  });

  const handleExportExcel = async () => {
    try {
      const res = await dashboardApi.getAttendanceReport(
        chartStartDate,
        chartEndDate,
        chartSubjectId || undefined
      );
      const data = (res.data as { roll_no: string; student_name: string; class: string; subject: string; total_classes: number; present: number; absent: number; attendance_percent: string; status: string }[]) ?? [];
      const rows = data.length > 0
        ? data.map((row) => ({
            'Roll No': row.roll_no,
            'Student Name': row.student_name,
            Class: row.class,
            Subject: row.subject,
            'Total Classes': row.total_classes,
            Present: row.present,
            Absent: row.absent,
            'Attendance %': row.attendance_percent,
            Status: row.status,
          }))
        : [{ 'Roll No': '', 'Student Name': '', Class: '', Subject: '', 'Total Classes': '', Present: '', Absent: '', 'Attendance %': '', Status: '' }];
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Attendance Report');
      const filename = `attendance_report_${chartStartDate}_to_${chartEndDate}.xlsx`;
      XLSX.writeFile(wb, filename);
    } catch {
      // Fallback to chart data if report API fails
      const data = chartData?.data ?? [];
      if (data.length === 0) return;
      const rows = data.map((row) => ({
        Date: row.label,
        Day: row.name,
        Present: row.present,
        Absent: row.absent,
      }));
      const ws = XLSX.utils.json_to_sheet(rows);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, 'Attendance');
      XLSX.writeFile(wb, `attendance_${chartStartDate}_to_${chartEndDate}.xlsx`);
    }
  };

  return (
    <div className="w-full">
      <h1 className="text-2xl font-bold text-slate-800 mb-6">
        Welcome, {user?.name}
      </h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Today's Attendance"
          value={isLoading ? '…' : String(stats?.today_count ?? '—')}
          icon={<Calendar className="w-6 h-6" />}
        />
        <StatCard
          title="Total Students"
          value={isLoading ? '…' : String(stats?.total_students ?? '—')}
          icon={<Users className="w-6 h-6" />}
        />
        <StatCard
          title="Attendance Rate"
          value={isLoading ? '…' : stats != null ? `${stats.attendance_rate}%` : '—'}
          icon={<BarChart3 className="w-6 h-6" />}
        />
        <StatCard
          title="Active Sessions"
          value={isLoading ? '…' : String(stats?.active_sessions ?? '—')}
          icon={<Activity className="w-6 h-6" />}
        />
      </div>
      <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2 shrink-0">
            <TrendingUp className="w-5 h-5 text-primary-600 shrink-0" />
            Attendance Analytics
          </h2>
          <div className="flex flex-wrap items-center gap-3 min-w-0">
            <div className="relative z-10 flex items-center gap-3">
              <span className="text-sm font-medium text-slate-600 hidden sm:inline">Subject</span>
              <select
                value={chartSubjectId}
                onChange={(e) => setChartSubjectId(e.target.value)}
                className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All Subjects</option>
                {(subjects as { id: string; name: string }[]).map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <Calendar className="w-4 h-4 text-slate-500" />
              <span className="text-sm font-medium text-slate-600 hidden sm:inline">From</span>
              <input
                type="date"
                value={chartStartDate}
                onChange={(e) => setChartStartDate(e.target.value)}
                className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <span className="text-slate-400">to</span>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-slate-600 hidden sm:inline">To</span>
              <input
                type="date"
                value={chartEndDate}
                onChange={(e) => setChartEndDate(e.target.value)}
                className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-300 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <button
              onClick={handleExportExcel}
              className="flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-emerald-600 text-white hover:bg-emerald-700 hover:opacity-90 transition-colors shrink-0"
            >
              <Download className="w-4 h-4" />
              Export to Excel
            </button>
          </div>
        </div>
        <div className="h-[320px] min-w-0 w-full">
          {chartLoading ? (
            <div className="flex items-center justify-center h-full text-slate-500">Loading chart…</div>
          ) : chartData?.data?.length ? (
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
              <AreaChart data={chartData.data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="presentArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.6} />
                    <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.08} />
                  </linearGradient>
                  <linearGradient id="absentArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#7dd3fc" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#bae6fd" stopOpacity={0.06} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={12} tickLine={false} axisLine={{ stroke: '#e2e8f0' }} />
                <YAxis stroke="#64748b" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    borderRadius: '10px',
                    border: '1px solid #e2e8f0',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    background: '#fff',
                  }}
                  labelFormatter={(_, payloads) => {
                    const p = Array.isArray(payloads) ? payloads[0] : null;
                    return (p as { payload?: { label?: string } } | null)?.payload?.label ?? '';
                  }}
                />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="absent"
                  stackId="1"
                  stroke="#7dd3fc"
                  fill="url(#absentArea)"
                  name="Absent"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="present"
                  stackId="1"
                  stroke="#0284c7"
                  fill="url(#presentArea)"
                  name="Present"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-slate-500">
              No attendance data for this period
            </div>
          )}
        </div>
      </div>
      <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-4">Quick Actions</h2>
        <div className="flex flex-wrap items-center gap-3">
          {(role === 'teacher' || role === 'admin') && (
            <>
              <Link to="/face-capture" className="inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                Mark Attendance
              </Link>
              <Link to="/students" className="inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium bg-slate-200 text-slate-800 rounded-lg hover:bg-slate-300">
                Manage Students
              </Link>
            </>
          )}
        </div>
      </div>

      {(role === 'teacher' || role === 'admin') && (
        <div className="mt-8 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5 text-primary-600" />
            Low Attendance SMS Alerts
          </h2>
          <p className="text-sm text-slate-600 mb-4">
            Send SMS to parents of students with attendance below 60% for a selected month.
          </p>
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Month</label>
              <select
                value={alertMonth}
                onChange={(e) => setAlertMonth(Number(e.target.value))}
                className="px-3 py-2 rounded-lg text-sm border border-slate-300 bg-white text-slate-800"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((m) => (
                  <option key={m} value={m}>
                    {new Date(2000, m - 1).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-slate-700">Year</label>
              <select
                value={alertYear}
                onChange={(e) => setAlertYear(Number(e.target.value))}
                className="px-3 py-2 rounded-lg text-sm border border-slate-300 bg-white text-slate-800"
              >
                {[now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
            <button
              type="button"
              onClick={() => previewMutation.mutate()}
              disabled={previewMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {previewMutation.isPending ? 'Loading…' : 'Preview'}
            </button>
            <button
              type="button"
              onClick={() => sendAlertsMutation.mutate()}
              disabled={sendAlertsMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-amber-600 text-white rounded-lg hover:bg-amber-700 disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              {sendAlertsMutation.isPending ? 'Sending…' : 'Send SMS to Parents'}
            </button>
          </div>
          {previewMutation.data && (
            <div className="mt-4 rounded-lg border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 px-4 py-2 text-sm font-medium text-slate-700">
                {previewMutation.data.low_attendance_count} students with low attendance ({previewMutation.data.low_attendance.filter((s) => s.has_phone).length} have valid phone)
              </div>
              <ul className="divide-y divide-slate-100 max-h-48 overflow-y-auto">
                {previewMutation.data.low_attendance.map((s) => (
                  <li key={s.student_id} className="px-4 py-2 flex justify-between text-sm">
                    <span className="text-slate-800">{s.student_name}</span>
                    <span className={s.percentage < 40 ? 'text-red-600 font-medium' : 'text-amber-700'}>
                      {s.percentage}%
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {sendAlertsMutation.data && sendAlertsMutation.data.sent > 0 && (
            <p className="mt-3 text-sm text-green-600 font-medium">
              Sent {sendAlertsMutation.data.sent} SMS successfully.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 flex items-center gap-4">
      <div className="p-2 bg-primary-100 rounded-lg text-primary-600 shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-sm text-slate-500">{title}</p>
        <p className="text-2xl font-bold text-slate-800 mt-0.5">{value}</p>
      </div>
    </div>
  );
}
