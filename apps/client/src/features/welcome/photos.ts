/** Library recipe photos for the signed-out screens, hotlinked like every recipe photo (ADR 0029). */
const sized = (raw: string) => `${raw}&w=720&h=540&fit=crop&crop=entropy&fm=webp&q=55`;

export const PHOTOS = {
  chanaMasala: sized(
    'https://images.unsplash.com/photo-1617355057919-2aa713486c9c?ixid=M3wxMTM5MTAxfDB8MXxzZWFyY2h8Mnx8Q2hhbmElMjBtYXNhbGF8ZW58MXwwfHx8MTc5NTE0NTY1NHww&ixlib=rb-4.1.0',
  ),
  dhalCurry: sized(
    'https://images.unsplash.com/photo-1743525700011-afac212694d7?ixid=M3wxMTM5MTAxfDB8MXxzZWFyY2h8MXx8U3JpJTIwTGFua2FuJTIwZGhhbCUyMGN1cnJ5fGVufDF8MHx8fDE3OTUxNTI5ODV8MA&ixlib=rb-4.1.0',
  ),
  greekChicken: sized(
    'https://images.unsplash.com/photo-1599161146640-8d60bd2888e3?ixid=M3wxMTM5MTAxfDB8MXxzZWFyY2h8MXx8R3JlZWslMjBsZW1vbiUyMGNoaWNrZW4lMjBhbmQlMjBwb3RhdG9lc3xlbnwxfDB8fHwxNzk1MTU1MTc3fDA&ixlib=rb-4.1.0',
  ),
  lemonOrzo: sized(
    'https://images.unsplash.com/photo-1490990813269-10586274747f?ixid=M3wxMTM5MTAxfDB8MXxzZWFyY2h8MXx8TGVtb24lMjBjaGlja2VuJTIwb3J6b3xlbnwxfDB8fHwxNzk1MTUzMjEyfDA&ixlib=rb-4.1.0',
  ),
} as const;
