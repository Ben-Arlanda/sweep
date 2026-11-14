import { useAuth, useUser } from '@clerk/expo';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Platform, Share, View } from 'react-native';

import { Button, Card, ErrorText, Text } from '@/components/ui';
import { CabinetCard } from '@/features/cabinet/CabinetCard';
import { ListsCard } from '@/features/lists/ListsCard';
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

  return (
    <>
      <View style={{ gap: t.space.xs }}>
        <Text variant="caption" muted>
          Your Household
        </Text>
        <Text variant="title">{me.household.name}</Text>
      </View>

      <ListsCard />
      <CabinetCard />

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
          variant="danger"
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
        <Button title="Delete account" variant="danger" onPress={() => setConfirming(true)} />
      )}
      <ErrorText message={error} />
    </Card>
  );
}
