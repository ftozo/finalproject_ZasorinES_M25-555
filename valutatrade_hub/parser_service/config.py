"""
Конфигурация Parser Service.

Содержит настройки API и параметры обновления курсов.
"""

import os
from dataclasses import dataclass, field


@dataclass
class ParserConfig:
    """
    Конфигурация сервиса парсинга курсов.

    Attributes:
        EXCHANGERATE_API_KEY: Ключ API для ExchangeRate-API
        COINGECKO_URL: URL эндпоинта CoinGecko
        EXCHANGERATE_API_URL: URL эндпоинта ExchangeRate-API
        BASE_CURRENCY: Базовая валюта для запросов
        FIAT_CURRENCIES: Список фиатных валют
        CRYPTO_CURRENCIES: Список криптовалют
        CRYPTO_ID_MAP: Соответствие кодов и ID для CoinGecko
        REQUEST_TIMEOUT: Таймаут запросов в секундах
    """

    # Ключ загружается из переменной окружения
    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "cef594f80d359bbab342a418")
    )

    # Эндпоинты API
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # Базовая валюта
    BASE_CURRENCY: str = "USD"

    # Списки валют для отслеживания
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB", "JPY", "CNY", "CHF", "CAD", "AUD")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "LTC")

    # Соответствие кодов криптовалют и ID для CoinGecko
    CRYPTO_ID_MAP: dict = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
            "XRP": "ripple",
            "ADA": "cardano",
            "DOGE": "dogecoin",
            "LTC": "litecoin",
        }
    )

    # Сетевые параметры
    REQUEST_TIMEOUT: int = 10

    # Пути к файлам (устанавливаются динамически)
    RATES_FILE_PATH: str = "data/rates.json"
    HISTORY_FILE_PATH: str = "data/exchange_rates.json"

    def get_coingecko_url(self) -> str:
        """Формирует полный URL для запроса к CoinGecko."""
        ids = ",".join(self.CRYPTO_ID_MAP.values())
        return f"{self.COINGECKO_URL}?ids={ids}&vs_currencies=usd"

    def get_exchangerate_url(self) -> str:
        """Формирует полный URL для запроса к ExchangeRate-API."""
        if not self.EXCHANGERATE_API_KEY:
            raise ValueError(
                "API ключ для ExchangeRate-API не установлен. "
                "Установите переменную окружения EXCHANGERATE_API_KEY"
            )
        return (
            f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{self.BASE_CURRENCY}"
        )

    def is_api_key_configured(self) -> bool:
        """Проверяет, настроен ли API ключ."""
        return bool(self.EXCHANGERATE_API_KEY)

    def get_crypto_id(self, code: str) -> str | None:
        """Получает ID криптовалюты для CoinGecko по коду."""
        return self.CRYPTO_ID_MAP.get(code.upper())

    def get_crypto_code(self, coingecko_id: str) -> str | None:
        """Получает код криптовалюты по ID CoinGecko."""
        for code, cg_id in self.CRYPTO_ID_MAP.items():
            if cg_id == coingecko_id:
                return code
        return None


# Глобальный экземпляр конфигурации
_config = None


def get_parser_config() -> ParserConfig:
    """Получение экземпляра конфигурации."""
    global _config
    if _config is None:
        _config = ParserConfig()
    return _config
