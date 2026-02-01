"""
Модуль хранения данных для Parser Service.

Операции чтения/записи курсов в JSON-файлы.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import get_settings
from valutatrade_hub.logging_config import get_logger

logger = get_logger("parser.storage")


class RatesStorage:
    """
    Хранилище курсов валют.

    Управляет двумя файлами:
    - rates.json: текущий кэш для Core Service
    - exchange_rates.json: история всех обновлений
    """

    def __init__(self):
        self._settings = get_settings()
        self._ensure_files()

    def _ensure_files(self):
        """Создание файлов, если они не существуют."""
        data_path = Path(self._settings.get("data_path"))
        data_path.mkdir(parents=True, exist_ok=True)

        rates_file = data_path / "rates.json"
        if not rates_file.exists():
            self._write_json(rates_file, {"pairs": {}, "last_refresh": None})

        history_file = data_path / "exchange_rates.json"
        if not history_file.exists():
            self._write_json(history_file, [])

    def _read_json(self, filepath: Path) -> Any:
        """Безопасное чтение JSON-файла."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _write_json(self, filepath: Path, data: Any):
        """Атомарная запись JSON-файла."""
        filepath = Path(filepath)
        dir_path = filepath.parent

        # Временный файл для атомарности
        fd, temp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    # ==================== rates.json (кэш) ====================

    def get_rates_cache(self) -> dict[str, Any]:
        """Получение текущего кэша курсов."""
        filepath = Path(self._settings.get("rates_file"))
        data = self._read_json(filepath)
        if data is None:
            return {"pairs": {}, "last_refresh": None}
        return data

    def save_rates_cache(self, rates: dict[str, float], source: str = "ParserService"):
        """Сохранение курсов в кэш."""
        filepath = Path(self._settings.get("rates_file"))
        current_time = datetime.now().isoformat()

        # Загружаем текущий кэш
        cache = self.get_rates_cache()
        pairs = cache.get("pairs", {})

        # Обновляем курсы
        for pair, rate in rates.items():
            pairs[pair] = {
                "rate": rate,
                "updated_at": current_time,
                "source": source,
            }

        # Сохраняем
        cache["pairs"] = pairs
        cache["last_refresh"] = current_time
        cache["source"] = source

        self._write_json(filepath, cache)
        logger.info(f"Сохранено {len(rates)} курсов в кэш")

    def update_single_rate(
        self, from_code: str, to_code: str, rate: float, source: str = "ParserService"
    ):
        """Обновление одного курса в кэше."""
        pair = f"{from_code.upper()}_{to_code.upper()}"
        self.save_rates_cache({pair: rate}, source)

    def get_rate_from_cache(self, from_code: str, to_code: str) -> dict | None:
        """Получение курса из кэша."""
        cache = self.get_rates_cache()
        pairs = cache.get("pairs", {})

        pair = f"{from_code.upper()}_{to_code.upper()}"
        if pair in pairs:
            return pairs[pair]

        # Попробуем обратный курс
        reverse_pair = f"{to_code.upper()}_{from_code.upper()}"
        if reverse_pair in pairs:
            reverse_data = pairs[reverse_pair]
            if reverse_data.get("rate"):
                return {
                    "rate": 1.0 / reverse_data["rate"],
                    "updated_at": reverse_data.get("updated_at"),
                    "source": reverse_data.get("source"),
                    "calculated": True,
                }

        return None

    # ==================== exchange_rates.json (история) ====================

    def get_history(self) -> list[dict]:
        """Получение истории курсов."""
        filepath = Path(self._settings.get("exchange_rates_file"))
        data = self._read_json(filepath)
        return data if isinstance(data, list) else []

    def add_history_record(self, record: dict):
        """Добавление записи в историю."""
        filepath = Path(self._settings.get("exchange_rates_file"))
        history = self.get_history()

        # Проверяем дубликаты по id
        record_id = record.get("id")
        if record_id:
            for existing in history:
                if existing.get("id") == record_id:
                    return  # Уже существует

        history.append(record)
        self._write_json(filepath, history)

    def save_rates_to_history(
        self,
        rates: dict[str, float],
        source: str,
        meta: dict[str, Any] | None = None,
    ):
        """Сохранение курсов в историю."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        for pair, rate in rates.items():
            parts = pair.split("_")
            if len(parts) != 2:
                continue

            from_code, to_code = parts
            record_id = f"{pair}_{timestamp}"

            record = {
                "id": record_id,
                "from_currency": from_code,
                "to_currency": to_code,
                "rate": rate,
                "timestamp": timestamp,
                "source": source,
            }

            if meta:
                record["meta"] = meta

            self.add_history_record(record)

        logger.debug(f"Добавлено {len(rates)} записей в историю")

    def get_history_for_pair(self, from_code: str, to_code: str, limit: int = 100) -> list[dict]:
        """Получение истории для конкретной пары."""
        history = self.get_history()
        from_code = from_code.upper()
        to_code = to_code.upper()

        filtered = [
            r
            for r in history
            if r.get("from_currency") == from_code and r.get("to_currency") == to_code
        ]

        # Сортируем по времени (новые первые) и ограничиваем
        filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return filtered[:limit]

    def clear_old_history(self, days: int = 30):
        """Очистка старых записей истории."""

        filepath = Path(self._settings.get("exchange_rates_file"))
        history = self.get_history()

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

        filtered = [r for r in history if r.get("timestamp", "") > cutoff]

        removed = len(history) - len(filtered)
        if removed > 0:
            self._write_json(filepath, filtered)
            logger.info(f"Удалено {removed} старых записей из истории")
