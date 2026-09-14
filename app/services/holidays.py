from datetime import date

import httpx


NAGER_URL = "https://date.nager.at/api/v3/PublicHolidays/2026/BR"


def get_brazilian_holidays() -> set[date]:
    """
    Consulta a API Nager.Date e retorna os feriados brasileiros de 2026.
    """
    try:
        response = httpx.get(NAGER_URL, timeout=10.0)
        response.raise_for_status()

        holidays = {
            date.fromisoformat(item["date"])
            for item in response.json()
        }

        return holidays

    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise RuntimeError(
            "Could not retrieve Brazilian holidays."
        ) from exc


def is_holiday(target_date: date) -> bool:
    return target_date in get_brazilian_holidays()

