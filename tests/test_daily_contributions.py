"""Offline tests for stable daily contribution count retrieval."""

from unittest.mock import Mock

import pytest


# Confirms single-day lookups use a wider calendar and select the exact requested date
def test_daily_contribution_count_uses_wider_calendar_window(gm_module, monkeypatch):
    day = gm_module.dt.date(2026, 7, 30)
    window_start = day - gm_module.dt.timedelta(days=gm_module.DAILY_CONTRIBUTION_LOOKBACK_DAYS - 1)
    contribution_lookup = Mock(return_value={window_start.isoformat(): 99, day.isoformat(): 4})
    monkeypatch.setattr(gm_module, "get_daily_contributions", contribution_lookup)
    assert gm_module.get_daily_contributions_count("misiektoja", day, "token") == 4
    contribution_lookup.assert_called_once_with("misiektoja", window_start, day, "token")


# Confirms an absent requested day is handled as a fetch failure instead of a false zero
def test_daily_contribution_count_rejects_missing_requested_date(gm_module, monkeypatch):
    day = gm_module.dt.date(2026, 7, 30)
    contribution_lookup = Mock(return_value={"2026-07-29": 3})
    monkeypatch.setattr(gm_module, "get_daily_contributions", contribution_lookup)
    with pytest.raises(RuntimeError, match="No contribution count returned for misiektoja on 2026-07-30"):
        gm_module.get_daily_contributions_count("misiektoja", day, "token")
