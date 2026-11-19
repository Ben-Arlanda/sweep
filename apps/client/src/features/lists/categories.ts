/**
 * The Shopping List in food categories (the Kitchen's own, ADR 0024), ordered the way
 * you walk a supermarket: fresh things first, frozen near the end. Items that aren't
 * linked to an Ingredient, or have a category we don't show, go under Other.
 */
import { CATEGORIES } from '@/features/kitchen/kitchenView';

const SHOP_ORDER = [
  'produce',
  'bakery',
  'meat',
  'seafood',
  'dairy',
  'chilled',
  'pantry',
  'spices',
  'frozen',
  'drinks',
];

export type ListSection<T> = { category: string; label: string; items: T[] };

export function listSections<T extends { ingredient: { category: string } | null }>(
  items: readonly T[],
): ListSection<T>[] {
  const labels = new Map(CATEGORIES.map((c) => [c.category, c.label]));
  const sectionOf = (item: T) => {
    const category = item.ingredient?.category;
    return category && SHOP_ORDER.includes(category) ? category : 'other';
  };
  return [...SHOP_ORDER, 'other']
    .map((category) => ({
      category,
      label: labels.get(category) ?? 'Other',
      items: items.filter((item) => sectionOf(item) === category),
    }))
    .filter((section) => section.items.length > 0);
}
