/**
 * Live updates: keep one WebSocket open to the API while signed in to a Household.
 *
 * The server never sends data down this socket, only "list X is now at version N"
 * (ADR 0004). We respond by refetching through the normal REST API, which runs the
 * usual permission checks. So the socket only makes the app faster to notice changes.
 * If it's down, the app still works, just staler (TanStack also refetches on focus).
 *
 * Lifecycle:
 *   connect ─► send {type:"auth", token} ─► "subscribed" ─► refetch (covers the gap)
 *          ─► "changed" ─► refetch that list if our copy is older
 *          ─► "resync"  ─► refetch everything (we missed something)
 *   closed ─► reconnect with growing delays (1s, 2s, 4s … 30s), unless the server said
 *            we're not allowed (4401/4403), or the app went to the background.
 */
import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { AppState } from 'react-native';

import { isNewer } from '@/features/lists/listCache';
import { cabinetKeys } from '@/lib/api/cabinet';
import { getToken, type ListDetail } from '@/lib/api/client';
import { listKeys } from '@/lib/api/lists';
import { API_URL } from '@/lib/config';

const WS_URL = `${API_URL.replace(/^http/, 'ws')}/ws`; // http→ws, https→wss
const CLOSE_UNAUTHORISED = 4401;
const CLOSE_NO_HOUSEHOLD = 4403;

type Notice =
  | { type: 'subscribed' }
  | { type: 'resync' }
  | { type: 'changed'; entity: string; id: string; version: number };

type CabinetCache = { version: number };

export function useChangeNotices(enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled) return;

    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let delay = 1000;
    let stopped = false;

    const refetchAll = () => {
      void queryClient.invalidateQueries({ queryKey: listKeys.all });
      void queryClient.invalidateQueries({ queryKey: cabinetKeys.all });
    };

    function handle(notice: Notice) {
      if (notice.type === 'subscribed' || notice.type === 'resync') {
        delay = 1000;
        refetchAll();
        return;
      }
      if (notice.type !== 'changed') return;
      if (notice.entity === 'cabinet') {
        const cached = queryClient.getQueryData<CabinetCache>(cabinetKeys.all);
        if (!cached || notice.version > cached.version) {
          void queryClient.invalidateQueries({ queryKey: cabinetKeys.all });
        }
        return;
      }
      if (notice.entity !== 'shopping_list') return;
      // Our own queued changes will refetch when they finish (see `settle`). Refetching
      // now could briefly show the list without the ones still on their way.
      if (queryClient.isMutating({ mutationKey: listKeys.all }) > 0) return;
      void queryClient.invalidateQueries({ queryKey: listKeys.summaries });
      const cached = queryClient.getQueryData<ListDetail>(listKeys.detail(notice.id));
      if (isNewer(notice.version, cached)) {
        void queryClient.invalidateQueries({
          queryKey: listKeys.detail(notice.id),
        });
      }
    }

    function connect() {
      if (stopped) return;
      const ws = new WebSocket(WS_URL);
      socket = ws;
      ws.onopen = async () => {
        const token = await getToken();
        if (token) ws.send(JSON.stringify({ type: 'auth', token }));
        else ws.close();
      };
      ws.onmessage = (event) => {
        try {
          handle(JSON.parse(String(event.data)) as Notice);
        } catch {
          // Ignore anything we don't understand.
        }
      };
      ws.onclose = (event) => {
        if (socket !== ws) return;
        socket = null;
        if (stopped) return;
        if (event.code === CLOSE_NO_HOUSEHOLD) {
          // Removed from the Household elsewhere: let the app find out and re-route.
          void queryClient.invalidateQueries();
          return;
        }
        // 4401 usually means the token expired between fetching and sending. Retry,
        // just more slowly.
        if (event.code === CLOSE_UNAUTHORISED) delay = Math.max(delay, 5000);
        retryTimer = setTimeout(connect, delay);
        delay = Math.min(delay * 2, 30_000);
      };
    }

    function disconnect() {
      clearTimeout(retryTimer);
      const ws = socket;
      socket = null;
      ws?.close();
    }

    // Phones suspend background apps. Close the socket while away; reconnect (and
    // refetch on "subscribed") when the app comes back.
    const appState = AppState.addEventListener('change', (state) => {
      if (state === 'active' && !socket) {
        delay = 1000;
        connect();
      } else if (state === 'background') {
        disconnect();
      }
    });

    connect();
    return () => {
      stopped = true;
      appState.remove();
      disconnect();
    };
  }, [enabled, queryClient]);
}
