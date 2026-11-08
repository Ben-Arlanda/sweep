// EXPO_PUBLIC_* variables are inlined into the app bundle at build time,
// so never put secrets here — anyone can read them from the shipped app.
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';
