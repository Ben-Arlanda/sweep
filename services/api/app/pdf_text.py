"""Reading a PDF a Member uploaded (slice 4d, the File door), without trusting it.

PDFs are a famously rich format, and a hostile one can be built to make a parser loop
for ages or eat memory. So pypdf never runs in the API process: `run_isolated` starts a
separate child process, waits at most TIME_LIMIT seconds, and kills it if it isn't done.
(A thread wouldn't do: Python can stop waiting for a thread, but can't stop the thread.)
Killing a process also hands back all of its memory.

Checked before that: it starts with "%PDF-" and is at most 10 MB. Then the child opens
it, refuses a locked one, and reads the first MAX_PAGES pages: their text, and those
pages as a new, smaller PDF (what a scanned PDF sends the model).
"""

import io
import multiprocessing
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import anyio

from app import errors

MAX_PDF_BYTES = 10_000_000
MAX_PAGES = 10
TIME_LIMIT = 10.0  # seconds, for the whole read
MEMORY_LIMIT = 1_000_000_000  # bytes, for the child (where the system enforces it)

UNREADABLE = "That PDF couldn't be read. Try another copy, or paste the recipe text."


@dataclass(frozen=True)
class PdfContents:
    text: str  # from the first MAX_PAGES pages; empty for a scan
    pages: int  # how many were read
    first_pages: bytes  # those pages as their own PDF


class _Locked(Exception):
    pass


# --- Running something in a child process, with a time limit -----------------------------


def _child(conn: Any, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
    try:
        import resource  # Unix only; Linux enforces it, macOS mostly ignores it

        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT, MEMORY_LIMIT))
    except (ImportError, ValueError, OSError):
        pass
    try:
        conn.send(("ok", fn(*args)))
    except _Locked:
        conn.send(("locked", None))
    except BaseException:  # noqa: BLE001 - report anything to the parent, then exit
        conn.send(("error", traceback.format_exc(limit=1)))
    finally:
        conn.close()


def run_isolated(fn: Callable[..., Any], args: tuple[Any, ...], timeout: float) -> Any:
    """fn(*args) in a fresh child process. TimeoutError if it takes longer than
    `timeout` (the child is killed), RuntimeError if it fails. Blocking: call it from a
    worker thread. `fn` must be a module-level function (the child imports it)."""
    # "spawn": a clean new interpreter, not a copy of this one with its open sockets.
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(send, fn, args), daemon=True)
    process.start()
    send.close()  # ours is closed; the child holds its own copy
    try:
        if not receive.poll(timeout):
            raise TimeoutError(f"took longer than {timeout}s")
        try:
            status, value = receive.recv()  # before join: a big result fills the pipe
        except EOFError as error:  # the child died without answering (e.g. out of memory)
            raise RuntimeError("the child process died") from error
    finally:
        if process.is_alive():
            process.kill()
        process.join(timeout=5)
        receive.close()
    if status == "locked":
        raise _Locked
    if status != "ok":
        raise RuntimeError(value)
    return value


# --- Reading the PDF (runs in the child) -------------------------------------------------


def _read(data: bytes, max_pages: int) -> PdfContents:
    import pypdf  # here, so only the child loads it

    reader = pypdf.PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise _Locked
    pages = reader.pages[:max_pages]
    text = "\n".join(page.extract_text() or "" for page in pages)
    writer = pypdf.PdfWriter()
    for page in pages:
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return PdfContents(text=text, pages=len(pages), first_pages=out.getvalue())


async def read_pdf(data: bytes) -> PdfContents:
    if not data.startswith(b"%PDF-"):
        raise errors.InvalidInput("Only PDF files for now. Or paste the recipe text.")
    if len(data) > MAX_PDF_BYTES:
        raise errors.InvalidInput("That PDF is over 10 MB. Try a smaller copy.")
    try:
        result: PdfContents = await anyio.to_thread.run_sync(
            run_isolated, _read, (data, MAX_PAGES), TIME_LIMIT
        )
    except _Locked as error:
        raise errors.InvalidInput(
            "That PDF is password-protected. Save an unlocked copy, or paste the text."
        ) from error
    except (TimeoutError, RuntimeError) as error:
        raise errors.InvalidInput(UNREADABLE) from error
    return result
