"""
Вспомогательные функции для ValutaTrade Hub.

Модуль содержит утилиты для валидации, форматирования и других общих задач.
"""

import re
from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import ValidationError


def validate_currency_code(code: str) -> str:
    """Валидация и нормализация кода валюты."""
    if not code or not code.strip():
        raise ValidationError("Код валюты не может быть пустым")

    code = code.upper().strip()
    if not re.match(r"^[A-Z]{2,5}$", code):
        raise ValidationError(f"Код валюты должен содержать 2-5 букв (A-Z), получено: '{code}'")
    return code


def validate_amount(amount: Any, allow_zero: bool = False) -> float:
    """Валидация суммы."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise ValidationError("'amount' должен быть числом")

    if allow_zero:
        if amount < 0:
            raise ValidationError("'amount' не может быть отрицательным")
    else:
        if amount <= 0:
            raise ValidationError("'amount' должен быть положительным числом")

    return amount


def format_currency(amount: float, currency_code: str, decimals: int = 4) -> str:
    """Форматирование суммы валюты для отображения."""
    return f"{amount:.{decimals}f} {currency_code}"


def format_rate(rate: float, from_code: str, to_code: str) -> str:
    """Форматирование курса валюты."""
    # Для очень маленьких значений используем научную нотацию
    if rate < 0.0001:
        return f"{rate:.8f} {to_code}/{from_code}"
    elif rate < 1:
        return f"{rate:.6f} {to_code}/{from_code}"
    else:
        return f"{rate:.2f} {to_code}/{from_code}"


def parse_datetime(value: str | datetime | None) -> datetime | None:
    """Парсинг даты/времени из строки."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def format_datetime(dt: datetime | None, include_time: bool = True) -> str:
    """Форматирование даты/времени для отображения."""
    if dt is None:
        return "N/A"
    if include_time:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt.strftime("%Y-%m-%d")


def calculate_rate(from_code: str, to_code: str, rates: dict[str, dict]) -> float | None:
    """Вычисление курса между двумя валютами."""
    from_code = from_code.upper()
    to_code = to_code.upper()

    # Тривиальный случай
    if from_code == to_code:
        return 1.0

    # Прямой курс
    direct_pair = f"{from_code}_{to_code}"
    if direct_pair in rates:
        rate_data = rates[direct_pair]
        if isinstance(rate_data, dict):
            return rate_data.get("rate")
        return rate_data

    # Обратный курс
    reverse_pair = f"{to_code}_{from_code}"
    if reverse_pair in rates:
        rate_data = rates[reverse_pair]
        if isinstance(rate_data, dict):
            rate = rate_data.get("rate")
        else:
            rate = rate_data
        if rate and rate != 0:
            return 1.0 / rate

    # Курс через USD (если оба не USD)
    if from_code != "USD" and to_code != "USD":
        from_usd_pair = f"{from_code}_USD"
        to_usd_pair = f"{to_code}_USD"

        from_rate = None
        to_rate = None

        if from_usd_pair in rates:
            rate_data = rates[from_usd_pair]
            from_rate = rate_data.get("rate") if isinstance(rate_data, dict) else rate_data

        if to_usd_pair in rates:
            rate_data = rates[to_usd_pair]
            to_rate = rate_data.get("rate") if isinstance(rate_data, dict) else rate_data

        if from_rate and to_rate and to_rate != 0:
            return from_rate / to_rate

    return None


def get_rate_pair_key(from_code: str, to_code: str) -> str:
    """Формирует ключ для пары валют."""
    return f"{from_code.upper()}_{to_code.upper()}"


def is_rate_fresh(updated_at: datetime | str | None, ttl_seconds: int = 300) -> bool:
    """Проверяет, актуален ли курс."""
    if updated_at is None:
        return False

    if isinstance(updated_at, str):
        updated_at = parse_datetime(updated_at)

    if updated_at is None:
        return False

    age = (datetime.now() - updated_at).total_seconds()
    return age < ttl_seconds


def format_number_with_separators(number: float, decimals: int = 2) -> str:
    """Форматирование числа с разделителями тысяч."""
    return f"{number:,.{decimals}f}"
