/**
 * Reading the agent's reply as it's written.
 *
 * `POST /conversations/{id}/messages` answers with Server-Sent Events (SSE): plain text
 * messages separated by a blank line, each like
 *
 *     event: text
 *     data: {"type":"text","text":"Hi"}
 *
 * The network hands us the body in chunks that can split anywhere, even mid-line, so the
 * parser keeps the unfinished end of each chunk and waits for the rest.
 *
 * Why not the browser's `EventSource`? It can only send GET requests and can't add our
 * Authorization header. And why `expo/fetch`? React Native's built-in fetch waits for the
 * whole body before giving you any of it; Expo's version can stream it, on web too.
 */
import { fetch } from 'expo/fetch';

import { ApiError, getToken } from '@/lib/api/client';
import type { components } from '@/lib/api/schema';
import { API_URL } from '@/lib/config';

export type TurnEvent = components['schemas']['TurnEvents'];

export type SseMessage = { event: string; data: string };

/** Returns a function you feed text chunks to; it gives back every message they finish. */
export function createSseParser() {
  let buffer = '';
  let event = 'message';
  let data: string[] = [];

  return (chunk: string): SseMessage[] => {
    buffer += chunk;
    const done: SseMessage[] = [];
    const lines = buffer.split(/\r?\n/);
    buffer = lines.pop() ?? ''; // the last piece has no line ending yet: keep it for later

    for (const line of lines) {
      if (line === '') {
        // A blank line ends a message. One with no data lines isn't a message.
        if (data.length > 0) done.push({ event, data: data.join('\n') });
        event = 'message';
        data = [];
      } else if (line.startsWith('data:')) {
        data.push(field(line, 'data:'));
      } else if (line.startsWith('event:')) {
        event = field(line, 'event:');
      }
      // Anything else (":" comments, "id:", "retry:") we don't use.
    }
    return done;
  };
}

function field(line: string, name: string) {
  const value = line.slice(name.length);
  return value.startsWith(' ') ? value.slice(1) : value; // one optional space after ":"
}

const KNOWN = new Set(['text', 'tool', 'draft', 'replan', 'proposal', 'done', 'error']);

/**
 * Sends one message and calls `onEvent` for each event as it arrives. Resolves when the
 * turn ends. Always ends with a `done` or `error` event, even if the connection drops.
 *
 * Never retried automatically: the server doesn't recognise a repeat of this request,
 * so a retry would run a second turn (and spend tokens twice).
 */
export async function streamTurn(
  conversationId: string,
  text: string,
  onEvent: (event: TurnEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = await getToken();
  const response = await fetch(`${API_URL}/conversations/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!response.ok) {
    // Access and validation errors come back as ordinary JSON before any streaming.
    const body = (await response.json().catch(() => ({}))) as {
      code?: string;
      detail?: unknown;
    };
    const message = typeof body.detail === 'string' ? body.detail : "Couldn't send that.";
    throw new ApiError(response.status, body.code ?? 'http_error', message);
  }
  if (!response.body) throw new ApiError(0, 'no_stream', "Couldn't read the reply.");

  await readEvents(response.body, onEvent);
}

/** Split out from streamTurn so it can be tested without a network. */
export async function readEvents(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: TurnEvent) => void,
): Promise<void> {
  const reader = body.getReader();
  // `stream: true` matters: an emoji is several bytes, and a chunk can end in the
  // middle of one. The decoder keeps those bytes until the rest arrive.
  const decoder = new TextDecoder();
  const parse = createSseParser();
  let finished = false;

  const handle = (messages: SseMessage[]) => {
    for (const message of messages) {
      let event: TurnEvent;
      try {
        event = JSON.parse(message.data) as TurnEvent;
      } catch {
        continue; // a garbled event shouldn't end the whole reply
      }
      if (!KNOWN.has(event.type)) continue; // from a newer server: skip it
      if (event.type === 'done' || event.type === 'error') finished = true;
      onEvent(event);
    }
  };

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      handle(parse(decoder.decode(value, { stream: true })));
    }
    handle(parse(decoder.decode() + '\n\n')); // flush whatever was left
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error;
    // The connection dropped mid-reply. Fall through to the message below.
  }
  if (!finished) {
    onEvent({
      type: 'error',
      message: 'The connection dropped. Your plan so far is saved.',
    });
  }
}
