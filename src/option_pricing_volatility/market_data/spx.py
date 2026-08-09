"""Download one immutable historical SPX option-chain snapshot."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd
import requests


BASE_URL = "https://api.marketdata.app/v1/options/chain/SPX/"
DEFAULT_RAW_DIR = Path("data/raw/marketdata_spx")


class MarketDataDownloadError(RuntimeError):
    """Raised when a requested MarketData snapshot cannot be downloaded safely."""


class MarketDataNoDataError(MarketDataDownloadError):
    """Raised when MarketData reports that the requested snapshot has no data."""


def spx_chain_path(
    quote_date: str,
    target_dte: int,
    strike_limit: int,
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
) -> Path:
    """Return the repository raw-data path for a PM-settled SPX request."""

    return Path(raw_dir) / (
        f"SPX_{quote_date}_dte{target_dte:03d}_pm_sl{strike_limit:03d}.csv"
    )


def download_spx_chain(
    quote_date: str,
    target_dte: int = 30,
    strike_limit: int = 10,
    *,
    raw_dir: str | Path = DEFAULT_RAW_DIR,
    api_token: str | None = None,
    timeout: float = 60.0,
) -> pd.DataFrame:
    """Load or download one historical, PM-settled SPX option chain.

    A nonempty raw CSV is always used as an immutable cache.  An existing empty
    file is treated as a blocker rather than overwritten.  When the file is
    absent, this function makes one HTTP request with the fixed date, DTE and
    strike limit; it never retries with altered request parameters.

    The API token is read from ``MARKETDATA_TOKEN`` only after the cache check.
    It is never printed or included in an exception message.
    """

    try:
        parsed_quote_date = date.fromisoformat(quote_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("quote_date must be an ISO date in YYYY-MM-DD format") from exc
    if parsed_quote_date.isoformat() != quote_date:
        raise ValueError("quote_date must be an ISO date in YYYY-MM-DD format")
    if isinstance(target_dte, bool) or not isinstance(target_dte, int) or target_dte <= 0:
        raise ValueError("target_dte must be a positive integer")
    if (
        isinstance(strike_limit, bool)
        or not isinstance(strike_limit, int)
        or strike_limit <= 0
    ):
        raise ValueError("strike_limit must be a positive integer")

    file_path = spx_chain_path(
        quote_date,
        target_dte,
        strike_limit,
        raw_dir=raw_dir,
    )
    if file_path.exists():
        if file_path.stat().st_size == 0:
            raise MarketDataDownloadError(
                f"raw cache exists but is empty; refusing to call the API or overwrite it: {file_path}"
            )
        print(f"[CACHE] Reading existing raw snapshot: {file_path.name}")
        return pd.read_csv(file_path)

    resolved_token = api_token if api_token is not None else os.getenv("MARKETDATA_TOKEN")
    if not resolved_token:
        raise MarketDataDownloadError(
            "MARKETDATA_TOKEN is not set; the missing raw snapshot cannot be downloaded"
        )

    params = {
        "date": quote_date,
        "dte": target_dte,
        "am": "false",
        "pm": "true",
        "strikeLimit": strike_limit,
    }
    headers = {
        "Authorization": f"Bearer {resolved_token}",
        "Accept": "application/json",
    }
    print(
        "[API CALL] "
        f"date={quote_date}, DTE≈{target_dte}, pm=true, strikeLimit={strike_limit}"
    )
    try:
        response = requests.get(
            BASE_URL,
            headers=headers,
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise MarketDataDownloadError(
            "MarketData request failed; no raw snapshot was written"
        ) from exc

    if response.status_code not in (200, 203):
        raise MarketDataDownloadError(
            f"MarketData request failed with HTTP status {response.status_code}; "
            "no raw snapshot was written"
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise MarketDataDownloadError(
            "MarketData returned invalid JSON; no raw snapshot was written"
        ) from exc
    if not isinstance(payload, dict):
        raise MarketDataDownloadError(
            "MarketData returned an unexpected payload; no raw snapshot was written"
        )

    status = payload.get("s")
    if status == "no_data":
        raise MarketDataNoDataError(
            f"MarketData returned no_data for date={quote_date}, "
            f"dte={target_dte}, strikeLimit={strike_limit}"
        )
    if status == "error":
        raise MarketDataDownloadError(
            "MarketData reported an API error; no raw snapshot was written"
        )
    if status != "ok":
        raise MarketDataDownloadError(
            "MarketData returned an unexpected status; no raw snapshot was written"
        )

    list_columns = {
        key: value for key, value in payload.items() if isinstance(value, list)
    }
    try:
        frame = pd.DataFrame(list_columns)
    except ValueError as exc:
        raise MarketDataDownloadError(
            "MarketData returned inconsistent column lengths; no raw snapshot was written"
        ) from exc
    if frame.empty:
        raise MarketDataNoDataError(
            "MarketData returned no option rows; no raw snapshot was written"
        )

    if "quote_date" not in frame.columns and "quoteDate" not in frame.columns:
        frame.insert(0, "quote_date", quote_date)
    frame["requested_dte"] = target_dte

    file_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_csv(file_path, index=False, mode="x")
    except FileExistsError as exc:
        raise MarketDataDownloadError(
            f"raw path appeared during download; refusing to overwrite it: {file_path}"
        ) from exc
    print(f"[SAVED] {len(frame):,} contracts -> {file_path.name}")
    return frame
