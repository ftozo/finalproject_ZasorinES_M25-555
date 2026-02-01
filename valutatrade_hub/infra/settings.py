"""
Модуль настроек приложения.

Содержит SettingsLoader - синглтон для управления конфигурацией.
"""

import os
from pathlib import Path
from typing import Any


class SettingsLoader:
    """
    Синглтон для загрузки и кэширования конфигурации проекта.

    Реализован через __new__ для простоты и читабельности.
    Гарантирует единственный экземпляр на всё приложение.
    """

    _instance = None
    _initialized = False

    def __new__(cls) -> "SettingsLoader":
        """Создание единственного экземпляра."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Инициализация настроек (только при первом создании)."""
        if SettingsLoader._initialized:
            return

        self._config: dict[str, Any] = {}
        self._load_defaults()
        self._load_from_env()

        SettingsLoader._initialized = True

    def _load_defaults(self):
        """Загрузка значений по умолчанию."""
        # Определяем базовую директорию проекта
        base_dir = Path(__file__).parent.parent.parent

        self._config = {
            # Пути к файлам данных
            "data_path": str(base_dir / "data"),
            "users_file": str(base_dir / "data" / "users.json"),
            "portfolios_file": str(base_dir / "data" / "portfolios.json"),
            "rates_file": str(base_dir / "data" / "rates.json"),
            "exchange_rates_file": str(base_dir / "data" / "exchange_rates.json"),
            # Настройки логирования
            "log_path": str(base_dir / "logs"),
            "log_level": "INFO",
            "log_format": "string",  # 'string' или 'json'
            # Настройки курсов
            "rates_ttl_seconds": 300,  # 5 минут
            "default_base_currency": "USD",
            # Настройки API
            "request_timeout": 10,
            # Базовая директория
            "base_dir": str(base_dir),
        }

    def _load_from_env(self):
        """Загрузка настроек из переменных окружения."""
        env_mappings = {
            "VALUTATRADE_DATA_PATH": "data_path",
            "VALUTATRADE_LOG_PATH": "log_path",
            "VALUTATRADE_LOG_LEVEL": "log_level",
            "VALUTATRADE_RATES_TTL": "rates_ttl_seconds",
            "VALUTATRADE_BASE_CURRENCY": "default_base_currency",
            "VALUTATRADE_REQUEST_TIMEOUT": "request_timeout",
        }

        for env_key, config_key in env_mappings.items():
            value = os.environ.get(env_key)
            if value is not None:
                # Конвертируем числовые значения
                if config_key in ("rates_ttl_seconds", "request_timeout"):
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                self._config[config_key] = value

        # Обновляем пути к файлам если изменился data_path
        if "VALUTATRADE_DATA_PATH" in os.environ:
            data_path = Path(self._config["data_path"])
            self._config["users_file"] = str(data_path / "users.json")
            self._config["portfolios_file"] = str(data_path / "portfolios.json")
            self._config["rates_file"] = str(data_path / "rates.json")
            self._config["exchange_rates_file"] = str(data_path / "exchange_rates.json")

    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения настройки."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """Установка значения настройки."""
        self._config[key] = value

    def reload(self):
        """Перезагрузка конфигурации."""
        self._config.clear()
        self._load_defaults()
        self._load_from_env()

    def get_all(self) -> dict[str, Any]:
        """Возвращает копию всех настроек."""
        return self._config.copy()

    def ensure_directories(self):
        """Создание необходимых директорий."""
        directories = [
            self.get("data_path"),
            self.get("log_path"),
        ]
        for dir_path in directories:
            if dir_path:
                Path(dir_path).mkdir(parents=True, exist_ok=True)

    def __repr__(self) -> str:
        return f"SettingsLoader(config_keys={list(self._config.keys())})"


# Удобный доступ к экземпляру
def get_settings() -> SettingsLoader:
    """Получение экземпляра SettingsLoader."""
    return SettingsLoader()
