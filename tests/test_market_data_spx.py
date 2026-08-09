from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pandas.testing as pdt
import pytest

from option_pricing_volatility.market_data import (
    MarketDataDownloadError,
    MarketDataNoDataError,
    download_spx_chain,
    spx_chain_path,
)
from option_pricing_volatility.market_data import spx


QUOTE_DATE = "2026-07-15"
TARGET_DTE = 30
STRIKE_LIMIT = 450


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict[str, Any]:
        return self._payload


def _path(raw_dir: Path) -> Path:
    return spx_chain_path(
        QUOTE_DATE,
        TARGET_DTE,
        STRIKE_LIMIT,
        raw_dir=raw_dir,
    )


def test_nonempty_cache_is_read_without_token_or_api_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = pd.DataFrame({"optionSymbol": ["SPXW260814C07500000"], "bid": [1.0]})
    cache_path = _path(tmp_path)
    expected.to_csv(cache_path, index=False)
    monkeypatch.delenv("MARKETDATA_TOKEN", raising=False)

    def unexpected_get(*args: object, **kwargs: object) -> None:
        raise AssertionError("the API must not be called for a nonempty cache")

    monkeypatch.setattr(spx.requests, "get", unexpected_get)
    actual = download_spx_chain(
        QUOTE_DATE,
        TARGET_DTE,
        STRIKE_LIMIT,
        raw_dir=tmp_path,
    )

    pdt.assert_frame_equal(actual, expected)


def test_missing_snapshot_makes_exactly_one_pm_request_then_uses_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    payload = {
        "s": "ok",
        "optionSymbol": ["SPXW260814C07500000"],
        "expiration": [1786737600],
        "side": ["call"],
        "strike": [7500.0],
        "updated": [1784145600],
        "bid": [100.0],
        "ask": [101.0],
        "underlyingPrice": [7572.4102],
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse(payload, status_code=203)

    monkeypatch.setattr(spx.requests, "get", fake_get)
    first = download_spx_chain(
        QUOTE_DATE,
        TARGET_DTE,
        STRIKE_LIMIT,
        raw_dir=tmp_path,
        api_token="test-token",
    )
    second = download_spx_chain(
        QUOTE_DATE,
        TARGET_DTE,
        STRIKE_LIMIT,
        raw_dir=tmp_path,
        api_token="test-token",
    )

    assert len(calls) == 1
    assert calls[0]["url"] == spx.BASE_URL
    assert calls[0]["params"] == {
        "date": QUOTE_DATE,
        "dte": TARGET_DTE,
        "am": "false",
        "pm": "true",
        "strikeLimit": STRIKE_LIMIT,
    }
    assert calls[0]["timeout"] == 60.0
    assert _path(tmp_path).is_file()
    pdt.assert_frame_equal(second, first, check_dtype=False)


def test_no_data_is_a_blocker_and_does_not_create_raw_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    call_count = 0

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        nonlocal call_count
        call_count += 1
        return FakeResponse({"s": "no_data"})

    monkeypatch.setattr(spx.requests, "get", fake_get)
    with pytest.raises(MarketDataNoDataError, match="no_data"):
        download_spx_chain(
            QUOTE_DATE,
            TARGET_DTE,
            STRIKE_LIMIT,
            raw_dir=tmp_path,
            api_token="test-token",
        )

    assert call_count == 1
    assert not _path(tmp_path).exists()


def test_unknown_api_status_is_not_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"s": "unexpected", "optionSymbol": ["unsafe-row"]})

    monkeypatch.setattr(spx.requests, "get", fake_get)
    with pytest.raises(MarketDataDownloadError, match="unexpected status"):
        download_spx_chain(
            QUOTE_DATE,
            TARGET_DTE,
            STRIKE_LIMIT,
            raw_dir=tmp_path,
            api_token="test-token",
        )

    assert not _path(tmp_path).exists()


def test_api_error_does_not_echo_vendor_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    reflected_secret = "reflected-test-token"

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"s": "error", "errmsg": reflected_secret})

    monkeypatch.setattr(spx.requests, "get", fake_get)
    with pytest.raises(MarketDataDownloadError) as error_info:
        download_spx_chain(
            QUOTE_DATE,
            TARGET_DTE,
            STRIKE_LIMIT,
            raw_dir=tmp_path,
            api_token="test-token",
        )

    assert reflected_secret not in str(error_info.value)
    assert not _path(tmp_path).exists()


def test_missing_token_is_a_blocker_before_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("MARKETDATA_TOKEN", raising=False)

    def unexpected_get(*args: object, **kwargs: object) -> None:
        raise AssertionError("the API must not be called without a token")

    monkeypatch.setattr(spx.requests, "get", unexpected_get)
    with pytest.raises(MarketDataDownloadError, match="MARKETDATA_TOKEN"):
        download_spx_chain(
            QUOTE_DATE,
            TARGET_DTE,
            STRIKE_LIMIT,
            raw_dir=tmp_path,
        )
    assert not _path(tmp_path).exists()


def test_empty_raw_file_is_a_blocker_and_is_not_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache_path = _path(tmp_path)
    cache_path.touch()

    def unexpected_get(*args: object, **kwargs: object) -> None:
        raise AssertionError("the API must not be called when a raw path exists")

    monkeypatch.setattr(spx.requests, "get", unexpected_get)
    with pytest.raises(MarketDataDownloadError, match="exists but is empty"):
        download_spx_chain(
            QUOTE_DATE,
            TARGET_DTE,
            STRIKE_LIMIT,
            raw_dir=tmp_path,
            api_token="test-token",
        )
    assert cache_path.stat().st_size == 0
