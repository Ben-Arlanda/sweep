import {
  Archive,
  Beef,
  Camera,
  Check,
  ChevronUp,
  Container,
  CupSoda,
  Croissant,
  Ellipsis,
  Fish,
  Leaf,
  Milk,
  Package,
  Pencil,
  Refrigerator,
  Salad,
  Search,
  ShoppingCart,
  Snowflake,
  Sparkles,
  Tag,
  Trash2,
  TriangleAlert,
  CircleX,
  ChevronRight,
  ChevronDown,
  GlassWater,
  Layers,
  Weight,
  X,
  type LucideIcon,
} from 'lucide-react-native';
import { useRef, useState } from 'react';
import {
  Pressable,
  Switch,
  TextInput,
  useWindowDimensions,
  View,
  type HostInstance,
} from 'react-native';

import { FoodThumb } from '@/components/FoodThumb';
import { Icon } from '@/components/Icon';
import { measureAnchor, Popover, type Anchor } from '@/components/Popover';
import { Sheet } from '@/components/Sheet';
import { useToast } from '@/components/Toast';
import { Button, ErrorText, Loading, Screen, TAB_ROOT, Text } from '@/components/ui';
import { AddFromPhotoSheet } from '@/features/kitchen/AddFromPhotoSheet';
import {
  allowedKinds,
  editable,
  KINDS,
  kindOf,
  quickPicks,
  UNITS,
  unitLabel,
  type Kind,
  type Unit,
} from '@/features/kitchen/amount';
import { newIngredientName } from '@/features/kitchen/addNew';
import { displayName } from '@/features/kitchen/format';
import {
  afterStockChange,
  sections as toSections,
  STOCK_LABEL,
  STOCK_ORDER,
  summary,
  toRows,
  type KitchenRow,
  type Stock,
  type Tab,
} from '@/features/kitchen/kitchenView';
import { onListIds } from '@/features/kitchen/onList';
import { usePlaceFilter } from '@/features/kitchen/placeFilter';
import { PLACES, type Place, type PlaceFilter } from '@/features/kitchen/places';
import { useIngredientSearch, useKitchen, useKitchenActions } from '@/lib/api/kitchen';
import { useList } from '@/lib/api/lists';
import { ingredientEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme, type Theme } from '@/theme/useTheme';

type Actions = ReturnType<typeof useKitchenActions>;

const PLACE_ICON: Record<Place, LucideIcon> = {
  fridge: Refrigerator,
  freezer: Snowflake,
  cupboard: Archive,
};

const CATEGORY_ICON: Record<string, LucideIcon> = {
  spices: Sparkles,
  pantry: Package,
  bakery: Croissant,
  produce: Salad,
  dairy: Milk,
  chilled: Refrigerator,
  meat: Beef,
  seafood: Fish,
  frozen: Snowflake,
  drinks: CupSoda,
};

const placeLabel = (place: Place) => PLACES.find((p) => p.place === place)?.label ?? place;

/**
 * What the Household has at home (ADR 0024). Staples and Non-staples on two tabs,
 * grouped by category. Each item has a status the Member sets from its badge: a Staple
 * that runs out goes on the Shopping List at once (Undo), a Non-staple only asks.
 */
export default function KitchenScreen() {
  const t = useTheme();
  const toast = useToast();
  const kitchen = useKitchen();
  const actions = useKitchenActions();
  const list = useList();
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<Tab>('staples');
  const [place, setPlace] = usePlaceFilter();
  const [stockFilter, setStockFilter] = useState<Stock | null>(null);
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  const [photoSheet, setPhotoSheet] = useState(false);
  const [popover, setPopover] = useState<{
    id: string;
    kind: 'status' | 'menu';
    anchor: Anchor;
  } | null>(null);
  const [sheet, setSheet] = useState<string | null>(null);
  // "Add to list" was tapped: the list learns it only when the server answers.
  const [added, setAdded] = useState<Set<string>>(() => new Set());

  if (kitchen.isPending) return <Loading />;
  if (kitchen.isError) {
    return (
      <Screen edges={TAB_ROOT}>
        <ErrorText message={kitchen.error.message} />
        <Button title="Try again" onPress={() => kitchen.refetch()} />
      </Screen>
    );
  }

  const rows = toRows(kitchen.data);
  const sum = summary(rows);
  const shown = toSections(rows, { tab, place, stock: stockFilter });
  const known = new Set(rows.map((r) => r.id));
  const onList = onListIds(list.data?.items);
  const isOnList = (r: KitchenRow) => onList.has(r.id) || added.has(r.id);
  const byId = (id: string | null) => rows.find((r) => r.id === id);

  async function addToList(row: KitchenRow) {
    setAdded((ids) => new Set(ids).add(row.id));
    try {
      const out = await actions.toList(row.id);
      toast({
        kind: 'undo',
        text: out.list_item_id ? 'Added to shopping list' : 'Already on your shopping list',
        detail: row.name,
        onUndo: () => {
          setAdded((ids) => {
            const next = new Set(ids);
            next.delete(row.id);
            return next;
          });
          if (out.list_item_id) actions.unlist(out.list_id, out.list_item_id);
        },
      });
    } catch {
      // actions.error shows the server's message
    }
  }

  async function changeStock(row: KitchenRow, next: Stock) {
    if (next === row.stock) return;
    const effect = afterStockChange(row, next);
    try {
      const out = await actions.setStock(row.id, next);
      if (effect === 'addedToList') {
        toast({
          kind: 'undo',
          text: out.list_item_id ? 'Added to shopping list' : 'Already on your shopping list',
          detail: `${row.name} (Staple)`,
          onUndo: () => {
            actions.setStock(row.id, row.stock);
            if (out.list_id && out.list_item_id) actions.unlist(out.list_id, out.list_item_id);
          },
        });
      } else if (effect === 'askToAdd' && !isOnList(row)) {
        toast({
          kind: 'ask',
          text: `Add ${row.name.toLowerCase()} to your shopping list?`,
          emoji: ingredientEmoji(row.ingredient),
          tint: tintFor(row.ingredient.name),
          actionLabel: 'Add to list',
          onAction: () => void addToList(row),
        });
      }
    } catch {
      // actions.error shows the server's message
    }
  }

  function moveKind(row: KitchenRow) {
    if (row.staple) {
      actions.notAStaple(row.id);
      actions.setAmount(row.id, row.quantity); // keeps its amount (null: "some")
      actions.setPlace(row.id, row.place);
    } else {
      actions.setStaple(row.id, row.stock !== 'out');
    }
    toast({
      kind: 'undo',
      text: `Moved to ${row.staple ? 'Non-staples' : 'Staples'}`,
      detail: row.name,
      onUndo: () => (row.staple ? actions.setStaple(row.id, true) : undoToTracked(actions, row)),
    });
  }

  function remove(row: KitchenRow) {
    if (row.staple) actions.notAStaple(row.id);
    else actions.remove(row.id);
    toast({
      kind: 'undo',
      text: 'Removed from Kitchen',
      detail: row.name,
      onUndo: () => {
        if (row.staple) {
          actions.setStaple(row.id, true);
          actions.setPlace(row.id, row.place);
          if (row.quantity) actions.setStapleAmount(row.id, row.quantity);
          if (row.stock !== 'in_stock') void actions.setStock(row.id, row.stock);
        } else undoToTracked(actions, row);
      },
    });
  }

  const popRow = byId(popover?.id ?? null);
  const sheetRow = byId(sheet);

  return (
    <Screen edges={TAB_ROOT}>
      <View style={{ gap: t.space.xs }}>
        <Text variant="display" accessibilityRole="header">
          Kitchen
        </Text>
        <Text muted>
          {sum.total} items · {sum.low} low · {sum.out} out
        </Text>
      </View>

      <View style={{ flexDirection: 'row', gap: t.space.sm }}>
        {STOCK_ORDER.map((stock) => (
          <SummaryTile
            key={stock}
            stock={stock}
            count={sum[stock]}
            on={stockFilter === stock}
            onPress={() => setStockFilter(stockFilter === stock ? null : stock)}
          />
        ))}
      </View>

      <View style={{ flexDirection: 'row', gap: t.space.sm, alignItems: 'stretch' }}>
        <View
          style={{
            flex: 1,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.sm,
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.pill,
            paddingHorizontal: t.space.lg,
            minHeight: 52,
            boxShadow: t.shadow.card,
          }}
        >
          <Icon icon={Search} size={20} color={t.colors.text} />
          <TextInput
            accessibilityLabel="Add to Kitchen"
            placeholder="Add to Kitchen, e.g. olive oil"
            placeholderTextColor={t.colors.textMuted}
            value={query}
            onChangeText={setQuery}
            autoCorrect={false}
            style={[t.type.body, { flex: 1, color: t.colors.text, minHeight: 44 }]}
          />
        </View>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Add from photo"
          onPress={() => setPhotoSheet(true)}
          style={({ pressed }) => ({
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.sm,
            paddingHorizontal: t.space.md,
            borderRadius: t.radius.lg,
            backgroundColor: pressed ? t.colors.actionPressed : t.colors.action,
          })}
        >
          <Icon icon={Camera} color={t.colors.onAction} />
          <Text variant="label" style={{ color: t.colors.onAction, lineHeight: 17 }}>
            {'Add from\nphoto'}
          </Text>
        </Pressable>
      </View>

      <AddMatches
        query={query}
        known={known}
        onAdd={(id) => {
          actions.setAmount(id, null);
          setQuery('');
        }}
        onAddNew={(name) => {
          actions.addNew(name);
          setQuery('');
        }}
      />
      <ErrorText message={actions.error?.message} />

      <View
        accessibilityRole="tablist"
        style={{
          flexDirection: 'row',
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.pill,
          padding: 4,
          boxShadow: t.shadow.card,
        }}
      >
        <TabButton
          label={`Staples (${rows.filter((r) => r.staple).length})`}
          icon={Container}
          on={tab === 'staples'}
          onPress={() => setTab('staples')}
        />
        <TabButton
          label={`Non-staples (${rows.filter((r) => !r.staple).length})`}
          icon={Leaf}
          on={tab === 'non-staples'}
          onPress={() => setTab('non-staples')}
        />
      </View>

      <View
        accessibilityRole="radiogroup"
        accessibilityLabel="Where"
        style={{ flexDirection: 'row', gap: 6 }}
      >
        <PlaceChip label="All" on={place === 'all'} onPress={() => setPlace('all')} narrow />
        {PLACES.map((p) => (
          <PlaceChip
            key={p.place}
            label={p.label}
            icon={PLACE_ICON[p.place]}
            on={place === p.place}
            onPress={() => setPlace(p.place as PlaceFilter)}
          />
        ))}
      </View>

      {shown.length === 0 ? (
        <Text muted>
          {rows.length === 0
            ? 'Nothing in your Kitchen yet.'
            : 'Nothing here. Try another tab or filter.'}
        </Text>
      ) : null}

      {shown.map((section) => {
        const open = !closed.has(section.category);
        return (
          <View
            key={section.category}
            style={{
              backgroundColor: t.colors.surface,
              borderRadius: t.radius.lg,
              boxShadow: t.shadow.card,
            }}
          >
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ expanded: open }}
              accessibilityLabel={`${section.label}, ${section.rows.length} items`}
              onPress={() =>
                setClosed((now) => {
                  const next = new Set(now);
                  if (open) next.add(section.category);
                  else next.delete(section.category);
                  return next;
                })
              }
              style={{
                flexDirection: 'row',
                alignItems: 'center',
                gap: t.space.sm,
                paddingHorizontal: t.space.lg,
                minHeight: 56,
              }}
            >
              <Icon icon={CATEGORY_ICON[section.category] ?? Package} color={t.colors.text} />
              <Text variant="heading" accessibilityRole="header" style={{ fontSize: 18 }}>
                {section.label}
              </Text>
              <Text variant="caption" muted style={{ flex: 1 }}>
                {section.rows.length} items
              </Text>
              <View style={{ transform: [{ rotate: open ? '0deg' : '180deg' }] }}>
                <Icon icon={ChevronUp} size={20} color={t.colors.text} strong />
              </View>
            </Pressable>
            {open
              ? section.rows.map((row) => (
                  <ItemRow
                    key={row.id}
                    row={row}
                    onList={isOnList(row)}
                    onStatus={(anchor) => setPopover({ id: row.id, kind: 'status', anchor })}
                    onMenu={(anchor) => setPopover({ id: row.id, kind: 'menu', anchor })}
                    onOpen={() => setSheet(row.id)}
                    onAdd={() => void addToList(row)}
                  />
                ))
              : null}
          </View>
        );
      })}

      {popover?.kind === 'status' && popRow ? (
        <Popover
          anchor={popover.anchor}
          label={`Update stock status for ${popRow.name}`}
          onClose={() => setPopover(null)}
        >
          <StatusPicker
            row={popRow}
            onPick={(stock) => {
              setPopover(null);
              void changeStock(popRow, stock);
            }}
          />
        </Popover>
      ) : null}
      {popover?.kind === 'menu' && popRow ? (
        <Popover
          anchor={popover.anchor}
          label={`${popRow.name} options`}
          width={250}
          onClose={() => setPopover(null)}
        >
          <ItemMenu
            row={popRow}
            onEdit={() => {
              setPopover(null);
              setSheet(popRow.id);
            }}
            onMove={() => {
              setPopover(null);
              moveKind(popRow);
            }}
            onRemove={() => {
              setPopover(null);
              remove(popRow);
            }}
          />
        </Popover>
      ) : null}
      {sheetRow ? (
        <ItemSheet
          row={sheetRow}
          actions={actions}
          onStock={(stock) => void changeStock(sheetRow, stock)}
          onClose={() => setSheet(null)}
        />
      ) : null}
      {photoSheet ? (
        <AddFromPhotoSheet
          start={place === 'all' ? 'fridge' : place}
          onClose={() => setPhotoSheet(false)}
        />
      ) : null}
    </Screen>
  );
}

/** Undo for a Non-staple that left: put back its amount, Place and status. */
function undoToTracked(actions: Actions, row: KitchenRow) {
  actions.setAmount(row.id, row.quantity);
  actions.setPlace(row.id, row.place);
  if (row.stock !== 'in_stock') void actions.setStock(row.id, row.stock);
}

function SummaryTile({
  stock,
  count,
  on,
  onPress,
}: {
  stock: Stock;
  count: number;
  on: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const c = t.stock[stock];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
      accessibilityLabel={`${count} ${STOCK_LABEL[stock]}${on ? ', showing only these' : ''}`}
      onPress={onPress}
      style={({ pressed }) => ({
        flex: 1,
        alignItems: 'center',
        gap: 2,
        paddingVertical: t.space.md,
        borderRadius: t.radius.lg,
        backgroundColor: c.tile,
        borderWidth: 2,
        borderColor: on ? c.icon : 'transparent',
        opacity: pressed ? 0.8 : 1,
      })}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
        <StockIcon stock={stock} size={22} />
        <Text variant="title" style={{ fontSize: 24, lineHeight: 30 }}>
          {count}
        </Text>
      </View>
      <Text variant="caption">{STOCK_LABEL[stock]}</Text>
    </Pressable>
  );
}

/** Filled circle with a tick (In stock), outlined warning (Running low), outlined cross (Out). */
function StockIcon({ stock, size = 18 }: { stock: Stock; size?: number }) {
  const t = useTheme();
  const c = t.stock[stock];
  if (stock === 'in_stock') {
    return (
      <View
        aria-hidden
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: c.icon,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon icon={Check} size={size * 0.62} color={t.colors.surface} strong />
      </View>
    );
  }
  return <Icon icon={stock === 'low' ? TriangleAlert : CircleX} size={size} color={c.icon} />;
}

function TabButton({
  label,
  icon,
  on,
  onPress,
}: {
  label: string;
  icon: LucideIcon;
  on: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const fg = on ? t.colors.onInverse : t.colors.text;
  return (
    <Pressable
      accessibilityRole="tab"
      accessibilityState={{ selected: on }}
      onPress={onPress}
      style={{
        flex: 1,
        minHeight: 46,
        borderRadius: t.radius.pill,
        backgroundColor: on ? t.colors.inverse : 'transparent',
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: t.space.sm,
      }}
    >
      <Icon icon={icon} size={20} color={fg} />
      <Text variant="label" style={{ color: fg, fontSize: 16 }}>
        {label}
      </Text>
    </Pressable>
  );
}

function PlaceChip({
  label,
  icon,
  on,
  narrow,
  onPress,
}: {
  label: string;
  icon?: LucideIcon;
  on: boolean;
  narrow?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="radio"
      accessibilityState={{ checked: on }}
      onPress={onPress}
      style={({ pressed }) => ({
        flex: narrow ? undefined : 1,
        minWidth: narrow ? 56 : undefined,
        minHeight: t.touchTarget,
        paddingHorizontal: t.space.sm,
        borderRadius: t.radius.pill,
        borderWidth: 1.5,
        borderColor: on ? t.colors.action : t.colors.border,
        backgroundColor: on ? t.colors.action : t.colors.surface,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 5,
        opacity: pressed ? 0.8 : 1,
      })}
    >
      {icon ? <Icon icon={icon} size={16} color={on ? t.colors.onAction : t.colors.text} /> : null}
      <Text variant="label" style={{ color: on ? t.colors.onAction : t.colors.text }}>
        {label}
      </Text>
    </Pressable>
  );
}

function StockBadge({ stock }: { stock: Stock }) {
  const t = useTheme();
  const c = t.stock[stock];
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingLeft: 5,
        paddingRight: 8,
        minHeight: 24,
        borderRadius: t.radius.pill,
        backgroundColor: c.bg,
      }}
    >
      <StockIcon stock={stock} size={14} />
      <Text variant="label" style={{ color: c.fg, fontSize: 12, lineHeight: 16 }}>
        {STOCK_LABEL[stock]}
      </Text>
    </View>
  );
}

/**
 * One item: picture, name, "Staple · Cupboard", and its status badge (tap to change).
 * The status carries the decision; an amount, if noted (via ⋯), joins the subtitle.
 * On the right: an Out Non-staple offers Add to list; an Out Staple went on the list by
 * itself, so it shows "On list", never a button. Then ⋯.
 */
function ItemRow({
  row,
  onList,
  onStatus,
  onMenu,
  onOpen,
  onAdd,
}: {
  row: KitchenRow;
  onList: boolean;
  onStatus: (anchor: Anchor) => void;
  onMenu: (anchor: Anchor) => void;
  onOpen: () => void;
  onAdd: () => void;
}) {
  const t = useTheme();
  // Narrow phones (iPhone SE and mini): smaller picture, tighter gaps.
  const compact = useWindowDimensions().width < 390;
  const gap = compact ? t.space.sm : t.space.md;
  const badge = useRef<HostInstance>(null);
  const more = useRef<HostInstance>(null);
  const out = row.stock === 'out';
  // Amounts are optional detail (added via ⋯): shown only when one is noted.
  const noted = row.quantity ? row.amount : null;
  // Out Staples went on the list by themselves: "On list" replaces the amount, no button.
  const stapleOnList = out && row.staple && onList;
  const offerList = out && !row.staple;
  const onListChip = (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        minHeight: 32,
        paddingHorizontal: t.space.sm + 2,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.actionSoft,
      }}
    >
      <Icon icon={ShoppingCart} size={14} color={t.colors.onActionSoft} />
      <Text variant="label" style={{ color: t.colors.onActionSoft, fontSize: 13 }}>
        On list
      </Text>
    </View>
  );
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap,
        marginHorizontal: compact ? t.space.sm : t.space.md,
        paddingVertical: t.space.sm + 2,
        borderTopWidth: 1,
        borderTopColor: t.colors.border,
      }}
    >
      <View
        style={{
          flex: 1,
          minWidth: 0,
          flexDirection: 'row',
          alignItems: 'center',
          gap,
        }}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`${row.name}, ${row.staple ? 'Staple' : 'Non-staple'}, ${placeLabel(row.place)}${noted ? `, ${noted}` : ''}`}
          accessibilityHint="Edit amount, status, staple and storage"
          onPress={onOpen}
          style={({ pressed }) => ({ opacity: pressed ? 0.75 : 1 })}
        >
          <FoodThumb
            emoji={ingredientEmoji(row.ingredient)}
            tint={tintFor(row.ingredient.name)}
            size={compact ? 40 : 48}
          />
        </Pressable>
        <View style={{ flex: 1, minWidth: 0, gap: 2, alignItems: 'flex-start' }}>
          <Pressable onPress={onOpen} accessible={false} focusable={false}>
            <Text variant="label" numberOfLines={2} style={{ fontSize: 15, lineHeight: 19 }}>
              {row.name}
            </Text>
            <Text
              variant="caption"
              muted
              numberOfLines={1}
              style={{ fontSize: 12, lineHeight: 16 }}
            >
              {[row.staple ? 'Staple' : 'Non-staple', placeLabel(row.place), noted]
                .filter(Boolean)
                .join(' · ')}
            </Text>
          </Pressable>
          <Pressable
            ref={badge}
            accessibilityRole="button"
            accessibilityLabel={`${row.name}: ${STOCK_LABEL[row.stock]}. Change stock status`}
            onPress={async () => onStatus(await measureAnchor(badge))}
            hitSlop={{ top: 10, bottom: 10, left: 4, right: 4 }} // 44 pt to tap
            style={({ pressed }) => ({ marginTop: 3, opacity: pressed ? 0.7 : 1 })}
          >
            <StockBadge stock={row.stock} />
          </Pressable>
        </View>
      </View>
      <View style={{ alignItems: 'flex-end', gap: t.space.sm }}>
        {stapleOnList ? onListChip : null}
        {offerList ? (
          onList ? (
            onListChip
          ) : (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Add ${row.name} to your shopping list`}
              onPress={onAdd}
              hitSlop={{ top: 4, bottom: 4 }}
              style={({ pressed }) => ({
                flexDirection: 'row',
                alignItems: 'center',
                gap: 4,
                minHeight: 40,
                paddingHorizontal: t.space.sm + 2,
                borderRadius: t.radius.pill,
                backgroundColor: pressed ? t.colors.actionPressed : t.colors.action,
              })}
            >
              <Icon icon={ShoppingCart} size={14} color={t.colors.onAction} />
              <Text variant="label" style={{ color: t.colors.onAction, fontSize: 13 }}>
                Add to list
              </Text>
            </Pressable>
          )
        ) : null}
      </View>
      <Pressable
        ref={more}
        accessibilityRole="button"
        accessibilityLabel={`More for ${row.name}`}
        onPress={async () => onMenu(await measureAnchor(more))}
        style={({ pressed }) => ({
          width: 28,
          minHeight: t.touchTarget,
          alignItems: 'center',
          justifyContent: 'center',
          opacity: pressed ? 0.6 : 1,
        })}
      >
        <Icon icon={Ellipsis} color={t.colors.text} strong />
      </Pressable>
    </View>
  );
}

/** "Update stock status": three rows, the current one green with a tick. */
function StatusPicker({ row, onPick }: { row: KitchenRow; onPick: (stock: Stock) => void }) {
  const t = useTheme();
  return (
    <>
      <Text variant="label" style={{ fontSize: 17, paddingHorizontal: 4, paddingBottom: 2 }}>
        Update stock status
      </Text>
      <View accessibilityRole="radiogroup" style={{ gap: t.space.sm }}>
        {STOCK_ORDER.map((stock) => {
          const on = row.stock === stock;
          const hint =
            stock === 'out' && !on
              ? row.staple
                ? '(Adds to shopping list)'
                : '(Asks to add to list)'
              : null;
          return (
            <Pressable
              key={stock}
              accessibilityRole="radio"
              accessibilityState={{ checked: on }}
              accessibilityLabel={`${stock === 'out' ? 'Ran out' : STOCK_LABEL[stock]}${hint ? `, ${hint.slice(1, -1)}` : ''}`}
              onPress={() => onPick(stock)}
              style={({ pressed }) => ({
                minHeight: 52,
                flexDirection: 'row',
                alignItems: 'center',
                gap: t.space.md,
                paddingHorizontal: t.space.md,
                paddingVertical: t.space.sm,
                borderRadius: t.radius.md,
                borderWidth: 1.5,
                borderColor: on ? t.stock.in_stock.tile : t.colors.border,
                backgroundColor: on ? t.stock.in_stock.tile : t.colors.surface,
                opacity: pressed ? 0.8 : 1,
              })}
            >
              <StockIcon stock={stock} size={24} />
              <View style={{ flex: 1 }}>
                <Text>{stock === 'out' ? 'Ran out' : STOCK_LABEL[stock]}</Text>
                {hint ? (
                  <Text variant="caption" muted>
                    {hint}
                  </Text>
                ) : null}
              </View>
              {on ? <Icon icon={Check} size={20} color={t.stock.in_stock.icon} strong /> : null}
            </Pressable>
          );
        })}
      </View>
    </>
  );
}

function ItemMenu({
  row,
  onEdit,
  onMove,
  onRemove,
}: {
  row: KitchenRow;
  onEdit: () => void;
  onMove: () => void;
  onRemove: () => void;
}) {
  const t = useTheme();
  return (
    <View
      accessibilityRole="menu"
      style={{ marginHorizontal: -t.space.md, marginVertical: -t.space.xs }}
    >
      <MenuItem icon={Pencil} label="Change amount" chevron onPress={onEdit} />
      <MenuItem
        icon={Tag}
        label={row.staple ? 'Move to Non-staples' : 'Move to Staples'}
        onPress={onMove}
        divider
      />
      <MenuItem
        icon={Archive}
        label="Storage location"
        detail={placeLabel(row.place)}
        chevron
        onPress={onEdit}
        divider
      />
      <MenuItem icon={Trash2} label="Remove item" danger onPress={onRemove} divider />
    </View>
  );
}

function MenuItem({
  icon,
  label,
  detail,
  chevron,
  danger,
  divider,
  onPress,
}: {
  icon: LucideIcon;
  label: string;
  detail?: string;
  chevron?: boolean;
  danger?: boolean;
  divider?: boolean;
  onPress: () => void;
}) {
  const t = useTheme();
  const color = danger ? t.colors.danger : t.colors.text;
  return (
    <Pressable
      accessibilityRole="menuitem"
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: 50,
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.md,
        paddingHorizontal: t.space.lg,
        borderTopWidth: divider ? 1 : 0,
        borderTopColor: t.colors.border,
        backgroundColor: pressed ? t.colors.background : 'transparent',
      })}
    >
      <Icon icon={icon} size={20} color={color} />
      <Text style={{ flex: 1, color }}>{label}</Text>
      {detail ? (
        <Text variant="caption" muted>
          {detail}
        </Text>
      ) : null}
      {chevron ? <Icon icon={ChevronRight} size={16} color={t.colors.text} /> : null}
    </Pressable>
  );
}

const KIND_ICON: Record<Kind, LucideIcon> = { weight: Weight, volume: GlassWater, count: Layers };

/**
 * The item sheet: amount (Weight / Volume / Count, number + unit, quick picks), stock
 * status, Staple on/off and storage, saved together. Status goes through the same rule
 * as the badge (a Staple that runs out goes on the list, with Undo).
 */
function ItemSheet({
  row,
  actions,
  onStock,
  onClose,
}: {
  row: KitchenRow;
  actions: Actions;
  onStock: (stock: Stock) => void;
  onClose: () => void;
}) {
  const t = useTheme();
  const toast = useToast();
  const start = editable(row.quantity, row.unit);
  const kinds = allowedKinds(row.unit, row.ingredient.grams_per_ml);
  const [value, setValue] = useState(start.value);
  const [unit, setUnit] = useState<Unit>(start.unit);
  const [unitMenu, setUnitMenu] = useState<Anchor | null>(null);
  const unitButton = useRef<HostInstance>(null);
  const [stock, setStock] = useState<Stock>(row.stock);
  const [staple, setStaple] = useState(row.staple);
  const [place, setPlace] = useState<Place>(row.place);
  const [placeOpen, setPlaceOpen] = useState(false);
  const qty = value.trim() === '' ? null : value.trim();
  const valid = qty === null || Number(qty) > 0;
  const amountChanged = (qty ?? '') !== start.value || unit !== start.unit;

  function save() {
    const setAmountFor = staple ? actions.setStapleAmount : actions.setAmount;
    if (staple !== row.staple) {
      // Changing kind starts a fresh row, so set its amount, Place and status after.
      if (staple) actions.setStaple(row.id, true);
      else actions.notAStaple(row.id);
      if (!staple || amountChanged) setAmountFor(row.id, qty, unit);
      actions.setPlace(row.id, place);
      if (stock !== 'in_stock') void actions.setStock(row.id, stock);
    } else {
      if (amountChanged) setAmountFor(row.id, qty, unit);
      if (place !== row.place) actions.setPlace(row.id, place);
      if (stock !== row.stock)
        onStock(stock); // same rule as the badge
      else if (place !== row.place)
        toast({
          tag: 'Kitchen',
          text: `Moved ${row.name} to the ${placeLabel(place).toLowerCase()}`,
        });
    }
    onClose();
  }

  const header = (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <FoodThumb
        emoji={ingredientEmoji(row.ingredient)}
        tint={tintFor(row.ingredient.name)}
        size={68}
      />
      <View style={{ flex: 1 }}>
        <Text variant="title" accessibilityRole="header" style={{ fontSize: 24, lineHeight: 30 }}>
          {row.name}
        </Text>
        <Text muted>
          {staple ? 'Staple' : 'Non-staple'} · {placeLabel(place)}
        </Text>
      </View>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Close"
        onPress={onClose}
        style={({ pressed }) => ({
          width: t.touchTarget,
          height: t.touchTarget,
          alignItems: 'center',
          justifyContent: 'center',
          alignSelf: 'flex-start',
          opacity: pressed ? 0.6 : 1,
        })}
      >
        <Icon icon={X} color={t.colors.text} strong />
      </Pressable>
    </View>
  );

  return (
    <Sheet label={row.name} title={row.name} header={header} onClose={onClose}>
      <View style={{ gap: t.space.md }}>
        <Text variant="heading" accessibilityRole="header">
          Amount
        </Text>
        {/* Only the ways this Ingredient can be measured; a single way needs no choice. */}
        {kinds.size > 1 ? (
          <View
            accessibilityRole="radiogroup"
            accessibilityLabel="Measure by"
            style={{ flexDirection: 'row', gap: t.space.sm }}
          >
            {KINDS.filter(({ kind }) => kinds.has(kind)).map(({ kind, label }) => {
              const on = kindOf(unit) === kind;
              const fg = on ? t.colors.onInverse : t.colors.text;
              return (
                <Pressable
                  key={kind}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: on }}
                  onPress={() => setUnit(UNITS[kind][0])}
                  style={{
                    flex: 1,
                    minHeight: 46,
                    borderRadius: t.radius.pill,
                    borderWidth: 1.5,
                    borderColor: on ? t.colors.inverse : t.colors.border,
                    backgroundColor: on ? t.colors.inverse : t.colors.surface,
                    flexDirection: 'row',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6,
                  }}
                >
                  <Icon icon={KIND_ICON[kind]} size={18} color={fg} />
                  <Text variant="label" style={{ color: fg }}>
                    {label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        ) : null}
        <View style={{ flexDirection: 'row', gap: t.space.sm }}>
          <TextInput
            accessibilityLabel={`Amount in ${unitLabel(unit)}`}
            value={value}
            onChangeText={setValue}
            keyboardType="decimal-pad"
            placeholder={staple ? 'Not noted' : 'Some'}
            placeholderTextColor={t.colors.textMuted}
            style={[
              t.type.heading,
              {
                flex: 2,
                minHeight: 56,
                paddingHorizontal: t.space.lg,
                borderRadius: t.radius.md,
                borderWidth: 1.5,
                borderColor: valid ? t.colors.border : t.colors.danger,
                backgroundColor: t.colors.surface,
                color: t.colors.text,
              },
            ]}
          />
          <Pressable
            ref={unitButton}
            accessibilityRole="button"
            accessibilityLabel={`Unit: ${unitLabel(unit)}. Change`}
            disabled={UNITS[kindOf(unit)].length < 2}
            onPress={async () => setUnitMenu(await measureAnchor(unitButton))}
            style={{
              flex: 1,
              minHeight: 56,
              paddingHorizontal: t.space.lg,
              borderRadius: t.radius.md,
              borderWidth: 1.5,
              borderColor: t.colors.border,
              backgroundColor: t.colors.surface,
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <Text variant="heading">{unitLabel(unit)}</Text>
            {UNITS[kindOf(unit)].length > 1 ? (
              <Icon icon={ChevronDown} size={20} color={t.colors.text} strong />
            ) : null}
          </Pressable>
        </View>
        {valid ? null : <ErrorText message="Enter a number above 0, or leave it empty" />}
        <View style={{ flexDirection: 'row', gap: t.space.sm, flexWrap: 'wrap' }}>
          {quickPicks(unit).map((pick) => (
            <Pressable
              key={pick}
              accessibilityRole="button"
              accessibilityLabel={`${pick} ${unitLabel(unit)}`}
              onPress={() => setValue(pick)}
              style={({ pressed }) => ({
                minHeight: t.touchTarget,
                minWidth: 64,
                paddingHorizontal: t.space.md,
                borderRadius: t.radius.pill,
                borderWidth: 1.5,
                borderColor: value === pick ? t.colors.inverse : t.colors.border,
                backgroundColor: t.colors.surface,
                alignItems: 'center',
                justifyContent: 'center',
                opacity: pressed ? 0.7 : 1,
              })}
            >
              <Text>
                {pick}
                {unit === 'count' ? '' : ` ${unit}`}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      <View style={{ gap: t.space.md }}>
        <Text variant="heading" accessibilityRole="header">
          Stock status
        </Text>
        <View accessibilityRole="radiogroup" style={{ flexDirection: 'row', gap: t.space.sm }}>
          {STOCK_ORDER.map((s) => {
            const on = stock === s;
            const c = t.stock[s];
            return (
              <Pressable
                key={s}
                accessibilityRole="radio"
                accessibilityState={{ checked: on }}
                onPress={() => setStock(s)}
                style={{
                  flex: 1,
                  minHeight: 88,
                  borderRadius: t.radius.md,
                  borderWidth: 2,
                  borderColor: on ? c.icon : t.colors.border,
                  backgroundColor: on ? c.tile : t.colors.surface,
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                }}
              >
                <StockIcon stock={s} size={28} />
                <Text variant="label">{s === 'out' ? 'Ran out' : STOCK_LABEL[s]}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.md,
          paddingHorizontal: t.space.lg,
          minHeight: 60,
          borderRadius: t.radius.lg,
          backgroundColor: t.colors.surface,
          boxShadow: t.shadow.card,
        }}
      >
        <Icon icon={Leaf} size={22} color={t.colors.text} />
        <Text style={{ flex: 1 }}>Make this a staple</Text>
        <Switch
          accessibilityLabel="Make this a staple"
          value={staple}
          onValueChange={setStaple}
          trackColor={{ true: t.stock.in_stock.icon, false: t.colors.border }}
          thumbColor="#ffffff"
        />
      </View>

      <View
        style={{
          borderRadius: t.radius.lg,
          backgroundColor: t.colors.surface,
          boxShadow: t.shadow.card,
        }}
      >
        <Pressable
          accessibilityRole="button"
          accessibilityState={{ expanded: placeOpen }}
          accessibilityLabel={`Storage location: ${placeLabel(place)}`}
          onPress={() => setPlaceOpen(!placeOpen)}
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            paddingHorizontal: t.space.lg,
            minHeight: 60,
          }}
        >
          <Icon icon={Container} size={22} color={t.colors.text} />
          <Text style={{ flex: 1 }}>Storage location</Text>
          <Text>{placeLabel(place)}</Text>
          <View style={{ transform: [{ rotate: placeOpen ? '90deg' : '0deg' }] }}>
            <Icon icon={ChevronRight} size={18} color={t.colors.text} strong />
          </View>
        </Pressable>
        {placeOpen ? (
          <View
            accessibilityRole="radiogroup"
            style={{
              flexDirection: 'row',
              gap: 6,
              paddingHorizontal: t.space.md,
              paddingBottom: t.space.md,
            }}
          >
            {PLACES.map((p) => (
              <PlaceChip
                key={p.place}
                label={p.label}
                icon={PLACE_ICON[p.place]}
                on={place === p.place}
                onPress={() => setPlace(p.place)}
              />
            ))}
          </View>
        ) : null}
      </View>

      <Button title="Save changes" disabled={!valid} onPress={save} />

      {unitMenu ? (
        <Popover anchor={unitMenu} label="Unit" width={160} onClose={() => setUnitMenu(null)}>
          {UNITS[kindOf(unit)].map((u) => (
            <Pressable
              key={u}
              accessibilityRole="radio"
              accessibilityState={{ checked: u === unit }}
              onPress={() => {
                setUnit(u);
                setUnitMenu(null);
              }}
              style={{
                minHeight: t.touchTarget,
                flexDirection: 'row',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingHorizontal: t.space.sm,
              }}
            >
              <Text variant="label">{unitLabel(u)}</Text>
              {u === unit ? (
                <Icon icon={Check} size={18} color={t.stock.in_stock.icon} strong />
              ) : null}
            </Pressable>
          ))}
        </Popover>
      ) : null}
    </Sheet>
  );
}

/**
 * Ingredients matching the "Add to Kitchen" search, each one tap to add. When nothing
 * is called exactly what was typed, the last row offers to add it anyway, as a
 * Household Ingredient (ADR 0012).
 */
function AddMatches({
  query,
  known,
  onAdd,
  onAddNew,
}: {
  query: string;
  known: Set<string>;
  onAdd: (id: string) => void;
  onAddNew: (name: string) => void;
}) {
  const t = useTheme();
  const results = useIngredientSearch(query);
  if (query.trim().length < 2) return null;
  // Wait for this query's results (not the previous query's), so we never offer to add
  // something search is about to show.
  const settled = results.isSuccess && !results.isPlaceholderData;
  const offer = settled
    ? newIngredientName(
        query,
        results.data.map((i) => i.name),
      )
    : null;

  return (
    <View
      style={{
        gap: t.space.xs,
        backgroundColor: t.colors.surface,
        borderRadius: t.radius.lg,
        padding: t.space.sm,
      }}
    >
      {results.data?.slice(0, 6).map((ingredient) => {
        const already = known.has(ingredient.id);
        return (
          <MatchRow
            key={ingredient.id}
            t={t}
            disabled={already}
            onPress={() => onAdd(ingredient.id)}
            name={displayName(ingredient.name)}
            note={already ? 'already in Kitchen' : 'add'}
          />
        );
      })}
      {offer ? (
        <MatchRow
          t={t}
          onPress={() => onAddNew(offer)}
          name={`Add "${displayName(offer)}"`}
          note="new to your Kitchen"
        />
      ) : null}
    </View>
  );
}

function MatchRow({
  t,
  name,
  note,
  disabled,
  onPress,
}: {
  t: Theme;
  name: string;
  note: string;
  disabled?: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => ({
        minHeight: t.touchTarget,
        justifyContent: 'center',
        paddingHorizontal: t.space.sm,
        opacity: disabled ? 0.5 : pressed ? 0.6 : 1,
      })}
    >
      <Text>
        {name}
        <Text muted> · {note}</Text>
      </Text>
    </Pressable>
  );
}
