import { router } from 'expo-router';
import { ArrowUp, Sparkles } from 'lucide-react-native';
import { useState } from 'react';
import { TextInput, View } from 'react-native';

import { Icon } from '@/components/Icon';
import { PressableScale } from '@/components/PressableScale';
import { requestAsk } from '@/features/chat/starters';
import { useTheme } from '@/theme/useTheme';

/** Free-text start for the chat: a quiet field, with lime only on the small AI mark. */
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
        minHeight: 50,
        paddingLeft: t.space.md,
        paddingRight: 3,
        borderRadius: t.radius.md + 2,
        borderWidth: 1,
        borderColor: t.colors.border,
        backgroundColor: t.colors.heroField,
      }}
    >
      {/* Lime marks Sweep's AI (the one other place lime is allowed). */}
      <View
        style={{
          width: 26,
          height: 26,
          borderRadius: 8,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: t.colors.action,
        }}
      >
        <Icon icon={Sparkles} size={15} color={t.colors.onAction} />
      </View>
      <TextInput
        accessibilityLabel="Ask Sweep"
        placeholder="Ask Sweep anything…"
        placeholderTextColor={t.colors.textMuted}
        value={text}
        onChangeText={setText}
        maxLength={2000}
        returnKeyType="send"
        submitBehavior="blurAndSubmit"
        onSubmitEditing={send}
        style={[
          t.type.body,
          { flex: 1, minHeight: t.touchTarget, fontSize: 14, lineHeight: 20, color: t.colors.text },
        ]}
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
          borderRadius: t.radius.md,
          alignItems: 'center',
          justifyContent: 'center',
          // Quiet until there's something to send, then a solid navy button.
          backgroundColor: canSend ? t.colors.selected : 'transparent',
        }}
      >
        <Icon
          icon={ArrowUp}
          size={20}
          color={canSend ? t.colors.onSelected : t.colors.textMuted}
          strong
        />
      </PressableScale>
    </View>
  );
}
