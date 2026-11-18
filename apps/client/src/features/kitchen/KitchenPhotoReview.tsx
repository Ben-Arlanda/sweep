import { randomUUID } from 'expo-crypto';
import { router, usePreventRemove } from 'expo-router';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { Checkbox } from '@/components/Checkbox';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { FoodThumb } from '@/components/FoodThumb';
import { useToast } from '@/components/Toast';
import { Button, ErrorText, Field, Screen, SectionLabel, Text } from '@/components/ui';
import { useApplyKitchenPhotos, type KitchenPhotoRead } from '@/lib/api/kitchenPhotos';
import { ingredientEmoji } from '@/theme/foodEmoji';
import { tintFor } from '@/theme/tint';
import { useTheme } from '@/theme/useTheme';

import { displayName } from './format';
import { dropPhotoRead } from './photoDrafts';
import {
  amountProblem,
  formRows,
  groups,
  hasChanges,
  inKitchenText,
  tickedCount,
  toApply,
  type ReviewRow,
} from './photoReview';
import { PLACES } from './places';

/**
 * What Sweep saw in a Kitchen Photo (ADR 0023). Everything starts ticked; the Member
 * unticks what's wrong or fixes an amount, then one tap adds the ticked rows. A photo
 * shows what you have, so its amount replaces the Kitchen's, and nothing is removed.
 */
export function KitchenPhotoReview({ read }: { read: KitchenPhotoRead }) {
  const t = useTheme();
  const toast = useToast();
  const [start] = useState(() => formRows(read.rows));
  const [rows, setRows] = useState(start);
  const [tried, setTried] = useState(false);
  const [leave, setLeave] = useState<(() => void) | null>(null);
  const [idempotencyKey] = useState(() => randomUUID()); // one review, one add
  const apply = useApplyKitchenPhotos();

  const disablePrevention = usePreventRemove(!apply.isSuccess, ({ repeat }) =>
    setLeave(() => repeat),
  );

  const place = PLACES.find((p) => p.place === read.place)?.label ?? read.place;
  const count = tickedCount(rows);
  const { fresh, existing } = groups(rows);
  const update = (key: string, change: Partial<ReviewRow>) =>
    setRows((all) => all.map((r) => (r.key === key ? { ...r, ...change } : r)));

  async function onAdd() {
    setTried(true);
    if (rows.some((r) => r.ticked && amountProblem(r))) return;
    try {
      await apply.mutateAsync({ body: toApply(read.place, rows), idempotencyKey });
      dropPhotoRead();
      disablePrevention();
      toast({ tag: 'Kitchen', text: `Added ${count} from the ${place.toLowerCase()}` });
      router.back();
    } catch {
      // apply.error has the server's message
    }
  }

  const section = (title: string, list: ReviewRow[]) =>
    list.length ? (
      <View style={{ gap: t.space.xs }}>
        <SectionLabel>{title}</SectionLabel>
        {list.map((row) => (
          <PhotoRowView
            key={row.key}
            row={row}
            problem={tried && row.ticked ? amountProblem(row) : null}
            onChange={(change) => update(row.key, change)}
          />
        ))}
      </View>
    ) : null;

  return (
    <Screen>
      <Text variant="title" accessibilityRole="header">
        Check what Sweep saw
      </Text>
      <Text muted>
        From the {place.toLowerCase()}. Untick anything that&apos;s wrong, and change an amount if
        you know it (empty means &ldquo;some&rdquo;). An amount replaces what&apos;s in your
        Kitchen; nothing missing from the photo is removed.
      </Text>
      {section('New', fresh)}
      {section('Already in your Kitchen', existing)}
      <ErrorText message={apply.error?.message} />
      <Button
        title={count ? `Add ${count} to Kitchen` : 'Nothing ticked'}
        disabled={!count}
        loading={apply.isPending}
        onPress={onAdd}
      />
      {leave ? (
        <ConfirmDialog
          title="Leave without adding?"
          message={
            hasChanges(start, rows)
              ? 'Your changes and what Sweep saw will be lost.'
              : 'Nothing will be added to your Kitchen.'
          }
          confirm="Leave without adding"
          cancel="Keep checking"
          onCancel={() => setLeave(null)}
          onConfirm={() => {
            dropPhotoRead();
            setLeave(null);
            disablePrevention();
            leave();
          }}
        />
      ) : null}
    </Screen>
  );
}

function PhotoRowView({
  row,
  problem,
  onChange,
}: {
  row: ReviewRow;
  problem: string | null;
  onChange: (change: Partial<ReviewRow>) => void;
}) {
  const t = useTheme();
  const name = displayName(row.ingredient?.name ?? row.name);
  const now = inKitchenText(row);
  return (
    <View style={{ gap: t.space.xs }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.sm }}>
        {/* The visible text is the checkbox's name, for voice control (WCAG 2.5.3). */}
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: row.ticked }}
          aria-checked={row.ticked}
          onPress={() => onChange({ ticked: !row.ticked })}
          style={({ pressed }) => ({
            flex: 1,
            minHeight: t.touchTarget + 8,
            flexDirection: 'row',
            alignItems: 'center',
            gap: t.space.md,
            opacity: pressed ? 0.75 : 1,
          })}
        >
          <Checkbox checked={row.ticked} />
          <FoodThumb
            emoji={ingredientEmoji(row.ingredient)}
            tint={tintFor(row.ingredient?.id ?? row.name)}
          />
          <View style={{ flex: 1, gap: 2 }}>
            <Text variant="label" muted={!row.ticked}>
              {name}
            </Text>
            {now ? (
              <Text variant="caption" muted>
                {now}
              </Text>
            ) : null}
            {row.ingredient ? null : (
              <Text variant="caption" muted>
                New to Sweep: added as named
              </Text>
            )}
          </View>
        </Pressable>
        {row.ticked && row.canHaveAmount ? (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.xs }}>
            <Field
              label={`${name} amount${row.unit ? ` in ${row.unit}` : ''}`}
              hideLabel
              placeholder="Some"
              value={row.amount}
              onChangeText={(amount) => onChange({ amount })}
              keyboardType="decimal-pad"
              maxLength={8}
              style={{ width: 76, paddingHorizontal: t.space.sm, textAlign: 'center' }}
            />
            <Text variant="caption" muted style={{ width: 20 }}>
              {row.unit}
            </Text>
          </View>
        ) : null}
      </View>
      {problem ? (
        <Text variant="caption" danger>
          {`${name}: ${problem}`}
        </Text>
      ) : null}
    </View>
  );
}
