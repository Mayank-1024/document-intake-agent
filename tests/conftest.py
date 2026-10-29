import json
from pathlib import Path

import pytest

from evals.dataset import DATA, load_cases
from intake.documents import load_path
from intake.scripted_model import answer_from_truth


@pytest.fixture(scope="session")
def cases():
    return {c.doc_id: c for c in load_cases()}


def truth(doc_id: str) -> dict:
    return json.loads((DATA / "truth" / f"{doc_id}.json").read_text())


def doc(doc_id: str):
    return load_path(DATA / truth(doc_id)["file"])


def good_answer(doc_id: str) -> dict:
    return answer_from_truth(truth(doc_id))


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "intake.db"
