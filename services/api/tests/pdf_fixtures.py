"""Tiny PDFs built in code, so tests need no binary files. Each page is a list of
text lines; an empty list makes a page with no text at all, which is how a scanned PDF
looks to a text extractor."""

import io

import pypdf


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(*pages: list[str], hidden: list[str] | None = None) -> bytes:
    """`hidden`: lines drawn invisibly on the first page (text render mode 3). A person
    never sees them, but they're in the text layer, so a text extractor does: the
    trick a hostile PDF uses to slip instructions to a model."""
    page_ids = [4 + 2 * i for i in range(len(pages))]
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for page_id, lines in zip(page_ids, pages, strict=True):
        shown = " ".join(f"({_escape(line)}) Tj T*" for line in lines)
        stream = f"BT /F1 12 Tf 72 720 Td 14 TL {shown} ET" if lines else ""
        if hidden and page_id == page_ids[0]:
            secret = " ".join(f"({_escape(line)}) Tj T*" for line in hidden)
            stream += f" BT 3 Tr /F1 12 Tf 72 300 Td 14 TL {secret} ET"
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1"))
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode())
    out.write(f"startxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def locked(pdf: bytes) -> bytes:
    """The same PDF, password-protected."""
    writer = pypdf.PdfWriter(clone_from=pypdf.PdfReader(io.BytesIO(pdf)))
    writer.encrypt("secret")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


RAGU_PAGE = [
    "Mum's Beef Ragu (serves 4)",
    "500g beef mince",
    "1 onion, finely chopped",
    "Brown the mince, then simmer for 2 hours.",
]
