"""
Модуль работы с базой данных (JSON-хранилище).

Содержит DatabaseManager - синглтон для операций с файлами данных.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.infra.settings import get_settings


class DatabaseManager:
    """
    Синглтон для управления JSON-хранилищем данных.

    Обеспечивает атомарные операции чтения/записи данных.
    """

    _instance = None
    _initialized = False

    def __new__(cls) -> "DatabaseManager":
        """Создание единственного экземпляра."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация менеджера БД."""
        if DatabaseManager._initialized:
            return

        self._settings = get_settings()
        self._ensure_data_files()

        DatabaseManager._initialized = True

    def _ensure_data_files(self):
        """Создание файлов данных, если они не существуют."""
        data_path = Path(self._settings.get("data_path"))
        data_path.mkdir(parents=True, exist_ok=True)

        # Начальные данные для файлов
        initial_data = {
            "users.json": [],
            "portfolios.json": [],
            "rates.json": {
                "pairs": {},
                "last_refresh": None,
            },
            "exchange_rates.json": [],
        }

        for filename, default_content in initial_data.items():
            filepath = data_path / filename
            if not filepath.exists():
                self._write_json(filepath, default_content)

    def _read_json(self, filepath: Path) -> Any:
        """Безопасное чтение JSON-файла."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _write_json(self, filepath: Path, data: Any):
        """Использует временный файл и переименование для атомарности."""
        filepath = Path(filepath)
        dir_path = filepath.parent

        # Создаём временный файл в той же директории
        fd, temp_path = tempfile.mkstemp(dir=str(dir_path), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)

            # Атомарное переименование
            os.replace(temp_path, filepath)
        except Exception:
            # Удаляем временный файл в случае ошибки
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    # ==================== Операции с пользователями ====================

    def get_all_users(self) -> list[User]:
        """Получение списка всех пользователей."""
        filepath = Path(self._settings.get("users_file"))
        data = self._read_json(filepath) or []
        return [User.from_dict(u) for u in data]

    def get_user_by_username(self, username: str) -> User | None:
        """Получение пользователя по имени."""
        users = self.get_all_users()
        for user in users:
            if user.username.lower() == username.lower():
                return user
        return None

    def get_user_by_id(self, user_id: int) -> User | None:
        """Получение пользователя по ID."""
        users = self.get_all_users()
        for user in users:
            if user.user_id == user_id:
                return user
        return None

    def save_user(self, user: User):
        """Сохранение пользователя (создание или обновление)."""
        filepath = Path(self._settings.get("users_file"))
        data = self._read_json(filepath) or []

        # Ищем существующего пользователя
        found = False
        for i, u in enumerate(data):
            if u.get("user_id") == user.user_id:
                data[i] = user.to_dict()
                found = True
                break

        if not found:
            data.append(user.to_dict())

        self._write_json(filepath, data)

    def get_next_user_id(self) -> int:
        """Получение следующего ID для нового пользователя."""
        users = self.get_all_users()
        if not users:
            return 1
        return max(u.user_id for u in users) + 1

    def user_exists(self, username: str) -> bool:
        """Проверка существования пользователя."""
        return self.get_user_by_username(username) is not None

    # ==================== Операции с портфелями ====================

    def get_portfolio(self, user_id: int) -> Portfolio | None:
        """Получение портфеля пользователя."""
        filepath = Path(self._settings.get("portfolios_file"))
        data = self._read_json(filepath) or []

        for p in data:
            if p.get("user_id") == user_id:
                return Portfolio.from_dict(p)
        return None

    def save_portfolio(self, portfolio: Portfolio):
        """Сохранение портфеля (создание или обновление)."""
        filepath = Path(self._settings.get("portfolios_file"))
        data = self._read_json(filepath) or []

        # Ищем существующий портфель
        found = False
        for i, p in enumerate(data):
            if p.get("user_id") == portfolio.user_id:
                data[i] = portfolio.to_dict()
                found = True
                break

        if not found:
            data.append(portfolio.to_dict())

        self._write_json(filepath, data)

    def create_empty_portfolio(self, user_id: int) -> Portfolio:
        """Создание пустого портфеля для пользователя."""
        portfolio = Portfolio(user_id=user_id)
        self.save_portfolio(portfolio)
        return portfolio

    # ==================== Операции с курсами ====================

    def get_rates(self) -> dict[str, Any]:
        """Получение текущих курсов из кэша."""
        filepath = Path(self._settings.get("rates_file"))
        data = self._read_json(filepath)
        if data is None:
            return {"pairs": {}, "last_refresh": None}
        return data

    def get_rate(self, from_code: str, to_code: str) -> dict | None:
        """Получение курса для конкретной пары."""
        rates = self.get_rates()
        pair = f"{from_code.upper()}_{to_code.upper()}"
        pairs = rates.get("pairs", rates)  # Поддержка обоих форматов

        if pair in pairs:
            return pairs[pair]

        # Попробуем обратный курс
        reverse_pair = f"{to_code.upper()}_{from_code.upper()}"
        if reverse_pair in pairs:
            reverse_data = pairs[reverse_pair]
            if isinstance(reverse_data, dict) and reverse_data.get("rate"):
                return {
                    "rate": 1.0 / reverse_data["rate"],
                    "updated_at": reverse_data.get("updated_at"),
                    "source": reverse_data.get("source"),
                }

        return None

    def save_rates(self, rates: dict[str, Any]):
        """Сохранение курсов в кэш."""
        filepath = Path(self._settings.get("rates_file"))
        self._write_json(filepath, rates)

    def update_rate(self, from_code: str, to_code: str, rate: float, source: str = "Unknown"):
        """Обновление курса для пары валют."""
        rates = self.get_rates()
        pair = f"{from_code.upper()}_{to_code.upper()}"

        if "pairs" not in rates:
            rates = {"pairs": rates, "last_refresh": None}

        rates["pairs"][pair] = {
            "rate": rate,
            "updated_at": datetime.now().isoformat(),
            "source": source,
        }
        rates["last_refresh"] = datetime.now().isoformat()

        self.save_rates(rates)

    # ==================== Операции с историей курсов ====================

    def get_exchange_rates_history(self) -> list[dict]:
        """Получение истории курсов."""
        filepath = Path(self._settings.get("exchange_rates_file"))
        data = self._read_json(filepath)
        return data if isinstance(data, list) else []

    def add_exchange_rate_record(self, record: dict):
        """Добавление записи в историю курсов."""
        filepath = Path(self._settings.get("exchange_rates_file"))
        history = self.get_exchange_rates_history()

        # Проверяем, нет ли уже такой записи
        record_id = record.get("id")
        if record_id:
            for existing in history:
                if existing.get("id") == record_id:
                    return  # Запись уже существует

        history.append(record)
        self._write_json(filepath, history)

    def __repr__(self) -> str:
        return f"DatabaseManager(data_path='{self._settings.get('data_path')}')"


# Удобный доступ к экземпляру
def get_database() -> DatabaseManager:
    """Получение экземпляра DatabaseManager."""
    return DatabaseManager()
