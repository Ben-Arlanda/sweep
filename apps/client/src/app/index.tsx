import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { API_URL } from '@/lib/config';

type Status = 'checking' | 'ok' | 'unreachable';

export default function HomeScreen() {
  const [status, setStatus] = useState<Status>('checking');

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => setStatus(res.ok ? 'ok' : 'unreachable'))
      .catch(() => setStatus('unreachable'));
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Sweep</Text>
      <Text>API: {status}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  title: { fontSize: 28, fontWeight: '600' },
});
