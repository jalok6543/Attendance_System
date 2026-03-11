import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { changeRequestsApi } from '../services/api';
import { useAuthContext } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { getApiErrorMessage } from '../utils/apiError';
import { ClipboardList, Check, X, User } from 'lucide-react';

type ChangeRequest = {
  id: string;
  student_id: string;
  requested_by: string;
  proposed_changes: Record<string, string>;
  message?: string;
  status: string;
  created_at: string;
  students?: { id: string; name: string; email: string; roll_number: string; parent_phone: string; class: string };
  users?: { id: string; name: string; email: string };
};

export function ChangeRequestsPage() {
  const { user } = useAuthContext();
  const isAdmin = user?.role === 'admin';
  const queryClient = useQueryClient();
  const toast = useToast();
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data: requests = [], isLoading, isFetching } = useQuery({
    queryKey: ['change-requests', statusFilter],
    queryFn: async () => {
      const res = await changeRequestsApi.list(statusFilter || undefined);
      return (res.data as ChangeRequest[]) ?? [];
    },
    enabled: !!user,
    staleTime: 30_000,
    gcTime: 5 * 60 * 1000,
  });

  const updateCacheOptimistically = useCallback(
    (requestId: string, newStatus: 'approved' | 'rejected' | 'pending') => {
      queryClient.setQueriesData(
        { queryKey: ['change-requests'] },
        (old: ChangeRequest[] | undefined) =>
          (old ?? []).map((r) =>
            r.id === requestId ? { ...r, status: newStatus } : r
          )
      );
      queryClient.setQueriesData(
        { queryKey: ['change-requests', statusFilter] },
        (old: ChangeRequest[] | undefined) =>
          (old ?? []).map((r) =>
            r.id === requestId ? { ...r, status: newStatus } : r
          )
      );
      if (isAdmin) {
        queryClient.setQueriesData(
          { queryKey: ['change-requests-pending'] },
          (old: { count: number } | undefined) => ({
            count: Math.max(0, (old?.count ?? 0) - 1),
          })
        );
      }
    },
    [queryClient, statusFilter, isAdmin]
  );

  const approveMutation = useMutation({
    mutationFn: (id: string) => changeRequestsApi.approve(id),
    onMutate: async (id) => {
      updateCacheOptimistically(id, 'approved');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['change-requests'] });
      queryClient.invalidateQueries({ queryKey: ['change-requests-pending'] });
      queryClient.invalidateQueries({ queryKey: ['students'] });
      toast.success('Request approved. Student updated.');
    },
    onError: (err, requestId) => {
      updateCacheOptimistically(requestId, 'pending');
      toast.error(getApiErrorMessage(err, 'Failed to approve'));
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => changeRequestsApi.reject(id),
    onMutate: async (id) => {
      updateCacheOptimistically(id, 'rejected');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['change-requests'] });
      queryClient.invalidateQueries({ queryKey: ['change-requests-pending'] });
      toast.success('Request rejected.');
    },
    onError: (err, requestId) => {
      updateCacheOptimistically(requestId, 'pending');
      toast.error(getApiErrorMessage(err, 'Failed to reject'));
    },
  });

  const pendingInList = requests.filter((r) => r.status === 'pending').length;
  const processingId = approveMutation.isPending ? approveMutation.variables : rejectMutation.isPending ? rejectMutation.variables : null;

  return (
    <div className="w-full min-w-0">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-8">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <ClipboardList className="w-7 h-7 text-primary-600" />
            Requests
            {isFetching && !isLoading && (
              <span className="inline-block w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
            )}
          </h1>
          {isAdmin && pendingInList > 0 && (
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-sm font-medium">
              {pendingInList} pending
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <label htmlFor="requests-filter" className="text-sm font-medium text-slate-600 whitespace-nowrap">Filter:</label>
          <select
            id="requests-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="min-w-[140px] px-4 py-2.5 rounded-lg border border-slate-300 bg-white text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          >
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse">
              <div className="h-5 bg-slate-200 rounded w-1/3 mb-3" />
              <div className="h-4 bg-slate-100 rounded w-1/2 mb-4" />
              <div className="h-16 bg-slate-100 rounded" />
            </div>
          ))}
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-500">
          <ClipboardList className="w-12 h-12 mx-auto mb-4 text-slate-300" />
          <p className="font-medium">
            {isAdmin ? 'No change requests yet' : 'You have not submitted any requests'}
          </p>
          <p className="text-sm mt-1">
            {isAdmin
              ? 'When teachers request student updates, they will appear here.'
              : 'Request student updates from the Students page.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((req) => (
            <div
              key={req.id}
              className={`bg-white rounded-xl border p-6 transition-opacity ${
                req.status === 'pending' ? 'border-amber-200 bg-amber-50/30' : 'border-slate-200'
              } ${processingId === req.id ? 'opacity-70' : ''}`}
            >
              <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <User className="w-4 h-4 text-slate-500 shrink-0" />
                    <span className="font-semibold text-slate-800">
                      {(req.students as { name?: string })?.name || 'Unknown Student'}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        req.status === 'pending'
                          ? 'bg-amber-200 text-amber-800'
                          : req.status === 'approved'
                            ? 'bg-green-200 text-green-800'
                            : 'bg-destructive-200 text-destructive-800'
                      }`}
                    >
                      {req.status}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600 mb-2">
                    {isAdmin && (
                      <>
                        Requested by {(req.users as { name?: string })?.name ?? 'Teacher'} •
                        <span className="ml-1" />
                      </>
                    )}
                    <span>
                      {new Date(req.created_at).toLocaleDateString()}{' '}
                      {new Date(req.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="bg-white rounded-lg border border-slate-300 p-4 text-sm">
                    <p className="font-medium text-slate-700 mb-1">Proposed changes:</p>
                    <ul className="space-y-0.5 text-slate-600">
                      {Object.entries(req.proposed_changes || {}).map(([key, val]) => (
                        <li key={key}>
                          <span className="capitalize">{key.replace('_', ' ')}:</span>{' '}
                          <span className="font-medium text-slate-800">{val}</span>
                        </li>
                      ))}
                    </ul>
                    {req.message && (
                      <p className="mt-2 pt-2 border-t border-slate-100 text-slate-600 italic">
                        &quot;{req.message}&quot;
                      </p>
                    )}
                  </div>
                </div>
                {isAdmin && req.status === 'pending' && (
                  <div className="flex gap-3 shrink-0">
                    <button
                      onClick={() => approveMutation.mutate(req.id)}
                      disabled={!!processingId}
                      className="flex items-center gap-1.5 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {approveMutation.isPending && approveMutation.variables === req.id ? (
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                      Approve
                    </button>
                    <button
                      onClick={() => rejectMutation.mutate(req.id)}
                      disabled={!!processingId}
                      className="flex items-center gap-1.5 px-4 py-2 bg-destructive-600 text-white rounded-lg text-sm font-medium hover:bg-destructive-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {rejectMutation.isPending && rejectMutation.variables === req.id ? (
                        <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <X className="w-4 h-4" />
                      )}
                      Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
