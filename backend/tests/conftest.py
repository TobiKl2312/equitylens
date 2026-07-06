import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def companyfacts() -> dict:
    return json.loads((FIXTURES / "companyfacts_sample.json").read_text())


@pytest.fixture
def submissions() -> dict:
    return json.loads((FIXTURES / "submissions_sample.json").read_text())
