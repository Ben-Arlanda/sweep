import { fetch } from 'expo/fetch';

import { createSseParser, readEvents, streamTurn, type TurnEvent } from './sse';

// sse.ts streams with expo/fetch, not the global one.
jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

describe('createSseParser', () => {
  it('reads one whole event', () => {
    const parse = createSseParser();
    expect(parse('event: text\ndata: {"type":"text","text":"Hi"}\n\n')).toEqual([
      { event: 'text', data: '{"type":"text","text":"Hi"}' },
    ]);
  });

  it('holds on to a half-sent event until the rest arrives', () => {
    const parse = createSseParser();
    expect(parse('event: text\nda')).toEqual([]);
    expect(parse('ta: {"type":"text","text":"Hi"}\n')).toEqual([]);
    expect(parse('\n')).toEqual([{ event: 'text', data: '{"type":"text","text":"Hi"}' }]);
  });

  it('reads several events from one chunk', () => {
    const parse = createSseParser();
    const got = parse('event: tool\ndata: 1\n\nevent: done\ndata: 2\n\nevent: te');
    expect(got).toEqual([
      { event: 'tool', data: '1' },
      { event: 'done', data: '2' },
    ]);
  });

  it('accepts \\r\\n line endings and joins multi-line data', () => {
    const parse = createSseParser();
    expect(parse('data: a\r\ndata: b\r\n\r\n')).toEqual([{ event: 'message', data: 'a\nb' }]);
  });

  it('ignores comments and lines it does not know', () => {
    const parse = createSseParser();
    expect(parse(': keep-alive\nid: 7\ndata: x\n\n')).toEqual([{ event: 'message', data: 'x' }]);
  });

  it('skips a blank line with no data', () => {
    const parse = createSseParser();
    expect(parse('\n\nevent: ping\n\n')).toEqual([]);
  });
});

describe('readEvents', () => {
  /** A fake response body that delivers these byte chunks, in order. */
  function body(chunks: Uint8Array[]) {
    return new ReadableStream<Uint8Array>({
      start(controller) {
        chunks.forEach((c) => controller.enqueue(c));
        controller.close();
      },
    });
  }
  const bytes = (s: string) => new TextEncoder().encode(s);

  it('decodes an emoji split across two chunks', async () => {
    const all = bytes(
      'event: text\ndata: {"type":"text","text":"🥕"}\n\nevent: done\ndata: {"type":"done"}\n\n',
    );
    const cut = all.indexOf(0xf0) + 2; // inside the carrot's 4 bytes
    const got: TurnEvent[] = [];
    await readEvents(body([all.slice(0, cut), all.slice(cut)]), (e) => got.push(e));
    expect(got).toEqual([{ type: 'text', text: '🥕' }, { type: 'done' }]);
  });

  it('ends with an error when the stream stops without done', async () => {
    const got: TurnEvent[] = [];
    await readEvents(
      body([bytes('event: tool\ndata: {"type":"tool","name":"get_kitchen"}\n\n')]),
      (e) => got.push(e),
    );
    expect(got.map((e) => e.type)).toEqual(['tool', 'error']);
  });

  it('skips garbled and unknown events', async () => {
    const got: TurnEvent[] = [];
    await readEvents(
      body([bytes('data: {oops\n\ndata: {"type":"future"}\n\ndata: {"type":"done"}\n\n')]),
      (e) => got.push(e),
    );
    expect(got).toEqual([{ type: 'done' }]);
  });
});

describe('streamTurn refused before streaming (slice 10 limits)', () => {
  function refuse(status: number, body: object) {
    jest.mocked(fetch).mockResolvedValue({ ok: false, status, json: async () => body } as never);
  }

  it.each([
    [
      409,
      'turn_in_progress',
      "Sweep is still answering your last message, maybe on another device. Try again when it's done.",
    ],
    [429, 'rate_limited', "That's a lot of messages. Try again in 12 minutes."],
  ])(
    '%i gives the server words, which the chat shows as they are',
    async (status, code, detail) => {
      refuse(status, { code, detail });
      const events: TurnEvent[] = [];
      const sent = streamTurn('c1', 'plan dinners', (e) => events.push(e));
      await expect(sent).rejects.toMatchObject({ status, code, message: detail });
      expect(events).toEqual([]); // no turn started, so no half reply to clean up
    },
  );
});
