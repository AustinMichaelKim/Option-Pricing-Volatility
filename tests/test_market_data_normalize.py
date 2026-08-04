from __future__ import annotations

from datetime import date

import pandas as pd
import pandas.testing as pdt
import pytest

from option_pricing_volatility.market_data.normalize import (
    calculate_t_act365f,
    normalize_vendor_iv,
    parse_contract_name,
    preprocess_option_data,
    resolve_expiry_timestamp,
    resolve_quote_timestamp,
)


def _raw_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "contract_code": "B0000001",
        "contract_name": "KOSPI200 C 202608 1,010.0 (day)",
        "close": 10.0,
        "daily_change": 1.0,
        "open": 9.0,
        "high": 11.0,
        "low": 8.0,
        "vendor_IV": 76.0,
        "settlement_price": 10.5,
        "volume": 2,
        "turnover_krw_million": 5,
        "open_interest": 10,
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("name", "option_type", "month", "strike", "session"),
    [
        ("KOSPI200 C 202608 1,010.0 (day)", "call", "202608", 1010.0, "day"),
        ("KOSPI200 P 202609 997.5 (night)", "put", "202609", 997.5, "night"),
        ("KOSPI200 C 202608 625.0 (day)", "call", "202608", 625.0, "day"),
    ],
)
def test_parse_contract_name(
    name: str, option_type: str, month: str, strike: float, session: str
) -> None:
    parsed = parse_contract_name(name)
    assert parsed.option_type == option_type
    assert parsed.contract_month == month
    assert parsed.strike == strike
    assert parsed.market_session == session


def test_invalid_contract_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="INVALID_CONTRACT_NAME"):
        parse_contract_name("not a contract")


@pytest.mark.parametrize(
    ("month", "expected"),
    [("202608", "2026-08-13T15:20:00+09:00"), ("202609", "2026-09-10T15:20:00+09:00")],
)
def test_resolve_expiry_timestamp(month: str, expected: str) -> None:
    assert resolve_expiry_timestamp(month).isoformat() == expected


def test_night_t_is_greater_than_day_t() -> None:
    quote_date = date(2026, 8, 4)
    expiry = resolve_expiry_timestamp("202608")
    day_t = calculate_t_act365f(expiry, resolve_quote_timestamp(quote_date, "day"))
    night_t = calculate_t_act365f(expiry, resolve_quote_timestamp(quote_date, "night"))
    assert night_t > day_t > 0


def test_vendor_iv_percent_is_normalized() -> None:
    assert normalize_vendor_iv(76.0, unit="percent") == pytest.approx(0.76)


def test_preprocess_preserves_rows_and_does_not_mutate_input() -> None:
    raw = pd.DataFrame(
        [
            _raw_row(),
            _raw_row(contract_name="KOSPI200 C 202608 1,010.0 (night)"),
        ]
    )
    original = raw.copy(deep=True)
    result = preprocess_option_data(raw, quote_date=date(2026, 8, 4))
    pdt.assert_frame_equal(raw, original)
    assert len(result) == 2
    assert set(result["market_session"]) == {"day", "night"}


def test_missing_and_zero_close_have_distinct_reasons() -> None:
    raw = pd.DataFrame([_raw_row(close=None), _raw_row(close=0)])
    result = preprocess_option_data(raw, quote_date=date(2026, 8, 4))
    assert "MISSING_CLOSE" in result.iloc[0]["rejection_reasons"]
    assert "NONPOSITIVE_CLOSE" in result.iloc[1]["rejection_reasons"]


def test_nonpositive_t_is_rejected() -> None:
    raw = pd.DataFrame([_raw_row(contract_name="KOSPI200 C 202607 625.0 (day)")])
    result = preprocess_option_data(raw, quote_date=date(2026, 8, 4))
    assert not bool(result.iloc[0]["analysis_eligible"])
    assert "NONPOSITIVE_TTM" in result.iloc[0]["rejection_reasons"]


def test_every_ineligible_row_has_a_reason() -> None:
    raw = pd.DataFrame(
        [
            _raw_row(),
            _raw_row(close=None, volume=0),
            _raw_row(contract_name="invalid", close=1, volume=1),
        ]
    )
    result = preprocess_option_data(raw, quote_date=date(2026, 8, 4))
    rejected = result.loc[~result["analysis_eligible"]]
    assert not rejected.empty
    assert rejected["rejection_reasons"].str.len().gt(0).all()
