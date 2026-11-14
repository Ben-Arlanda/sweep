/**
 * One screen for both signing in and signing up, by email code only (no passwords).
 *
 * 1. Enter email → we try to sign in. If Clerk says there's no account with that
 *    email, we start a sign-up instead. Either way Clerk emails a 6-digit code.
 * 2. Enter the code → verify → finalize. Finalizing makes the session active, and
 *    the (auth) layout notices `isSignedIn` and redirects into the app.
 */
import { useSignIn, useSignUp } from '@clerk/expo';
import { useState } from 'react';
import { View } from 'react-native';

import { Button, Card, ErrorText, Field, Screen, Text } from '@/components/ui';
import { clerkErrorCodes, clerkErrorMessage } from '@/lib/clerkErrors';

type Mode = 'sign-in' | 'sign-up';

export default function SignInScreen() {
  const { signIn } = useSignIn();
  const { signUp } = useSignUp();

  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [mode, setMode] = useState<Mode | null>(null); // null = still on the email step
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function sendCode() {
    setBusy(true);
    setError(null);
    try {
      const attempt = await signIn.emailCode.sendCode({ emailAddress: email.trim() });
      if (!attempt.error) return setMode('sign-in');

      if (!clerkErrorCodes(attempt.error).includes('form_identifier_not_found')) {
        return setError(clerkErrorMessage(attempt.error));
      }

      // No account yet: sign up with the same email, verified by the same kind of code.
      const created = await signUp.create({ emailAddress: email.trim() });
      if (created.error) return setError(clerkErrorMessage(created.error));
      const sent = await signUp.verifications.sendEmailCode();
      if (sent.error) return setError(clerkErrorMessage(sent.error));
      setMode('sign-up');
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setBusy(true);
    setError(null);
    try {
      if (mode === 'sign-in') {
        const result = await signIn.emailCode.verifyCode({ code: code.trim() });
        if (result.error) return setError(clerkErrorMessage(result.error));
        if (signIn.status !== 'complete') {
          return setError(`Sign-in needs another step (${signIn.status}).`);
        }
        const done = await signIn.finalize();
        if (done.error) setError(clerkErrorMessage(done.error));
      } else {
        const result = await signUp.verifications.verifyEmailCode({ code: code.trim() });
        if (result.error) return setError(clerkErrorMessage(result.error));
        if (signUp.status !== 'complete') {
          return setError(`Sign-up needs more details (${signUp.missingFields.join(', ')}).`);
        }
        const done = await signUp.finalize();
        if (done.error) setError(clerkErrorMessage(done.error));
      }
    } finally {
      setBusy(false);
    }
  }

  function startOver() {
    setMode(null);
    setCode('');
    setError(null);
  }

  return (
    <Screen>
      <View style={{ gap: 4, marginTop: 24 }}>
        <Text variant="title">Sweep</Text>
        <Text muted>Plan the week, shop together.</Text>
      </View>

      <Card>
        {mode === null ? (
          <>
            <Field
              label="Email"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              autoCapitalize="none"
              autoComplete="email"
              keyboardType="email-address"
              inputMode="email"
              onSubmitEditing={sendCode}
            />
            <ErrorText message={error} />
            <Button title="Email me a code" onPress={sendCode} loading={busy} disabled={!email} />
            <Text variant="caption" muted>
              No password needed. New here? The same code creates your account.
            </Text>
          </>
        ) : (
          <>
            <Text>
              We sent a code to <Text variant="label">{email.trim()}</Text>.
            </Text>
            <Field
              label="Code"
              value={code}
              onChangeText={setCode}
              placeholder="123456"
              keyboardType="number-pad"
              inputMode="numeric"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              onSubmitEditing={verify}
            />
            <ErrorText message={error} />
            <Button title="Continue" onPress={verify} loading={busy} disabled={!code} />
            <Button title="Use a different email" variant="secondary" onPress={startOver} />
          </>
        )}
      </Card>

      {/* Clerk mounts its bot-protection challenge here on web sign-ups, if enabled. */}
      <View nativeID="clerk-captcha" />
    </Screen>
  );
}
