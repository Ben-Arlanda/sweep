import { useState } from 'react';

import { Button, Card, ErrorText, Field, Text } from '@/components/ui';
import { useAcceptInvite, useCreateHousehold } from '@/lib/api/households';

/** Signed in, but not in a Household yet: start one, or join with an invite code. */
export function Onboarding({ suggestedName }: { suggestedName: string }) {
  const [displayName, setDisplayName] = useState(suggestedName);
  const [householdName, setHouseholdName] = useState('');
  const [code, setCode] = useState('');
  const create = useCreateHousehold();
  const join = useAcceptInvite();

  return (
    <>
      <Text variant="title">Welcome</Text>
      <Field
        label="Your name"
        value={displayName}
        onChangeText={setDisplayName}
        placeholder="What your Household calls you"
        autoComplete="name"
      />

      <Card>
        <Text variant="heading">Start a Household</Text>
        <Field
          label="Household name"
          value={householdName}
          onChangeText={setHouseholdName}
          placeholder="e.g. The Flat"
        />
        <ErrorText message={create.error?.message} />
        <Button
          title="Create Household"
          loading={create.isPending}
          disabled={!householdName.trim() || !displayName.trim()}
          onPress={() => create.mutate({ name: householdName, display_name: displayName })}
        />
      </Card>

      <Card>
        <Text variant="heading">Join with a code</Text>
        <Field
          label="Invite code"
          value={code}
          onChangeText={setCode}
          placeholder="K7QM2XPA"
          autoCapitalize="characters"
          autoCorrect={false}
        />
        <ErrorText message={join.error?.message} />
        <Button
          title="Join Household"
          variant="secondary"
          loading={join.isPending}
          disabled={!code.trim() || !displayName.trim()}
          onPress={() => join.mutate({ code, displayName })}
        />
      </Card>
    </>
  );
}
