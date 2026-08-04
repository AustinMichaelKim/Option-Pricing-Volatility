"""Normalize the fixed KRX KOSPI 200 option-chain snapshot.

Times use ``Asia/Seoul`` and time to maturity uses ACT/365F.  Until an
exchange contract master is added, monthly expiries are provisionally resolved
to the second Thursday at 15:20 and are explicitly marked as assumed.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


SEOUL = ZoneInfo("Asia/Seoul")
DAY_COUNT_CONVENTION = "ACT/365F"
EXPIRY_SOURCE = "DERIVED_SECOND_THURSDAY"
QUOTE_TIMESTAMP_POLICY = "session_close_proxy"
OUTPUT_COLUMNS = [
    "contract_code",
    "underlying",
    "option_type",
    "contract_month",
    "expiry_date",
    "expiry_timestamp",
    "expiry_source",
    "expiry_is_assumed",
    "strike",
    "market_session",
    "quote_date",
    "quote_timestamp",
    "quote_timestamp_is_assumed",
    "quote_timestamp_policy",
    "day_count_convention",
    "T",
    "close",
    "target_price",
    "target_price_type",
    "open",
    "high",
    "low",
    "vendor_iv_raw",
    "vendor_implied_volatility",
    "settlement_price",
    "volume",
    "turnover_krw_million",
    "open_interest",
    "analysis_eligible",
    "primary_smile_eligible",
    "quality_flags",
    "rejection_reasons",
]
REQUIRED_RAW_COLUMNS = {
    "contract_code",
    "contract_name",
    "close",
    "open",
    "high",
    "low",
    "vendor_IV",
    "settlement_price",
    "volume",
    "turnover_krw_million",
    "open_interest",
}
_CONTRACT_PATTERN = re.compile(
    r"^(?P<underlying>KOSPI200)\s+"
    r"(?P<option_code>[A-Z])\s+"
    r"(?P<contract_month>\d{6})\s+"
    r"(?P<strike>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s+"
    r"\((?P<market_session>day|night)\)$"
)
_QUOTE_DATE_PATTERN = re.compile(r"(?P<date>\d{8})(?=\.csv$)")


@dataclass(frozen=True)
class ContractParts:
    """Parsed identity fields from a KRX contract name."""

    underlying: str
    option_type: str
    contract_month: str
    strike: float
    market_session: str


def parse_contract_name(contract_name: str) -> ContractParts:
    """Parse one KRX contract name without applying time conventions."""

    if not isinstance(contract_name, str):
        raise ValueError("INVALID_CONTRACT_NAME")
    match = _CONTRACT_PATTERN.fullmatch(contract_name.strip())
    if match is None:
        raise ValueError("INVALID_CONTRACT_NAME")
    option_code = match.group("option_code")
    if option_code not in {"C", "P"}:
        raise ValueError("INVALID_OPTION_TYPE")
    return ContractParts(
        underlying=match.group("underlying"),
        option_type={"C": "call", "P": "put"}[option_code],
        contract_month=match.group("contract_month"),
        strike=float(match.group("strike").replace(",", "")),
        market_session=match.group("market_session"),
    )


def extract_quote_date(source_path: str | Path) -> date:
    """Extract the KRX lookup date encoded as YYYYMMDD in a CSV filename."""

    match = _QUOTE_DATE_PATTERN.search(Path(source_path).name)
    if match is None:
        raise ValueError("source filename must end with a YYYYMMDD date and .csv")
    return datetime.strptime(match.group("date"), "%Y%m%d").date()


def resolve_quote_timestamp(quote_date: date, market_session: str) -> datetime:
    """Return the configured EOD proxy timestamp for a day or night row."""

    session_times = {"day": time(15, 45), "night": time(6, 0)}
    try:
        session_time = session_times[market_session]
    except KeyError as exc:
        raise ValueError(f"unsupported market session: {market_session!r}") from exc
    return datetime.combine(quote_date, session_time, tzinfo=SEOUL)


def resolve_expiry_timestamp(contract_month: str) -> datetime:
    """Provisionally resolve a YYYYMM monthly expiry to second Thursday 15:20."""

    if not re.fullmatch(r"\d{6}", contract_month):
        raise ValueError("UNKNOWN_EXPIRY")
    year, month = int(contract_month[:4]), int(contract_month[4:])
    if month not in range(1, 13):
        raise ValueError("UNKNOWN_EXPIRY")
    month_calendar = calendar.monthcalendar(year, month)
    thursdays = [week[calendar.THURSDAY] for week in month_calendar if week[calendar.THURSDAY]]
    expiry_date = date(year, month, thursdays[1])
    return datetime.combine(expiry_date, time(15, 20), tzinfo=SEOUL)


def calculate_t_act365f(expiry_timestamp: datetime, quote_timestamp: datetime) -> float:
    """Return nonnegative ACT/365F time to maturity in years."""

    if expiry_timestamp.tzinfo is None or quote_timestamp.tzinfo is None:
        raise ValueError("ACT/365F timestamps must be timezone-aware")
    seconds = max(
        (expiry_timestamp.astimezone(ZoneInfo("UTC")) - quote_timestamp.astimezone(ZoneInfo("UTC"))).total_seconds(),
        0.0,
    )
    return seconds / (365.0 * 24.0 * 60.0 * 60.0)


def normalize_vendor_iv(value: object, *, unit: str = "percent") -> float | pd.NA:
    """Normalize vendor IV to decimal units while allowing the raw value to persist."""

    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return pd.NA
    if unit == "percent":
        return float(numeric) / 100.0
    if unit == "decimal":
        return float(numeric)
    raise ValueError("vendor IV unit must be 'percent' or 'decimal'")


def validate_row(row: pd.Series) -> list[str]:
    """Return all first-stage rejection reason codes for one normalized row."""

    reasons = list(row.get("parse_rejection_reasons", []))
    strike = row.get("strike")
    close = row.get("close")
    volume = row.get("volume")
    ttm = row.get("T")
    if pd.notna(strike) and float(strike) <= 0:
        reasons.append("NONPOSITIVE_STRIKE")
    if pd.isna(close):
        reasons.append("MISSING_CLOSE")
    elif float(close) <= 0:
        reasons.append("NONPOSITIVE_CLOSE")
    if pd.isna(volume):
        reasons.append("MISSING_VOLUME")
    elif float(volume) <= 0:
        reasons.append("NONPOSITIVE_VOLUME")
    if "UNKNOWN_EXPIRY" not in reasons:
        if pd.isna(ttm) or float(ttm) <= 0:
            reasons.append("NONPOSITIVE_TTM")
    return list(dict.fromkeys(reasons))


def build_quality_flags(row: pd.Series) -> list[str]:
    """Return non-rejection research and provenance flags for one row."""

    flags = ["ASSUMED_QUOTE_TIMESTAMP"]
    if pd.notna(row.get("target_price")):
        flags.insert(0, "EOD_CLOSE_NOT_MID")
    return flags


def preprocess_option_data(
    raw: pd.DataFrame,
    *,
    quote_date: date,
    vendor_iv_unit: str = "percent",
) -> pd.DataFrame:
    """Return a normalized copy of a KRX option-chain DataFrame.

    ``vendor_iv_unit='percent'`` is the explicit policy for the supplied KRX
    snapshot; the raw vendor value is retained for audit.  The input DataFrame
    is never mutated.
    """

    missing = sorted(REQUIRED_RAW_COLUMNS.difference(raw.columns))
    if missing:
        raise ValueError(f"missing required raw columns: {', '.join(missing)}")
    normalized = raw.copy(deep=True)
    numeric_columns = [
        "close",
        "open",
        "high",
        "low",
        "vendor_IV",
        "settlement_price",
        "volume",
        "turnover_krw_million",
        "open_interest",
    ]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    parsed_records: list[dict[str, object]] = []
    for contract_name in normalized["contract_name"]:
        try:
            parts = parse_contract_name(contract_name)
            parsed_records.append({**parts.__dict__, "parse_rejection_reasons": []})
        except ValueError as exc:
            parsed_records.append(
                {
                    "underlying": pd.NA,
                    "option_type": pd.NA,
                    "contract_month": pd.NA,
                    "strike": pd.NA,
                    "market_session": pd.NA,
                    "parse_rejection_reasons": [str(exc)],
                }
            )
    parsed = pd.DataFrame(parsed_records, index=normalized.index)
    normalized = pd.concat([normalized, parsed], axis=1)

    expiry_timestamps: list[datetime | pd.NaT] = []
    quote_timestamps: list[datetime | pd.NaT] = []
    ttms: list[float | pd.NA] = []
    for index, row in normalized.iterrows():
        expiry_timestamp: datetime | pd.NaT = pd.NaT
        quote_timestamp: datetime | pd.NaT = pd.NaT
        if pd.notna(row["contract_month"]):
            try:
                expiry_timestamp = resolve_expiry_timestamp(str(row["contract_month"]))
            except ValueError:
                row["parse_rejection_reasons"].append("UNKNOWN_EXPIRY")
        if pd.notna(row["market_session"]):
            quote_timestamp = resolve_quote_timestamp(quote_date, str(row["market_session"]))
        expiry_timestamps.append(expiry_timestamp)
        quote_timestamps.append(quote_timestamp)
        if pd.isna(expiry_timestamp) or pd.isna(quote_timestamp):
            ttms.append(pd.NA)
        else:
            ttms.append(calculate_t_act365f(expiry_timestamp, quote_timestamp))

    normalized["expiry_timestamp"] = pd.to_datetime(expiry_timestamps, utc=True)
    normalized["quote_timestamp"] = pd.to_datetime(quote_timestamps, utc=True)
    normalized["expiry_date"] = normalized["expiry_timestamp"].dt.tz_convert(SEOUL).dt.date
    normalized["expiry_source"] = normalized["expiry_timestamp"].notna().map(
        {True: EXPIRY_SOURCE, False: pd.NA}
    )
    normalized["expiry_is_assumed"] = normalized["expiry_timestamp"].notna()
    normalized["quote_date"] = quote_date.isoformat()
    normalized["quote_timestamp_is_assumed"] = normalized["quote_timestamp"].notna()
    normalized["quote_timestamp_policy"] = normalized["quote_timestamp"].notna().map(
        {True: QUOTE_TIMESTAMP_POLICY, False: pd.NA}
    )
    normalized["day_count_convention"] = DAY_COUNT_CONVENTION
    normalized["T"] = pd.array(ttms, dtype="Float64")
    normalized["target_price"] = normalized["close"].where(normalized["close"] > 0)
    normalized["target_price_type"] = normalized["target_price"].notna().map(
        {True: "close", False: pd.NA}
    )
    normalized["vendor_iv_raw"] = normalized["vendor_IV"]
    normalized["vendor_implied_volatility"] = normalized["vendor_IV"].map(
        lambda value: normalize_vendor_iv(value, unit=vendor_iv_unit)
    )
    reason_lists = normalized.apply(validate_row, axis=1)
    normalized["analysis_eligible"] = reason_lists.map(lambda reasons: not reasons)
    normalized["primary_smile_eligible"] = normalized["analysis_eligible"] & normalized[
        "market_session"
    ].eq("day")
    normalized["quality_flags"] = normalized.apply(build_quality_flags, axis=1).map("|".join)
    normalized["rejection_reasons"] = reason_lists.map("|".join)
    return normalized.loc[:, OUTPUT_COLUMNS]


def write_processed_outputs(
    source_path: str | Path,
    output_directory: str | Path,
    *,
    vendor_iv_unit: str = "percent",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read one raw snapshot and write normalized and eligible-only CSV files."""

    source = Path(source_path)
    output_dir = Path(output_directory)
    raw = pd.read_csv(source)
    normalized = preprocess_option_data(
        raw,
        quote_date=extract_quote_date(source),
        vendor_iv_unit=vendor_iv_unit,
    )
    processed = normalized.loc[normalized["analysis_eligible"]].copy()
    date_token = extract_quote_date(source).strftime("%Y%m%d")
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(
        output_dir / f"1st_normalized_kospi_200_option_all_{date_token}.csv",
        index=False,
    )
    processed.to_csv(
        output_dir / f"1st_processed_kospi_200_option_all_{date_token}.csv",
        index=False,
    )
    return normalized, processed
