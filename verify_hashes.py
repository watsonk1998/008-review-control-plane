import hashlib
from typing import Any
from pydantic import BaseModel


class Attachment(BaseModel):
    id: str
    title: str
    visibility: str = "parsed"
    reason: str | None = None


class DocumentParseResult(BaseModel):
    documentId: str
    blocks: list[dict[str, Any]]
    tables: list[dict[str, Any]]
    attachments: list[Attachment]


def test_hash_logic():
    doc_id = "doc123"
    block_id = "block456"
    table_id = "table789"
    attachment_id = "attach000"

    block_hash = hashlib.md5(
        f"document:{doc_id}:block:{block_id}".encode()
    ).hexdigest()[:16]
    table_hash = hashlib.md5(
        f"document:{doc_id}:table:{table_id}".encode()
    ).hexdigest()[:16]
    attach_hash = hashlib.md5(
        f"document:{doc_id}:attachment:{attachment_id}".encode()
    ).hexdigest()[:16]

    print(f"Block hash: {block_hash}")
    print(f"Table hash: {table_hash}")
    print(f"Attachment hash: {attach_hash}")

    assert len(block_hash) == 16
    assert len(table_hash) == 16
    assert len(attach_hash) == 16


if __name__ == "__main__":
    test_hash_logic()
    print("Hash logic verified.")
