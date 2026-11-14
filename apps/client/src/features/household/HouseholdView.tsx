import { useAuth, useUser } from '@clerk/expo';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Platform, Share, View } from 'react-native';

import { router } from 'expo-router';

import { Avatar, AvatarStack } from '@/components/Avatar';
import { Button, Card, ErrorText, Highlight, SectionLabel, Text } from '@/components/ui';
import { CabinetTile } from '@/features/cabinet/CabinetTile';
import { RecipesTile } from '@/features/recipes/RecipesTile';
import { ListTiles, NewList } from '@/features/lists/ListTiles';
import type { MeOut } from '@/lib/api/client';
import {
  useCreateInvite,
  useDeleteMyData,
  useHousehold,
  useRemoveMember,
} from '@/lib/api/households';
import { clerkErrorMessage } from '@/lib/clerkErrors';
import { useTheme } from '@/theme/useTheme';

export function HouseholdView({ me }: { me: MeOut }) {
  const t = useTheme();
  const household = useHousehold(true);
  const isOwner = me.member.role === 'owner';

  const firstName = me.member.display_name.split(' ')[0];

  return (
    <>
      {/* Header: the Household as a chip, with everyone in it. */}
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          alignSelf: 'flex-start',
          gap: t.space.sm,
          backgroundColor: t.colors.surface,
          borderRadius: t.radius.pill,
          paddingVertical: 6,
          paddingLeft: 6,
          paddingRight: t.space.md,
          boxShadow: t.shadow.card,
        }}
      >
        <AvatarStack members={household.data?.members ?? [me.member]} size={26} />
        <Text variant="label" style={{ fontFamily: t.fonts.displayBold }}>
          {me.household.name}
        </Text>
      </View>

      <View style={{ gap: t.space.xs }}>
        <Text muted>Hi {firstName}</Text>
        <Text variant="display" accessibilityRole="header">
          What&apos;s <Highlight>cooking?</Highlight>
        </Text>
      </View>

      {/* The board: one pastel tile per list, plus the Cabinet. */}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: t.space.md }}>
        <ListTiles />
        <CabinetTile />
        <RecipesTile />
      </View>
      <NewList />

      <SectionLabel>Household</SectionLabel>
      <Card>
        <Text variant="heading">Members</Text>
        <ErrorText message={household.error?.message} />
        {household.data?.members.map((m) => (
          <MemberRow
            key={m.id}
            name={m.display_name}
            role={m.role}
            isMe={m.id === me.member.id}
            canRemove={isOwner && m.id !== me.member.id}
            memberId={m.id}
          />
        ))}
      </Card>

      {isOwner ? <InviteCard /> : null}
      <AccountCard />
    </>
  );
}

function MemberRow(props: {
  name: string;
  role: string;
  isMe: boolean;
  canRemove: boolean;
  memberId: string;
}) {
  const t = useTheme();
  const remove = useRemoveMember();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: t.space.md }}>
      <Avatar id={props.memberId} name={props.name} size={36} />
      <View style={{ flex: 1 }}>
        <Text>
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
          loading={remove.isPending}
          onPress={() => remove.mutate(props.memberId)}
        />
      ) : null}
    </View>
  );
}

function InviteCard() {
  const invite = useCreateInvite();
  const code = invite.data?.code;

  return (
    <Card>
      <Text variant="heading">Invite someone</Text>
      {code ? (
        <>
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
        </>
      ) : null}
      <ErrorText message={invite.error?.message} />
      <Button
        title={code ? 'New code' : 'Create invite code'}
        variant={code ? 'secondary' : 'primary'}
        loading={invite.isPending}
        onPress={() => invite.mutate()}
      />
    </Card>
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

  return (
    <Card>
      <Text variant="heading">Account</Text>
      <Text variant="caption" muted>
        Signed in as {user?.primaryEmailAddress?.emailAddress}
      </Text>
      {__DEV__ ? (
        <Button
          title="Design system (dev only)"
          variant="ghost"
          onPress={() => router.push('/design')}
        />
      ) : null}
      <Button
        title="Sign out"
        variant="secondary"
        onPress={async () => {
          await signOut();
          queryClient.clear(); // don't leave one person's data cached for the next
        }}
      />
      {confirming ? (
        <>
          <Text danger>
            This permanently deletes your account. If you&apos;re the last Member, the Household
            and everything in it is deleted too.
          </Text>
          <Button
            title="Yes, delete my account"
            variant="danger"
            loading={deleteMyData.isPending}
            onPress={deleteAccount}
          />
          <Button title="Cancel" variant="secondary" onPress={() => setConfirming(false)} />
        </>
      ) : (
        <Button title="Delete account" variant="ghost" onPress={() => setConfirming(true)} />
      )}
      <ErrorText message={error} />
    </Card>
  );
}
