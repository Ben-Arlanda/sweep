"""The File door (slice 4d step 6): one PDF, first 10 pages, never stored.

A PDF with text takes the Paste path, so every line is still checked against the text.
A scanned PDF (no text) goes to the model as a document, and every line is marked Check.
pypdf runs in a child process with a time limit: a hostile PDF can't hang the API.
"""

import io
import time

import httpx
import pypdf
import pytest

from app import errors
from app.pdf_text import MAX_PAGES, read_pdf, rejoin_split_lines, run_isolated
from tests.conftest import FakeIssuer
from tests.fake_model import ScriptedReader
from tests.helpers import create_household
from tests.pdf_fixtures import RAGU_PAGE, locked, make_pdf
from tests.test_recipe_import import reading

pytestmark = pytest.mark.anyio

FILE = "/recipes/imports/file"


# --- Reading the PDF (pypdf, in a child process) ---------------------------------------


def test_split_lines_from_a_print_to_pdf_are_joined_back() -> None:
    # What pypdf gives for a RecipeTin print-out: the rest of a line starts the next one.
    text = "4 x 180g salmon fillets \n, skin on (Note 1)\n1 tsp dijon mustard \n(Note 2)\n1 lemon"
    assert rejoin_split_lines(text) == (
        "4 x 180g salmon fillets, skin on (Note 1)\n1 tsp dijon mustard (Note 2)\n1 lemon"
    )


def test_ordinary_lines_are_left_alone() -> None:
    text = "Ingredients\n500g beef mince\n\n1. Brown the mince."
    assert rejoin_split_lines(text) == text


async def test_a_pdf_with_text_gives_its_text() -> None:
    contents = await read_pdf(make_pdf(RAGU_PAGE))
    assert "500g beef mince" in contents.text
    assert contents.pages == 1


async def test_a_pdf_with_text_gives_its_layout_too() -> None:
    # Placed by position: a print-to-PDF's plain text can put headings above the list
    contents = await read_pdf(make_pdf(["Marinade slather:", "1 tbsp lemon juice"]))
    lines = [line.strip() for line in contents.layout_text.splitlines() if line.strip()]
    assert lines == ["Marinade slather:", "1 tbsp lemon juice"]


async def test_only_the_first_pages_are_read() -> None:
    pages = [[f"Page {n} line"] for n in range(1, MAX_PAGES + 3)]
    contents = await read_pdf(make_pdf(*pages))
    assert f"Page {MAX_PAGES} line" in contents.text
    assert f"Page {MAX_PAGES + 1} line" not in contents.text
    # What a scanned PDF would send the model: just those pages, as a new PDF.
    assert len(pypdf.PdfReader(io.BytesIO(contents.first_pages)).pages) == MAX_PAGES


async def test_a_scanned_pdf_has_no_text() -> None:
    contents = await read_pdf(make_pdf([]))
    assert contents.text.strip() == ""
    assert len(pypdf.PdfReader(io.BytesIO(contents.first_pages)).pages) == 1


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"PK\x03\x04 a zip, or a .docx", "PDF"),
        (b"%PDF-1.7 and then nothing that parses", "couldn't be read"),
        (locked(make_pdf(RAGU_PAGE)), "password"),
        (b"%PDF-" + b"\0" * 10_000_001, "10 MB"),
    ],
)
async def test_bad_files_are_refused_plainly(data: bytes, message: str) -> None:
    with pytest.raises(errors.InvalidInput, match=message):
        await read_pdf(data)


def sleep_forever(seconds: float) -> str:
    time.sleep(seconds)
    return "finished"


def explode() -> str:
    raise ValueError("boom")


def test_a_child_that_takes_too_long_is_killed() -> None:
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        run_isolated(sleep_forever, (30.0,), timeout=1.0)
    assert time.monotonic() - started < 10  # killed, not waited for


def test_a_child_that_fails_says_so() -> None:
    with pytest.raises(RuntimeError, match="ValueError"):
        run_isolated(explode, (), timeout=10.0)
    assert run_isolated(sleep_forever, (0.0,), timeout=10.0) == "finished"


# --- The route -----------------------------------------------------------------------------


async def upload(
    client: httpx.AsyncClient, issuer: FakeIssuer, data: bytes, name: str = "ragu.pdf"
) -> httpx.Response:
    files = {"file": (name, data, "application/pdf")}
    return await client.post(FILE, files=files, headers=issuer.headers("ana"))


async def test_a_text_pdf_takes_the_paste_path(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    lines = ["500g beef mince", "1 onion, finely chopped", "50 saffron threads"]
    reader.answers.append(reading(ingredient_lines=lines))
    response = await upload(client, fake_issuer, make_pdf(RAGU_PAGE))
    assert response.status_code == 200, response.text
    draft = response.json()
    # Checked against the PDF's text, like a paste: the invented line is marked.
    assert [line["check"] for line in draft["lines"]] == [False, False, True]
    [(text, _)] = reader.calls
    assert "500g beef mince" in text
    [layout] = reader.layouts  # to place headings (ADR 0033)
    assert layout is not None and "500g beef mince" in layout
    assert reader.document_calls == []


async def test_a_scanned_pdf_goes_to_the_model_as_a_document(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading())
    response = await upload(client, fake_issuer, make_pdf([], []))
    assert response.status_code == 200, response.text
    assert [line["check"] for line in response.json()["lines"]] == [True, True, True]
    assert reader.calls == []
    [pages] = reader.document_calls
    assert pages == 2  # the pages it was sent


async def test_a_word_file_is_refused_before_the_model(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    response = await upload(client, fake_issuer, b"PK\x03\x04 word", name="ragu.docx")
    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]
    assert (reader.calls, reader.document_calls) == ([], [])


async def test_the_more_than_one_recipe_flag_comes_through(
    client: httpx.AsyncClient, fake_issuer: FakeIssuer, reader: ScriptedReader
) -> None:
    await create_household(client, fake_issuer, "ana")
    reader.answers.append(reading(more_recipes=True))
    response = await upload(client, fake_issuer, make_pdf([]))
    assert response.json()["more_recipes"] is True
