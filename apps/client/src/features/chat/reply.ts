export type Span = { text: string; bold: boolean };
export type Block =
  { kind: 'text'; spans: Span[] } | { kind: 'item'; marker: string; spans: Span[] };

/** Only numbered lines, "- " bullets and **bold**: links and images stay text (slice 10). */
export function replyBlocks(reply: string): Block[] {
  const blocks: Block[] = [];
  for (const raw of reply.split('\n')) {
    const line = raw.trim();
    if (!line) continue;
    const numbered = /^(\d{1,2})[.)]\s+(.*)$/.exec(line);
    const bullet = /^[-•*]\s+(.*)$/.exec(line);
    if (numbered) blocks.push({ kind: 'item', marker: numbered[1], spans: spans(numbered[2]) });
    else if (bullet) blocks.push({ kind: 'item', marker: '•', spans: spans(bullet[1]) });
    else blocks.push({ kind: 'text', spans: spans(line) });
  }
  return blocks;
}

function spans(line: string): Span[] {
  const parts = line.split('**');
  if (parts.length % 2 === 0) return [{ text: line, bold: false }]; // an unclosed **
  return parts.map((text, i) => ({ text, bold: i % 2 === 1 })).filter((span) => span.text !== '');
}
