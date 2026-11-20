import {
  ChevronUp,
  Ellipsis,
  Link2,
  Plus,
  ShoppingBasket,
  Store,
  Trash2,
} from 'lucide-react-native';
import { useRef, useState, type ReactNode } from 'react';
import Animated, {
  LayoutAnimationConfig,
  useAnimatedKeyboard,
  useAnimatedStyle,
  useSharedValue,
} from 'react-native-reanimated';
import {
  Platform,
  Pressable,
  TextInput,
  View,
  type HostInstance,
  type TextInputInstance,
} from 'react-native';

import { toggled } from '@/components/CategoryAccordion';
import { Checkbox } from '@/components/Checkbox';
import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { MenuItem } from '@/components/MenuItem';
import { displayName } from '@/features/kitchen/format';
import { PageHeader } from '@/components/PageHeader';
import { measureAnchor, Popover, type Anchor } from '@/components/Popover';
import { useToast } from '@/components/Toast';
import { Button, ErrorText, Loading, Screen, TAB_ROOT, Text } from '@/components/ui';
import { useMembers } from '@/features/household/useMembers';
import { addedByText } from '@/features/lists/addedBy';
import { listSections } from '@/features/lists/categories';
import { shoppingOrder } from '@/features/lists/listCache';
import { LinkSheet } from '@/features/lists/LinkSheet';
import { ShopSheet } from '@/features/lists/ShopSheet';
import { filterByShop, knownShop, shopName, type ShopFilter } from '@/features/lists/shops';
import type { Item, ListDetail } from '@/lib/api/client';
import { useMe } from '@/lib/api/households';
import { useIsOnline, useList, useListActions, usePendingListChanges } from '@/lib/api/lists';
import { haptic } from '@/lib/haptics';
import { inputText } from '@/theme/inputText';
import { rowEntering, rowExiting, rowLayout } from '@/theme/listMotion';
import { PageColors } from '@/theme/PageColors';
import { useTheme } from '@/theme/useTheme';

const ALL = 'all';

/**
 * The Household's Shopping List (one per Household, ADR 0009), made for using in a shop
 * with one hand: big tap targets, the add box at the top. Ticking an item takes it off
 * the list (with Undo); ••• holds its Shop, Kitchen link and Remove. Filter by Shop when
 * you're standing in one.
 */
function ListScreenContent() {
  const list = useList();
  if (list.isPending) return <Loading />;
  if (list.isError) {
    return (
      <Screen>
        <ErrorText message={list.error.message} />
        <Button title="Try again" onPress={() => list.refetch()} />
      </Screen>
    );
  }
  return <ListContent list={list.data} />;
}

function ListContent({ list }: { list: ListDetail }) {
  const t = useTheme();
  const actions = useListActions(list.id);
  const { byId } = useMembers();
  const me = useMe().data?.member.id;
  const [filter, setFilter] = useState<ShopFilter>(ALL);
  const toast = useToast();
  // Which item's ••• menu, Shop sheet or Kitchen link sheet is open, if any.
  const [menu, setMenu] = useState<{ item: Item; anchor: Anchor } | null>(null);
  const [tagging, setTagging] = useState<Item | null>(null);
  const [linking, setLinking] = useState<Item | null>(null);
  // Food categories folded away, by category (open by default).
  const [closed, setClosed] = useState<Set<string>>(() => new Set());
  // Items added since the add box was focused: shown at the top until the keyboard closes.
  const [justAdded, setJustAdded] = useState<string[]>([]);

  const { shops } = list;
  // A Shop deleted on another phone while we were filtering by it: show everything.
  const shown = filter === ALL ? ALL : (knownShop(filter, shops) ?? ALL);
  // Ticked items are off the list: no "In the trolley" section (Undo brings one back).
  const { toBuy: all } = shoppingOrder(filterByShop(list.items, shown));
  const fresh = justAdded
    .map((id) => all.find((item) => item.id === id))
    .filter((item): item is Item => item !== undefined)
    .reverse();
  const toBuy = all.filter((item) => !justAdded.includes(item.id));
  const at = shown === ALL ? '' : ` at ${shopName(shops, shown)}`;
  const summary = all.length === 0 ? `Nothing left to buy${at}` : `${all.length} to buy${at}`;
  const sync = useSyncStatus();

  const row = (item: Item, i: number) => (
    <Animated.View key={item.id} entering={rowEntering} exiting={rowExiting} layout={rowLayout}>
      <ItemRow
        item={item}
        index={i}
        actions={actions}
        // On a Shop's filter every row is that Shop, so its name would just repeat.
        shop={shown === ALL ? shopName(shops, item.shop_id) : null}
        onMenu={(anchor) => setMenu({ item, anchor })}
      />
    </Animated.View>
  );

  return (
    <Screen edges={TAB_ROOT}>
      <FoldsForKeyboard>
        <PageHeader
          icon={ShoppingBasket}
          section="list"
          title="Shopping list"
          subtitle={`${summary}${sync ? ` · ${sync}` : ''}`}
        />
      </FoldsForKeyboard>

      <AddItem
        onAdd={(text) => {
          const id = actions.addItem(text);
          setJustAdded((now) => [...now, id]);
        }}
        onDone={() => setJustAdded([])}
      />

      {fresh.length > 0 ? (
        <Animated.View entering={rowEntering} exiting={rowExiting} layout={rowLayout}>
          <ListGroup label="Just added" count={fresh.length} open>
            {fresh.map(row)}
          </ListGroup>
        </Animated.View>
      ) : null}

      {shops.length > 0 ? (
        <ChoiceChips
          label="Show items for"
          value={shown}
          onChange={setFilter}
          size="small"
          options={[
            { label: 'All', value: ALL, accessibilityLabel: 'All shops' },
            ...shops.map((shop) => ({ label: shop.name, value: shop.id })),
          ]}
        />
      ) : null}

      <ErrorText message={actions.error?.message} />

      {toBuy.length === 0 && fresh.length === 0 ? (
        <Text style={{ color: t.colors.onBackgroundMuted }}>Nothing left to buy. Nice work.</Text>
      ) : null}
      <LayoutAnimationConfig skipEntering>
        {listSections(toBuy).map((section) => (
          <Animated.View
            key={section.category}
            entering={rowEntering}
            exiting={rowExiting}
            layout={rowLayout}
          >
            <ListGroup
              label={section.label}
              count={section.items.length}
              open={!closed.has(section.category)}
              onToggle={() => setClosed((now) => toggled(now, section.category))}
            >
              {section.items.map(row)}
            </ListGroup>
          </Animated.View>
        ))}
      </LayoutAnimationConfig>

      {menu ? (
        <Popover
          anchor={menu.anchor}
          label={`${displayName(menu.item.text)} options`}
          width={260}
          onClose={() => setMenu(null)}
        >
          <ItemMenu
            item={menu.item}
            addedBy={addedByText(menu.item, me, byId)}
            shop={shopName(shops, menu.item.shop_id)}
            onShop={() => {
              setMenu(null);
              setTagging(menu.item);
            }}
            onLink={() => {
              setMenu(null);
              setLinking(menu.item);
            }}
            onRemove={() => {
              setMenu(null);
              actions.deleteItem(menu.item.id);
              toast({ tag: 'List', text: `Removed ${displayName(menu.item.text)}` });
            }}
          />
        </Popover>
      ) : null}

      {tagging ? (
        <ShopSheet
          itemText={tagging.text}
          shopId={tagging.shop_id}
          shops={shops}
          onPick={(shopId) => actions.setShop(tagging.id, shopId)}
          onClose={() => setTagging(null)}
        />
      ) : null}
      {linking ? (
        <LinkSheet
          name={linking.text}
          current={linking.ingredient}
          onPick={(ingredient) => {
            actions.link(linking.id, ingredient);
            toast({
              tag: 'Kitchen',
              text: ingredient
                ? `${linking.text} is ${ingredient.name}. Sweep will remember.`
                : `${linking.text} won't be added to the Kitchen`,
            });
          }}
          onClose={() => setLinking(null)}
        />
      ) : null}
    </Screen>
  );
}

type Actions = ReturnType<typeof useListActions>;

/** The add box. New items are "any shop"; pick one from the item's ••• menu. */
function AddItem({ onAdd, onDone }: { onAdd: (text: string) => void; onDone: () => void }) {
  const t = useTheme();
  const [text, setText] = useState('');
  const input = useRef<TextInputInstance>(null);

  function submit() {
    if (!text.trim()) return;
    onAdd(text.trim());
    setText('');
    input.current?.focus(); // keep the keyboard up for the next item
  }

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        minHeight: 46,
        paddingHorizontal: t.space.md,
        borderRadius: t.radius.md,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surface,
      }}
    >
      <Icon icon={Plus} size={18} color={t.colors.textMuted} />
      <TextInput
        ref={input}
        accessibilityLabel="Add an item"
        placeholder="Add an item, e.g. 2 L milk"
        placeholderTextColor={t.colors.textMuted}
        value={text}
        onChangeText={setText}
        onSubmitEditing={submit}
        onBlur={onDone}
        submitBehavior="submit"
        // The web ignores submitBehavior and drops focus after Enter unless told not to.
        {...(Platform.OS === 'web' ? { blurOnSubmit: false } : null)}
        returnKeyType="done"
        maxLength={200}
        style={[
          inputText(t.type.body),
          { flex: 1, minHeight: t.touchTarget, color: t.colors.text },
        ]}
      />
    </View>
  );
}

/**
 * Folds the page heading away as the keyboard rises, frame by frame with it, so the add
 * box and the list move up together; it unfolds as the keyboard goes. Phones only.
 */
function FoldsForKeyboard({ children }: { children: ReactNode }) {
  if (Platform.OS === 'web') return children;
  return <Fold>{children}</Fold>;
}

function Fold({ children }: { children: ReactNode }) {
  const keyboard = useAnimatedKeyboard();
  const natural = useSharedValue(0);
  const folding = useAnimatedStyle(() => {
    const full = natural.get();
    if (full === 0) return {};
    const shut = Math.min(1, keyboard.height.get() / full);
    return { height: full * (1 - shut), opacity: 1 - shut };
  });
  return (
    <Animated.View style={[{ overflow: 'hidden' }, folding]}>
      <View onLayout={(e) => natural.set(e.nativeEvent.layout.height)}>{children}</View>
    </Animated.View>
  );
}

/**
 * A food category: a small uppercase heading over a card of rows. The heading folds the
 * card away (open by default), so a long list stays easy to scan in the shop.
 */
function ListGroup({
  label,
  count,
  open,
  onToggle,
  children,
}: {
  label: string;
  count: number;
  open: boolean;
  /** Without it the heading doesn't fold (Just added). */
  onToggle?: () => void;
  children: ReactNode;
}) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.sm }}>
      <Pressable
        disabled={!onToggle}
        accessibilityRole={onToggle ? 'button' : undefined}
        accessibilityState={onToggle ? { expanded: open } : undefined}
        accessibilityLabel={`${label}, ${count} ${count === 1 ? 'item' : 'items'}`}
        onPress={onToggle}
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          gap: 6,
          minHeight: 32,
          paddingLeft: 2,
        }}
      >
        <Text
          variant="caption"
          muted
          accessibilityRole="header"
          style={{
            fontFamily: t.fonts.bold,
            fontSize: 12,
            letterSpacing: 0.7,
            textTransform: 'uppercase',
          }}
        >
          {label}
        </Text>
        {onToggle ? (
          <View style={{ transform: [{ rotate: open ? '0deg' : '180deg' }] }}>
            <Icon icon={ChevronUp} size={14} color={t.colors.textMuted} strong />
          </View>
        ) : null}
      </Pressable>
      {open ? (
        <View
          style={{
            backgroundColor: t.colors.surface,
            borderRadius: t.radius.lg,
            boxShadow: t.shadow.card,
            overflow: 'hidden',
          }}
        >
          {children}
        </View>
      ) : null}
    </View>
  );
}

/**
 * One item. The whole row is the checkbox (a big target for one thumb in a shop): ticking
 * takes it off the list, with Undo. Ticking an item linked to an Ingredient also stocks
 * the Kitchen (ADR 0003), so the toast says so: that's the loop, made visible. ••• opens
 * Shop, Kitchen link and Remove (which doesn't stock the Kitchen).
 */
/** How long a ticked row stays to show its tick before it leaves the list. */
const TICK_MS = 180;

function ItemRow({
  item,
  index,
  actions,
  shop,
  onMenu,
}: {
  item: Item;
  index: number;
  actions: Actions;
  /** Shown under the name on All; null on a Shop's own filter or for "any shop". */
  shop: string | null;
  onMenu: (anchor: Anchor) => void;
}) {
  const t = useTheme();
  const toast = useToast();
  const more = useRef<HostInstance>(null);
  const amount = [item.quantity, item.unit].filter(Boolean).join(' ');
  // Under the name: the amount, then the Shop on All ("250 g · Aldi").
  const detail = [amount, shop].filter(Boolean).join(' · ');

  const [ticked, setTicked] = useState(false);

  function tick() {
    if (ticked) return;
    setTicked(true);
    haptic.tap();
    // Let the tick land before the row leaves.
    setTimeout(() => {
      // Send what the Member *sees* as the new state, not "toggle" (ADR 0004).
      actions.setChecked(item.id, true);
      toast({
        kind: 'undo',
        text: `Ticked off ${displayName(item.text)}`,
        detail: item.ingredient
          ? `Added ${amount ? `${amount} ` : ''}${item.ingredient.name} to your Kitchen`
          : undefined,
        onUndo: () => actions.setChecked(item.id, false),
      });
    }, TICK_MS);
  }

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        // A line between rows (none above the first) inside the category card.
        borderTopWidth: index === 0 ? 0 : 1,
        borderTopColor: t.colors.border,
        paddingRight: 6,
      }}
    >
      {/* No custom label: the visible text ("Milk, Coles, 2 L") is the
            name, so voice control users can say exactly what they see (WCAG 2.5.3). */}
      <Pressable
        accessibilityRole="checkbox"
        accessibilityState={{ checked: ticked }}
        aria-checked={ticked}
        onPress={tick}
        style={({ pressed }) => ({
          flex: 1,
          minHeight: 60,
          flexDirection: 'row',
          alignItems: 'center',
          gap: t.space.sm,
          paddingVertical: t.space.sm,
          paddingLeft: t.space.xs,
          opacity: pressed ? 0.75 : 1,
        })}
      >
        <View style={{ width: 36, alignItems: 'center' }}>
          <Checkbox checked={ticked} size={22} tick={false} />
        </View>
        <View style={{ flex: 1, gap: 2 }}>
          <Text variant="label">{displayName(item.text)}</Text>
          {detail ? (
            <Text variant="caption" muted style={{ fontVariant: ['tabular-nums'] }}>
              {detail}
            </Text>
          ) : null}
        </View>
      </Pressable>
      <Pressable
        ref={more}
        accessibilityRole="button"
        accessibilityLabel={`More for ${displayName(item.text)}`}
        onPress={async () => onMenu(await measureAnchor(more))}
        style={({ pressed }) => ({
          width: t.touchTarget,
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

/** ••• on an item: its Shop, what it is in the Kitchen (ADR 0012), and Remove. */
function ItemMenu({
  item,
  addedBy,
  shop,
  onShop,
  onLink,
  onRemove,
}: {
  item: Item;
  addedBy: string;
  shop: string | null;
  onShop: () => void;
  onLink: () => void;
  onRemove: () => void;
}) {
  const t = useTheme();
  return (
    <View style={{ marginHorizontal: -t.space.md, marginVertical: -t.space.xs }}>
      <View accessibilityRole="menu">
        <MenuItem icon={Store} label="Shop" detail={shop ?? 'Any shop'} chevron onPress={onShop} />
        <MenuItem
          icon={Link2}
          label="Link item"
          detail={item.ingredient?.name ?? 'None'}
          chevron
          divider
          onPress={onLink}
        />
        <MenuItem icon={Trash2} label="Remove from list" danger divider onPress={onRemove} />
      </View>
      {/* Outside the menu: screen readers only announce menu items inside one. */}
      <Text
        variant="caption"
        muted
        style={{
          paddingHorizontal: t.space.lg,
          paddingVertical: t.space.sm,
          borderTopWidth: 1,
          borderTopColor: t.colors.border,
        }}
      >
        {addedBy}
      </Text>
    </View>
  );
}

/**
 * Tells the Member their taps are safe even when the signal isn't. Shown on the summary
 * line, not a line of its own: appearing for a moment on every tick, a line above the
 * add box pushed it down and back up.
 */
function useSyncStatus(): string | null {
  const pending = usePendingListChanges();
  const online = useIsOnline();
  if (pending === 0) return null;
  return online ? 'Saving…' : `Offline: ${pending} to sync`;
}

/** The list tab on its own page colour (PAGE_COLORS). */
export default function ListScreen() {
  return (
    <PageColors page="list">
      <ListScreenContent />
    </PageColors>
  );
}
