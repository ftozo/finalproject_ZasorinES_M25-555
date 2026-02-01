"""
Модуль иерархии валют.

Содержит абстрактный базовый класс Currency и его наследников
FiatCurrency и CryptoCurrency для работы с разными типами валют.
"""

import re
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """
    Абстрактный базовый класс для всех типов валют.

    Определяет общий интерфейс для работы с валютами.
    """

    def __init__(self, name: str, code: str):
        """Инициализация валюты."""
        if not name or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        code = code.upper().strip()
        if not re.match(r"^[A-Z]{2,5}$", code):
            raise ValueError(f"Код валюты должен содержать 2-5 символов (A-Z), получено: '{code}'")

        self._name = name.strip()
        self._code = code

    @property
    def name(self) -> str:
        """Название валюты."""
        return self._name

    @property
    def code(self) -> str:
        """Код валюты."""
        return self._code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает строковое представление валюты для UI/логов."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code='{self.code}', name='{self.name}')"

    def __str__(self) -> str:
        return self.get_display_info()


class FiatCurrency(Currency):
    """
    Фиатная (традиционная) валюта.

    Расширяет базовый класс информацией о стране-эмитенте.
    """

    def __init__(self, name: str, code: str, issuing_country: str):
        """Инициализация фиатной валюты."""
        super().__init__(name, code)
        if not issuing_country or not issuing_country.strip():
            raise ValueError("Страна-эмитент не может быть пустой")
        self._issuing_country = issuing_country.strip()

    @property
    def issuing_country(self) -> str:
        """Страна-эмитент валюты."""
        return self._issuing_country

    def get_display_info(self) -> str:
        """Возвращает информацию о фиатной валюте."""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """
    Криптовалюта.

    Расширяет базовый класс информацией об алгоритме и рыночной капитализации.
    """

    def __init__(self, name: str, code: str, algorithm: str, market_cap: float = 0.0):
        """
        Инициализация криптовалюты.
        """
        super().__init__(name, code)
        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        self._algorithm = algorithm.strip()
        self._market_cap = max(0.0, float(market_cap))

    @property
    def algorithm(self) -> str:
        """Алгоритм криптовалюты."""
        return self._algorithm

    @property
    def market_cap(self) -> float:
        """Рыночная капитализация."""
        return self._market_cap

    @market_cap.setter
    def market_cap(self, value: float):
        """Установка рыночной капитализации."""
        self._market_cap = max(0.0, float(value))

    def get_display_info(self) -> str:
        """Возвращает информацию о криптовалюте."""
        mcap_str = f"{self.market_cap:.2e}" if self.market_cap > 0 else "N/A"
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"


# Реестр поддерживаемых валют
_CURRENCY_REGISTRY: dict[str, Currency] = {}


def _init_currency_registry():
    """Инициализация реестра валют с предопределёнными значениями."""
    global _CURRENCY_REGISTRY

    # Фиатные валюты
    fiat_currencies = [
        FiatCurrency("US Dollar", "USD", "United States"),
        FiatCurrency("Euro", "EUR", "Eurozone"),
        FiatCurrency("British Pound", "GBP", "United Kingdom"),
        FiatCurrency("Russian Ruble", "RUB", "Russia"),
        FiatCurrency("Japanese Yen", "JPY", "Japan"),
        FiatCurrency("Chinese Yuan", "CNY", "China"),
        FiatCurrency("Swiss Franc", "CHF", "Switzerland"),
        FiatCurrency("Canadian Dollar", "CAD", "Canada"),
        FiatCurrency("Australian Dollar", "AUD", "Australia"),
    ]

    # Криптовалюты
    crypto_currencies = [
        CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
        CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
        CryptoCurrency("Solana", "SOL", "Proof of History", 8.0e10),
        CryptoCurrency("Ripple", "XRP", "RPCA", 3.0e10),
        CryptoCurrency("Cardano", "ADA", "Ouroboros", 2.0e10),
        CryptoCurrency("Dogecoin", "DOGE", "Scrypt", 1.5e10),
        CryptoCurrency("Litecoin", "LTC", "Scrypt", 8.0e9),
    ]

    for currency in fiat_currencies + crypto_currencies:
        _CURRENCY_REGISTRY[currency.code] = currency


# Инициализация реестра при импорте модуля
_init_currency_registry()


def get_currency(code: str) -> Currency:
    """Получение валюты по коду из реестра."""
    code = code.upper().strip()
    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)
    return _CURRENCY_REGISTRY[code]


def register_currency(currency: Currency):
    """Добавление валюты в реестр."""
    _CURRENCY_REGISTRY[currency.code] = currency


def get_all_currencies() -> list[Currency]:
    """Возвращает список всех зарегистрированных валют."""
    return list(_CURRENCY_REGISTRY.values())


def get_fiat_currencies() -> list[FiatCurrency]:
    """Возвращает список всех фиатных валют."""
    return [c for c in _CURRENCY_REGISTRY.values() if isinstance(c, FiatCurrency)]


def get_crypto_currencies() -> list[CryptoCurrency]:
    """Возвращает список всех криптовалют."""
    return [c for c in _CURRENCY_REGISTRY.values() if isinstance(c, CryptoCurrency)]


def is_currency_supported(code: str) -> bool:
    """Проверяет, поддерживается ли валюта."""
    return code.upper().strip() in _CURRENCY_REGISTRY
