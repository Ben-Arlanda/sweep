import { Ellipsis, Link2, Store, Trash2 } from 'lucide-react-native';
import { useRef, useState } from 'react';
import { Pressable, View, type HostInstance, type TextInputInstance } from 'react-native';
import Animated, { FadeInDown, FadeOut, ReduceMotion } from 'react-native-reanimated';

import { AvatarStack } from '@/components/Avatar';
import { Checkbox } from '@/components/Checkbox';
import { ChoiceChips } from '@/components/ChoiceChips';
import { Icon } from '@/components/Icon';
import { MenuItem } from '@/components/MenuItem';
import { Pill } from '@/components/Pill';
import { measureAnchor, Popover, type Anchor } from '@/components/Popover';
import { useToast } from '@/components/Toast';
import {
  Button,
  Card,
  ErrorText,
  Field,
  Loading,
  Screen,
  SectionLabel,
  Text,
} from '@/components/ui';
import { useMembers } from '@/features/household/useMembers';
import { shoppingOrder } from '@/features/lists/listCache';
import { LinkSheet } from '@/features/lists/LinkSheet';
import { ShopSheet } from '@/features/lists/ShopSheet';
import {
  filterByShop,
  knownShop,
  shopName,
  type Shop,
  type ShopFilter,
} from '@/features/lists/shops';
import type { Item, ListDetail, MemberOut } from '@/lib/api/client';
import { useIsOnline, useList, useListActions, usePendingListChanges } from '@/lib/api/lists';
import { tintFor } from '@/theme/tint';
import { FoodThumb } from '@/components/FoodThumb';
import { ingredientEmoji } from '@/theme/foodEmoji';
import { useTheme } from '@/theme/useTheme';

const ALL = 'all';

/**
 * The Household's Shopping List (one per Household, ADR 0009), made for using in a shop
 * with one hand: big tap targets, the add box at the top. Ticking an item takes it off
 * the list (with Undo); ••• holds its Shop, Kitchen link and Remove. Filter by Shop when
 * you're standing in one.
 */
export default function ListScreen() {
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
  const { members, byId } = useMembers();
  const [filter, setFilter] = useState<ShopFilter>(ALL);
  const toast = useToast();
  // Which item's ••• menu, Shop sheet or Kitchen link sheet is open, if any.
  const [menu, setMenu] = useState<{ item: Item; anchor: Anchor } | null>(null);
  const [tagging, setTagging] = useState<Item | null>(null);
  const [linking, setLinking] = useState<Item | null>(null);

  const { shops } = list;
  // A Shop deleted on another phone while we were filtering by it: show everything.
  const shown = filter === ALL ? ALL : (knownShop(filter, shops) ?? ALL);
  // Ticked items are off the list: no "In the trolley" section (Undo brings one back).
  const { toBuy } = shoppingOrder(filterByShop(list.items, shown));
  const at = shown === ALL ? '' : ` at ${shopName(shops, shown)}`;
  const summary = toBuy.length === 0 ? `Nothing left to buy${at}` : `${toBuy.length} to buy${at}`;

  const row = (item: Item, i: number) => (
    <ItemRow
      key={item.id}
      item={item}
      index={i}
      actions={actions}
      members={byId}
      shops={shops}
      onMenu={(anchor) => setMenu({ item, anchor })}
    />
  );

  return (
    <Screen>
      <Card tint={tintFor(list.id)} style={{ gap: t.space.sm }}>
        <View
          style={{
            flexDirection: 'row',
            alignItems: 'flex-start',
            gap: t.space.md,
          }}
        >
          <Text variant="title" accessibilityRole="header" style={{ flex: 1 }}>
            Shopping List
          </Text>
          <AvatarStack members={members} size={28} />
        </View>
        <Text accessibilityLiveRegion="polite">{summary}</Text>
      </Card>

      {shops.length > 0 ? (
        <ChoiceChips
          label="Show items for"
          value={shown}
          onChange={setFilter}
          options={[
            { label: 'All', value: ALL, accessibilityLabel: 'All shops' },
            ...shops.map((shop) => ({ label: shop.name, value: shop.id })),
          ]}
        />
      ) : null}

      <SyncStatus />
      <AddItem onAdd={actions.addItem} />
      <ErrorText message={actions.error?.message} />

      <View style={{ gap: t.space.sm }}>
        <SectionLabel>To buy</SectionLabel>
        {toBuy.length === 0 ? <Text muted>Nothing left to buy. Nice work.</Text> : null}
        {toBuy.map(row)}
      </View>

      {menu ? (
        <Popover
          anchor={menu.anchor}
          label={`${menu.item.text} options`}
          width={260}
          onClose={() => setMenu(null)}
        >
          <ItemMenu
            item={menu.item}
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
              toast({ tag: 'List', text: `Removed ${menu.item.text}` });
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
function AddItem({ onAdd }: { onAdd: (text: string) => void }) {
  const [text, setText] = useState('');
  const input = useRef<TextInputInstance>(null);

  function submit() {
    if (!text.trim()) return;
    onAdd(text.trim());
    setText('');
    input.current?.focus(); // keep the keyboard up for the next item
  }

  return (
    <Field
      ref={input}
      label="Add an item"
      placeholder="e.g. 2 L milk"
      value={text}
      onChangeText={setText}
      onSubmitEditing={submit}
      submitBehavior="submit"
      returnKeyType="done"
      maxLength={200}
    />
  );
}

/**
 * One item. The whole row is the checkbox (a big target for one thumb in a shop): ticking
 * takes it off the list, with Undo. Ticking an item linked to an Ingredient also stocks
 * the Kitchen (ADR 0003), so the toast says so: that's the loop, made visible. ••• opens
 * Shop, Kitchen link and Remove (which doesn't stock the Kitchen).
 */
function ItemRow({
  item,
  index,
  actions,
  members,
  shops,
  onMenu,
}: {
  item: Item;
  index: number;
  actions: Actions;
  members: Map<string, MemberOut>;
  shops: readonly Shop[];
  onMenu: (anchor: Anchor) => void;
}) {
  const t = useTheme();
  const toast = useToast();
  const more = useRef<HostInstance>(null);
  const amount = [item.quantity, item.unit].filter(Boolean).join(' ');
  const tint = tintFor(item.ingredient?.name ?? item.text);
  const addedBy = item.added_by_member_id ? members.get(item.added_by_member_id) : undefined;
  const shop = shopName(shops, item.shop_id);

  const caption = [shop, addedBy ? `added by ${addedBy.display_name}` : null]
    .filter(Boolean)
    .join(' · ');

  function tick() {
    // Send what the Member *sees* as the new state, not "toggle" (ADR 0004).
    actions.setChecked(item.id, true);
    toast({
      kind: 'undo',
      text: `Ticked off ${item.text}`,
      detail: item.ingredient
        ? `Added ${amount ? `${amount} ` : ''}${item.ingredient.name} to your Kitchen`
        : undefined,
      onUndo: () => actions.setChecked(item.id, false),
    });
  }

  return (
    <Animated.View
      // Rows rise in one after another when the list opens. Capped so a long list
      // doesn't make the last row wait.
      entering={FadeInDown.delay(Math.min(index, 8) * t.motion.staggerMs)
        .springify()
        .damping(18)
        .reduceMotion(ReduceMotion.System)}
      exiting={FadeOut.duration(180).reduceMotion(ReduceMotion.System)}
    >
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.md,
          boxShadow: t.shadow.card,
        }}
      >
        {/* No custom label: the visible text ("Milk, Coles · added by Alice, 2 L") is the
            name, so voice control users can say exactly what they see (WCAG 2.5.3). */}
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: false }}
          aria-checked={false}
          onPress={tick}
          style={({ pressed }) => ({
            flex: 1,
            minHeight: t.touchTarget + 12,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            paddingVertical: t.space.sm,
            paddingLeft: t.space.sm,
            opacity: pressed ? 0.75 : 1,
          })}
        >
          <Checkbox checked={false} />
          <FoodThumb emoji={ingredientEmoji(item.ingredient)} tint={tint} />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="label">{item.text}</Text>
            {caption ? (
              <Text variant="caption" muted numberOfLines={2}>
                {caption}
              </Text>
            ) : null}
          </View>
          {amount ? <Pill tint={tint}>{amount}</Pill> : null}
        </Pressable>
        <Pressable
          ref={more}
          accessibilityRole="button"
          accessibilityLabel={`More for ${item.text}`}
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
    </Animated.View>
  );
}

/** ••• on an item: its Shop, what it is in the Kitchen (ADR 0012), and Remove. */
function ItemMenu({
  item,
  shop,
  onShop,
  onLink,
  onRemove,
}: {
  item: Item;
  shop: string | null;
  onShop: () => void;
  onLink: () => void;
  onRemove: () => void;
}) {
  const t = useTheme();
  return (
    <View
      accessibilityRole="menu"
      style={{ marginHorizontal: -t.space.md, marginVertical: -t.space.xs }}
    >
      <MenuItem icon={Store} label="Shop" detail={shop ?? 'Any shop'} chevron onPress={onShop} />
      <MenuItem
        icon={Link2}
        label="Kitchen link"
        detail={item.ingredient?.name ?? 'None'}
        chevron
        divider
        onPress={onLink}
      />
      <MenuItem icon={Trash2} label="Remove from list" danger divider onPress={onRemove} />
    </View>
  );
}

/** Tells the Member their taps are safe even when the signal isn't. */
function SyncStatus() {
  const pending = usePendingListChanges();
  const online = useIsOnline();
  if (pending === 0) return null;
  return (
    <Text variant="caption" muted accessibilityLiveRegion="polite">
      {online
        ? 'Saving…'
        : `Offline. ${pending} ${pending === 1 ? 'change' : 'changes'} will sync when you're back online.`}
    </Text>
  );
}
