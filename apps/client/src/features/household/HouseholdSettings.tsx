import { useAuth, useUser } from '@clerk/expo';
import { useQueryClient } from '@tanstack/react-query';
import { ChevronRight, Plus } from 'lucide-react-native';
import { useState, type ReactNode } from 'react';
import { Platform, Pressable, Share, View } from 'react-native';

import { router } from 'expo-router';

import { Avatar } from '@/components/Avatar';
import { Icon } from '@/components/Icon';
import { Button, ErrorText, Text } from '@/components/ui';
import type { MeOut } from '@/lib/api/client';
import {
  useCreateInvite,
  useDeleteMyData,
  useHousehold,
  useRemoveMember,
} from '@/lib/api/households';
import { clerkErrorMessage } from '@/lib/clerkErrors';
import { useTheme } from '@/theme/useTheme';

/** Household settings: who's in it, inviting someone, preferences, and your account. */
export function HouseholdSettings({ me }: { me: MeOut }) {
  const household = useHousehold(true);
  const isOwner = me.member.role === 'owner';
  return (
    <>
      <Group label="Members">
        <ErrorText message={household.error?.message} />
        {household.data?.members.map((m, i) => (
          <MemberRow
            key={m.id}
            first={i === 0}
            name={m.display_name}
            role={m.role}
            isMe={m.id === me.member.id}
            canRemove={isOwner && m.id !== me.member.id}
            memberId={m.id}
          />
        ))}
        {isOwner ? <InviteRow /> : null}
      </Group>

      <Group label="Preferences">
        <LinkRow
          first
          title="Dietary rules & preferences"
          hint="Allergies and diets Sweep must always follow, plus the food you like"
          onPress={() => router.push('/dietary-rules')}
        />
      </Group>

      <AccountCard />
    </>
  );
}

/** A small uppercase label over a card of rows, like iOS Settings. */
function Group({ label, children }: { label?: string; children: ReactNode }) {
  const t = useTheme();
  return (
    <View style={{ gap: t.space.sm }}>
      {label ? (
        <Text
          variant="caption"
          muted
          accessibilityRole="header"
          style={{
            fontFamily: t.fonts.bold,
            fontSize: 12,
            letterSpacing: 0.7,
            textTransform: 'uppercase',
            paddingLeft: 2,
          }}
        >
          {label}
        </Text>
      ) : null}
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
    </View>
  );
}

function rowStyle(t: ReturnType<typeof useTheme>, first: boolean) {
  return {
    flexDirection: 'row' as const,
    alignItems: 'center' as const,
    gap: t.space.md,
    minHeight: 60,
    paddingVertical: t.space.sm,
    paddingLeft: 14,
    paddingRight: t.space.sm,
    borderTopWidth: first ? 0 : 1,
    borderTopColor: t.colors.border,
  };
}

/** A row that opens another screen: title, a hint under it, and a chevron. */
function LinkRow({
  first,
  title,
  hint,
  onPress,
}: {
  first: boolean;
  title: string;
  hint?: string;
  onPress: () => void;
}) {
  const t = useTheme();
  return (
    <Pressable
      accessibilityRole="link"
      onPress={onPress}
      style={({ pressed }) => [rowStyle(t, first), { opacity: pressed ? 0.7 : 1 }]}
    >
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ fontFamily: t.fonts.medium }}>{title}</Text>
        {hint ? (
          <Text variant="caption" muted>
            {hint}
          </Text>
        ) : null}
      </View>
      <Icon icon={ChevronRight} size={18} color={t.colors.textMuted} />
    </Pressable>
  );
}

function MemberRow(props: {
  first: boolean;
  name: string;
  role: string;
  isMe: boolean;
  canRemove: boolean;
  memberId: string;
}) {
  const t = useTheme();
  const remove = useRemoveMember();
  return (
    <View style={rowStyle(t, props.first)}>
      <Avatar id={props.memberId} name={props.name} size={36} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text variant="label">
          {props.name}
          {props.isMe ? ' (you)' : ''}
        </Text>
        <Text variant="caption" muted>
          {props.role === 'owner' ? 'Owner' : 'Member'}
        </Text>
      </View>
      {props.canRemove ? (
        <Button
          title="Remove"
          accessibilityLabel={`Remove ${props.name} from the Household`}
          variant="danger"
          compact
          tight
          loading={remove.isPending}
          onPress={() => remove.mutate(props.memberId)}
        />
      ) : null}
    </View>
  );
}

/** "+ Invite someone": makes a one-time code and shows it in the row. */
function InviteRow() {
  const t = useTheme();
  const invite = useCreateInvite();
  const code = invite.data?.code;
  return (
    <View style={{ borderTopWidth: 1, borderTopColor: t.colors.border }}>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ busy: invite.isPending }}
        disabled={invite.isPending}
        onPress={() => invite.mutate()}
        style={({ pressed }) => [rowStyle(t, true), { opacity: pressed ? 0.7 : 1 }]}
      >
        <View
          style={{
            width: 36,
            height: 36,
            borderRadius: 18,
            borderWidth: 1.5,
            borderStyle: 'dashed',
            borderColor: t.colors.switchOff,
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Icon icon={Plus} size={18} color={t.colors.text} />
        </View>
        <Text style={{ flex: 1, fontFamily: t.fonts.medium }}>
          {code ? 'New invite code' : 'Invite someone'}
        </Text>
      </Pressable>
      {code ? (
        <View style={{ paddingHorizontal: 14, paddingBottom: t.space.lg, gap: t.space.sm }}>
          <Text variant="title" selectable style={{ letterSpacing: 4 }}>
            {code}
          </Text>
          <Text variant="caption" muted>
            Works once, for 7 days. They enter it after signing in.
          </Text>
          {Platform.OS !== 'web' ? (
            <Button
              title="Share code"
              variant="secondary"
              onPress={() =>
                Share.share({ message: `Join our Household on Sweep with code ${code}` })
              }
            />
          ) : null}
        </View>
      ) : null}
      <View style={{ paddingHorizontal: 14 }}>
        <ErrorText message={invite.error?.message} />
      </View>
    </View>
  );
}

/**
 * Sign out, and delete account (App Store guideline 5.1.1(v)).
 *
 * Deletion order matters: our data first, then the Clerk login. If our API call fails,
 * nothing has changed and the person can retry. Done the other way round, a failure
 * would leave Household data behind for a login that no longer exists.
 */
function AccountCard() {
  const { signOut } = useAuth();
  const { user } = useUser();
  const queryClient = useQueryClient();
  const deleteMyData = useDeleteMyData();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function deleteAccount() {
    setError(null);
    try {
      await deleteMyData.mutateAsync();
    } catch (e) {
      return setError(e instanceof Error ? e.message : 'Could not delete your data.');
    }
    try {
      await user?.delete(); // also ends the session
    } catch (e) {
      // Our data is already gone; the login could not be removed (e.g. account deletion
      // is turned off in the Clerk Dashboard). Sign out so the app is in a clean state.
      setError(`Your Sweep data was deleted, but your login was not: ${clerkErrorMessage(e)}`);
      await signOut();
    }
    queryClient.clear();
  }

  const t = useTheme();
  const signOutNow = async () => {
    await signOut();
    queryClient.clear(); // don't leave one person's data cached for the next
  };
  return (
    <Group label="Account">
      <View style={[rowStyle(t, true), { minHeight: 48 }]}>
        <Text variant="caption" muted style={{ flex: 1 }}>
          Signed in as {user?.primaryEmailAddress?.emailAddress}
        </Text>
      </View>
      {__DEV__ ? (
        <LinkRow
          first={false}
          title="Design system (dev only)"
          onPress={() => router.push('/design')}
        />
      ) : null}
      <Pressable
        accessibilityRole="button"
        onPress={signOutNow}
        style={({ pressed }) => [rowStyle(t, false), { opacity: pressed ? 0.7 : 1 }]}
      >
        <Text style={{ fontFamily: t.fonts.medium }}>Sign out</Text>
      </Pressable>
      {confirming ? (
        <View
          style={{
            padding: 14,
            gap: t.space.sm,
            borderTopWidth: 1,
            borderTopColor: t.colors.border,
          }}
        >
          <Text danger>
            This permanently deletes your account. If you&apos;re the last Member, the Household and
            everything in it is deleted too.
          </Text>
          <Button
            title="Yes, delete my account"
            variant="dangerSolid"
            loading={deleteMyData.isPending}
            onPress={deleteAccount}
          />
          <Button title="Cancel" variant="secondary" onPress={() => setConfirming(false)} />
        </View>
      ) : (
        <Pressable
          accessibilityRole="button"
          onPress={() => setConfirming(true)}
          style={({ pressed }) => [rowStyle(t, false), { opacity: pressed ? 0.7 : 1 }]}
        >
          <Text style={{ fontFamily: t.fonts.medium, color: t.colors.danger }}>Delete account</Text>
        </Pressable>
      )}
      <View style={{ paddingHorizontal: 14 }}>
        <ErrorText message={error} />
      </View>
    </Group>
  );
}
