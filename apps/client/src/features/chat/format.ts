import { formatAmount } from '@/features/kitchen/format';

/**
 * "2026-11-16" → "Mon 16 Nov". Built from the parts, because `new Date('2026-11-16')`
 * means midnight UTC, which is the day before for anyone west of Greenwich.
 */
export function formatDay(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (!match) return iso;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  const weekday = date.toLocaleDateString('en-AU', { weekday: 'short' });
  const month = date.toLocaleDateString('en-AU', { month: 'short' });
  return `${weekday} ${date.getDate()} ${month}`;
}

type AdditionShape = { name: string; quantity: number | null; unit: string | null };

/** "6", "1.2 kg", "1 bunch", or null when there's no amount. */
export function amountOf(item: AdditionShape): string | null {
  if (item.quantity === null) return null;
  const unit = item.unit ?? 'count';
  return unit === 'g' || unit === 'ml' || unit === 'count'
    ? formatAmount(String(item.quantity), unit) // g → kg, ml → L, count → just the number
    : `${item.quantity} ${unit}`;
}

/** "6 eggs", "1.2 kg canned tomatoes", "1 bunch coriander", or just "garlic". */
export function formatAddition(item: AdditionShape): string {
  const amount = amountOf(item);
  return amount ? `${amount} ${item.name}` : item.name;
}

/**
 * A Proposal's list addition. It's the extra on top of what's already on the list (ADR
 * 0016), so when some is there it says "4 more sausages (4 on the list)".
 */
export function additionLine(item: AdditionShape & { on_list?: string | null }): string {
  if (!item.on_list) return formatAddition(item);
  const amount = amountOf(item);
  const what = amount ? `${amount} more ${item.name}` : item.name;
  return `${what} (${item.on_list} on the list)`;
}
