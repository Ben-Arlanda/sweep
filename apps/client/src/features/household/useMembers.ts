import { useMemo } from 'react';

import type { MemberOut } from '@/lib/api/client';
import { useHousehold } from '@/lib/api/households';

/** The Household's Members, plus a quick lookup by id (for "who added / who ticked this"). */
export function useMembers() {
  const household = useHousehold(true);
  const data = household.data?.members;
  return useMemo(() => {
    const members = data ?? [];
    const byId = new Map<string, MemberOut>(members.map((m) => [m.id, m]));
    return { members, byId };
  }, [data]);
}
