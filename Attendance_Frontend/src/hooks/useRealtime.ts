import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { supabase } from '../lib/supabase';

/** Map table names to React Query keys to invalidate on change. */
const TABLE_TO_QUERY_KEYS: Record<string, string[][]> = {
  students: [['students'], ['dashboard-stats']],
  teachers: [['teachers']],
  subjects: [['subjects']],
  attendance: [['attendance'], ['dashboard-stats'], ['attendance-analytics']],
  face_embeddings: [['students']],
  logs: [['logs']],
  student_change_requests: [['change-requests'], ['change-requests-pending']],
};

const REALTIME_TABLES = Object.keys(TABLE_TO_QUERY_KEYS);
const INVALIDATE_DEBOUNCE_MS = 40;

/** Fast realtime: batched invalidation, table-specific subscriptions, active-only refetch. */
export function useRealtime() {
  const queryClient = useQueryClient();
  const pendingKeysRef = useRef<Set<string>>(new Set());
  const flushRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (pendingKeysRef.current.size === 0) return;
    const keys = Array.from(pendingKeysRef.current);
    pendingKeysRef.current.clear();
    keys.forEach((key) => {
      try {
        const queryKey = JSON.parse(key) as string[];
        queryClient.invalidateQueries({ queryKey, refetchType: 'active' });
      } catch {
        /* ignore */
      }
    });
  }, [queryClient]);

  const scheduleFlush = useCallback(() => {
    if (flushRef.current) return;
    flushRef.current = setTimeout(() => {
      flushRef.current = null;
      flush();
    }, INVALIDATE_DEBOUNCE_MS);
  }, [flush]);

  useEffect(() => {
    const client = supabase;
    if (!client) return;

    const onChange = (payload: { table: string }) => {
      const keys = TABLE_TO_QUERY_KEYS[payload.table];
      if (!keys) return;
      keys.forEach((k) => pendingKeysRef.current.add(JSON.stringify(k)));
      scheduleFlush();
    };

    const channel = client.channel('realtime-attendance');
    REALTIME_TABLES.forEach((table) => {
      channel.on('postgres_changes', { event: '*', schema: 'public', table }, onChange);
    });
    channel.subscribe();

    return () => {
      if (flushRef.current) clearTimeout(flushRef.current);
      client.removeChannel(channel);
    };
  }, [scheduleFlush, flush]);
}
