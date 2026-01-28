from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.schemas import ExplainSuccessionRequest, SuccessionExplanation
from app.ai.service import explain_succession_result, explain_validation_payload
from app.core.database import Base
import app.core.models  # noqa: F401 - ensure models are registered
from app.sources.models import Source
from app.succession.schemas import (
    CustomRule,
    SuccessionEvaluationResult,
    SuccessionReason,
)


def _make_session():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_explain_succession_result_with_mocked_openai():
    """Test AI explanation generation with mocked OpenAI response."""
    result = SuccessionEvaluationResult(
        root_person_id=1,
        candidate_person_id=2,
        rule_type="agnatic",
        status="VALID",
        as_of=None,
        path_person_ids=[1, 2],
        relationship_ids=[10],
        checked_paths=1,
        reasons=[],
        applied_rule=CustomRule(
            allow_female_inheritance=False,
            allow_female_transmission=False,
            allow_adoption=False,
            max_depth=12,
        ),
    )

    mock_response = {
        "summary": "The candidate is valid under agnatic succession rules.",
        "detailed_reasoning": "The lineage path from root person 1 to candidate 2 is a direct male line with no violations.",
        "citations": [
            {
                "category": "applied_rule",
                "description": "Agnatic succession: male-only inheritance and transmission.",
            }
        ],
    }

    with patch("app.ai.service.get_openai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = (
            '{"summary": "The candidate is valid under agnatic succession rules.", '
            '"detailed_reasoning": "The lineage path from root person 1 to candidate 2 is a direct male line with no violations.", '
            '"citations": [{"category": "applied_rule", "description": "Agnatic succession: male-only inheritance and transmission."}]}'
        )
        mock_client.chat.completions.create.return_value = mock_completion
        mock_get_client.return_value = mock_client

        explanation = explain_succession_result(result)

        assert explanation.summary == mock_response["summary"]
        assert explanation.detailed_reasoning == mock_response["detailed_reasoning"]
        assert len(explanation.citations) == 1
        assert explanation.citations[0].category == "applied_rule"

        # Deterministic meta
        assert explanation.confidence == 1.0
        assert explanation.sources == []
        assert explanation.rules_applied["rule_type"] == "agnatic"
        assert explanation.rules_applied["applied_rule"]["allow_female_inheritance"] is False


def test_explain_validation_payload_includes_sources_confidence_and_rules():
    db = _make_session()

    src = Source(
        source_type="law",
        jurisdiction_id=None,
        issued_date=date(1800, 1, 1),
        citation="Test Act 1800",
        url="https://example.invalid/test-act-1800",
        notes=None,
        valid_from=date(1800, 1, 1),
        valid_to=None,
    )
    db.add(src)
    db.commit()

    payload = {
        "kind": "order_validation",
        "result": {
            "classification": "LEGITIMATE",
            "legitimacy_score": 80,
            "fraud_flags": [],
            "factors": {"fons_honorum_valid": True},
            "sources": [src.id],
        },
    }

    with patch("app.ai.service.get_openai_client") as mock_get_client:
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = (
            '{"summary": "Order appears legitimate.", '
            '"detailed_reasoning": "Based on provided factors and evidence.", '
            '"citations": [{"category": "applied_rule", "description": "Used payload.factors and payload.sources."}]}'
        )
        mock_client.chat.completions.create.return_value = mock_completion
        mock_get_client.return_value = mock_client

        explanation = explain_validation_payload(payload, db=db)

    assert explanation.confidence == 0.8
    assert len(explanation.sources) == 1
    assert explanation.sources[0].id == src.id
    assert explanation.sources[0].citation == "Test Act 1800"
    assert explanation.rules_applied["kind"] == "order_validation"


def test_explain_succession_result_no_api_key_returns_deterministic_explanation():
    result = SuccessionEvaluationResult(
        root_person_id=1,
        candidate_person_id=2,
        rule_type="agnatic",
        status="VALID",
        as_of=None,
        path_person_ids=[1, 2],
        relationship_ids=[10],
        checked_paths=1,
        reasons=[],
        applied_rule=CustomRule(),
    )

    with patch("app.ai.service.get_openai_client", return_value=None):
        explanation = explain_succession_result(result)

    assert explanation.confidence == 1.0
    assert explanation.rules_applied["rule_type"] == "agnatic"
    assert "ai unavailable" in explanation.summary.lower()
