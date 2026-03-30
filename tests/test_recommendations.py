"""
Unit tests for the recommendation engine.
These run without a database — pure business logic.
"""
import pytest
from app.schemas.quiz import QuizAnswers
from app.services.recommendation import get_recommendations, build_summary, MAX_RECS


def make_answers(**overrides) -> QuizAnswers:
    defaults = dict(
        energy="great",
        sleep="good",
        stress="low",
        focus="great",
        diet="great",
        activity="moderate",
    )
    defaults.update(overrides)
    return QuizAnswers(**defaults)


class TestRecommendationEngine:

    def test_always_returns_max_recs(self):
        """Even a perfect-health user should get MAX_RECS supplements."""
        recs = get_recommendations(make_answers())
        assert len(recs) == MAX_RECS

    def test_bad_sleep_triggers_magnesium(self):
        recs = get_recommendations(make_answers(sleep="wake"))
        keys = [r.key for r in recs]
        assert "magnesium" in keys

    def test_high_stress_triggers_ashwagandha(self):
        recs = get_recommendations(make_answers(stress="high"))
        keys = [r.key for r in recs]
        assert "ashwagandha" in keys

    def test_low_energy_triggers_vitamin_b(self):
        recs = get_recommendations(make_answers(energy="low"))
        keys = [r.key for r in recs]
        assert "vitamin_b" in keys

    def test_vegan_diet_triggers_iron_b12(self):
        recs = get_recommendations(make_answers(diet="vegan"))
        keys = [r.key for r in recs]
        assert "iron_b12" in keys

    def test_active_user_triggers_creatine(self):
        recs = get_recommendations(make_answers(activity="high"))
        keys = [r.key for r in recs]
        assert "creatine" in keys

    def test_no_duplicate_recommendations(self):
        recs = get_recommendations(make_answers(
            sleep="fall", stress="extreme", energy="low",
            focus="poor", diet="poor", activity="none",
        ))
        keys = [r.key for r in recs]
        assert len(keys) == len(set(keys))

    def test_supplement_info_has_all_fields(self):
        recs = get_recommendations(make_answers())
        for r in recs:
            assert r.key
            assert r.name
            assert r.emoji
            assert r.reason
            assert r.price


class TestSummaryBuilder:

    def test_low_energy_in_summary(self):
        summary = build_summary(make_answers(energy="low"))
        assert "low energy" in summary

    def test_sleep_issue_in_summary(self):
        summary = build_summary(make_answers(sleep="fall"))
        assert "sleep" in summary

    def test_general_wellness_fallback(self):
        summary = build_summary(make_answers())
        assert "general wellness" in summary

    def test_multiple_issues_combined(self):
        summary = build_summary(make_answers(sleep="wake", stress="extreme"))
        assert "sleep" in summary
        assert "stress" in summary
