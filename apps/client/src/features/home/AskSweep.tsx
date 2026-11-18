import { router } from 'expo-router';
import { ArrowUp, Sparkles } from 'lucide-react-native';
import { useState } from 'react';
import { TextInput, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { requestAsk } from '@/features/chat/starters';
import { useTheme } from '@/theme/useTheme';

/** Free-text start for the chat. Not lime: Plan my week is the screen's one primary. */
export function AskSweep() {
  const t = useTheme();
  const [text, setText] = useState('');
  const canSend = text.trim().length > 0;

  function send() {
    if (!requestAsk(text)) return;
    setText('');
    router.push('/plan');
  }

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: t.space.sm,
        minHeight: t.touchTarget + 12,
        paddingLeft: t.space.lg,
        paddingRight: t.space.xs,
        borderRadius: t.radius.pill,
        backgroundColor: t.colors.heroField,
      }}
    >
      <Icon icon={Sparkles} size={20} color={t.colors.onHero} />
      <TextInput
        accessibilityLabel="Ask Sweep"
        placeholder="Ask Sweep for dinner ideas…"
        placeholderTextColor={t.colors.onHeroMuted}
        value={text}
        onChangeText={setText}
        maxLength={2000}
        returnKeyType="send"
        submitBehavior="blurAndSubmit"
        onSubmitEditing={send}
        style={[t.type.body, { flex: 1, minHeight: t.touchTarget, color: t.colors.onHero }]}
      />
      <PressableScale
        accessibilityRole="button"
        accessibilityLabel="Send to Sweep"
        accessibilityState={{ disabled: !canSend }}
        disabled={!canSend}
        onPress={send}
        style={{
          width: t.touchTarget,
          height: t.touchTarget,
          borderRadius: t.radius.pill,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: t.colors.onHero,
          opacity: canSend ? 1 : 0.35,
        }}
      >
        <Icon icon={ArrowUp} size={20} color={t.colors.heroField} strong />
      </PressableScale>
    </View>
  );
}
