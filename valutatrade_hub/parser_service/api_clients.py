"""
API-клиенты для получения курсов валют.

Содержит абстракцию BaseApiClient и реализации для CoinGecko и ExchangeRate-API.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.config import get_parser_config

# Пытаемся импортировать requests, если недоступен - используем заглушку
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


logger = get_logger("parser.api_clients")


class BaseApiClient(ABC):
    """
    Абстрактный базовый класс для API-клиентов.

    Определяет единый интерфейс для получения курсов валют.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Название источника данных."""
        pass

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получение курсов валют."""
        pass


class CoinGeckoClient(BaseApiClient):
    """
    Клиент для получения курсов криптовалют от CoinGecko.

    Использует публичный API без необходимости авторизации.
    """

    def __init__(self):
        self._config = get_parser_config()

    @property
    def source_name(self) -> str:
        return "CoinGecko"

    def fetch_rates(self) -> dict[str, float]:
        """Получение курсов криптовалют."""
        if not REQUESTS_AVAILABLE:
            logger.warning("Библиотека requests недоступна, используем заглушку")
            return self._get_mock_rates()

        url = self._config.get_coingecko_url()
        start_time = time.time()

        try:
            response = requests.get(
                url,
                timeout=self._config.REQUEST_TIMEOUT,
                headers={"Accept": "application/json"},
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 429:
                raise ApiRequestError("Превышен лимит запросов к CoinGecko (429)")

            if response.status_code != 200:
                raise ApiRequestError(f"CoinGecko вернул статус {response.status_code}")

            data = response.json()
            return self._parse_response(data, elapsed_ms, response.status_code)

        except requests.exceptions.Timeout:
            raise ApiRequestError("Таймаут при запросе к CoinGecko")
        except requests.exceptions.ConnectionError:
            raise ApiRequestError("Ошибка соединения с CoinGecko")
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка запроса к CoinGecko: {str(e)}")

    def _parse_response(
        self, data: dict[str, Any], elapsed_ms: int, status_code: int
    ) -> dict[str, float]:
        """Парсинг ответа CoinGecko."""
        rates = {}
        base_currency = self._config.BASE_CURRENCY.lower()

        for coingecko_id, prices in data.items():
            code = self._config.get_crypto_code(coingecko_id)
            if code and base_currency in prices:
                pair = f"{code}_{self._config.BASE_CURRENCY}"
                rates[pair] = float(prices[base_currency])

        logger.info(
            f"CoinGecko: получено {len(rates)} курсов за {elapsed_ms}ms (HTTP {status_code})"
        )
        return rates

    def _get_mock_rates(self) -> dict[str, float]:
        """Заглушка с тестовыми данными."""
        return {
            "BTC_USD": 59337.21,
            "ETH_USD": 3720.00,
            "SOL_USD": 145.12,
            "XRP_USD": 0.52,
            "ADA_USD": 0.45,
            "DOGE_USD": 0.082,
            "LTC_USD": 72.50,
        }


class ExchangeRateApiClient(BaseApiClient):
    """
    Клиент для получения курсов фиатных валют от ExchangeRate-API.

    Требует API-ключ, который загружается из переменной окружения.
    """

    def __init__(self):
        self._config = get_parser_config()

    @property
    def source_name(self) -> str:
        return "ExchangeRate-API"

    def fetch_rates(self) -> dict[str, float]:
        """Получение курсов фиатных валют."""
        if not REQUESTS_AVAILABLE:
            logger.warning("Библиотека requests недоступна, используем заглушку")
            return self._get_mock_rates()

        if not self._config.is_api_key_configured():
            logger.warning("API ключ для ExchangeRate-API не настроен, используем заглушку")
            return self._get_mock_rates()

        try:
            url = self._config.get_exchangerate_url()
        except ValueError as e:
            raise ApiRequestError(str(e))

        start_time = time.time()

        try:
            response = requests.get(
                url,
                timeout=self._config.REQUEST_TIMEOUT,
                headers={"Accept": "application/json"},
            )
            elapsed_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 401:
                raise ApiRequestError("Неверный API ключ для ExchangeRate-API")

            if response.status_code == 429:
                raise ApiRequestError("Превышен лимит запросов к ExchangeRate-API (429)")

            if response.status_code != 200:
                raise ApiRequestError(f"ExchangeRate-API вернул статус {response.status_code}")

            data = response.json()

            if data.get("result") != "success":
                raise ApiRequestError(
                    f"ExchangeRate-API вернул ошибку: {data.get('error-type', 'unknown')}"
                )

            return self._parse_response(data, elapsed_ms, response.status_code)

        except requests.exceptions.Timeout:
            raise ApiRequestError("Таймаут при запросе к ExchangeRate-API")
        except requests.exceptions.ConnectionError:
            raise ApiRequestError("Ошибка соединения с ExchangeRate-API")
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка запроса к ExchangeRate-API: {str(e)}")

    def _parse_response(
        self, data: dict[str, Any], elapsed_ms: int, status_code: int
    ) -> dict[str, float]:
        """Парсинг ответа ExchangeRate-API."""
        rates = {}
        api_rates = data.get("conversion_rates", data.get("rates", {}))
        base = self._config.BASE_CURRENCY

        for code in self._config.FIAT_CURRENCIES:
            if code in api_rates and code != base:
                # API возвращает: 1 USD = X FIAT
                # Нам нужно: 1 FIAT = Y USD
                usd_to_fiat = float(api_rates[code])
                if usd_to_fiat != 0:
                    fiat_to_usd = 1.0 / usd_to_fiat
                    pair = f"{code}_{base}"
                    rates[pair] = fiat_to_usd

        logger.info(
            f"ExchangeRate-API: получено {len(rates)} курсов за {elapsed_ms}ms (HTTP {status_code})"
        )
        return rates

    def _get_mock_rates(self) -> dict[str, float]:
        """Заглушка с тестовыми данными."""
        return {
            "EUR_USD": 1.0786,
            "GBP_USD": 1.2650,
            "RUB_USD": 0.01016,
            "JPY_USD": 0.0067,
            "CNY_USD": 0.1380,
            "CHF_USD": 1.1320,
            "CAD_USD": 0.7420,
            "AUD_USD": 0.6530,
        }


class MockApiClient(BaseApiClient):
    """Клиент-заглушка для тестирования без реальных API-запросов."""

    def __init__(self, rates: dict[str, float] | None = None):
        self._rates = rates or {}

    @property
    def source_name(self) -> str:
        return "MockAPI"

    def fetch_rates(self) -> dict[str, float]:
        """Возвращает предустановленные курсы."""
        return self._rates.copy()

    def set_rates(self, rates: dict[str, float]):
        """Устанавливает курсы для возврата."""
        self._rates = rates.copy()
