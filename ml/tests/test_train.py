"""Tests for the winner-selection rule in ml/train.py.

Deliberately imported lazily inside each test: ml/train.py pulls in pandas,
scikit-learn and xgboost at module level, none of which the rule under test
actually needs.
"""

import pytest

train = pytest.importorskip("ml.train")


def _results(**f1_by_name):
    return {name: {"f1": f1} for name, f1 in f1_by_name.items()}


def test_plain_f1_ranking_when_gap_is_clear():
    winner, note = train.pick_winner(_results(**{"Random Forest": 0.95, "XGBoost": 0.90}))
    assert winner == "Random Forest"
    assert note is None


def test_preferred_model_wins_a_near_tie():
    # The actual shipped numbers: RF edges XGBoost by 0.0005 on F1, well
    # under the tie margin, so the hand-checked model ships instead.
    results = _results(**{"Random Forest": 0.9169326, "XGBoost": 0.9164323})
    winner, note = train.pick_winner(results)
    assert winner == "XGBoost"
    assert note is not None and "tie margin" in note


def test_no_note_when_preferred_model_wins_outright():
    winner, note = train.pick_winner(_results(**{"Random Forest": 0.90, "XGBoost": 0.95}))
    assert winner == "XGBoost"
    assert note is None


def test_tie_break_does_not_apply_across_the_margin():
    # 0.001 exactly is the boundary and is *not* treated as a tie.
    results = _results(**{"Random Forest": 0.9200, "XGBoost": 0.9190})
    winner, _ = train.pick_winner(results)
    assert winner == "Random Forest"
