"""
Бизнес-логика ValutaTrade Hub.

Модуль содержит use cases для операций с пользователями, портфелями и валютами.
"""

from datetime import datetime
from typing import Any

from valutatrade_hub.core.currencies import get_currency, is_currency_supported
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InvalidPasswordError,
    NotLoggedInError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    calculate_rate,
    is_rate_fresh,
    validate_amount,
    validate_currency_code,
)
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import get_settings


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self):
        self._db = get_database()
        self._current_user: User | None = None

    @property
    def current_user(self) -> User | None:
        """Текущий авторизованный пользователь."""
        return self._current_user

    @log_action("REGISTER")
    def register(self, username: str, password: str) -> User:
        """Регистрация нового пользователя."""
        # Валидация
        if not username or not username.strip():
            raise ValidationError("Имя пользователя не может быть пустым")

        username = username.strip()
        User.validate_password(password)

        # Проверка уникальности
        if self._db.user_exists(username):
            raise UserAlreadyExistsError(username)

        # Создание пользователя
        user_id = self._db.get_next_user_id()
        user = User(
            user_id=user_id,
            username=username,
            password=password,
            registration_date=datetime.now(),
        )

        # Сохранение
        self._db.save_user(user)

        # Создание пустого портфеля
        self._db.create_empty_portfolio(user_id)

        return user

    @log_action("LOGIN")
    def login(self, username: str, password: str) -> User:
        """Авторизация пользователя."""
        user = self._db.get_user_by_username(username)
        if user is None:
            raise UserNotFoundError(username)

        if not user.verify_password(password):
            raise InvalidPasswordError()

        self._current_user = user
        return user

    def logout(self):
        """Выход из системы."""
        self._current_user = None

    def is_logged_in(self) -> bool:
        """Проверка авторизации."""
        return self._current_user is not None

    def get_current_user_id(self) -> int | None:
        """Получение ID текущего пользователя."""
        return self._current_user.user_id if self._current_user else None


class PortfolioService:
    """Сервис для работы с портфелями."""

    def __init__(self, user_service: UserService):
        self._db = get_database()
        self._settings = get_settings()
        self._user_service = user_service

    def _require_login(self) -> User:
        """Проверка авторизации."""
        user = self._user_service.current_user
        if user is None:
            raise NotLoggedInError()
        return user

    def get_portfolio(self, user_id: int | None = None) -> Portfolio:
        """Получение портфеля пользователя."""
        if user_id is None:
            user = self._require_login()
            user_id = user.user_id

        portfolio = self._db.get_portfolio(user_id)
        if portfolio is None:
            portfolio = self._db.create_empty_portfolio(user_id)
        return portfolio

    def get_portfolio_summary(self, base_currency: str = "USD") -> dict[str, Any]:
        """Получение сводки по портфелю."""
        user = self._require_login()
        portfolio = self.get_portfolio(user.user_id)

        # Проверяем валюту
        base_currency = validate_currency_code(base_currency)
        if not is_currency_supported(base_currency):
            raise CurrencyNotFoundError(base_currency)

        # Получаем курсы
        rates_data = self._db.get_rates()
        pairs = rates_data.get("pairs", rates_data)

        # Конвертируем в формат для Portfolio.get_total_value
        rates = {}
        for pair, data in pairs.items():
            if isinstance(data, dict):
                rates[pair] = data.get("rate", 0)
            else:
                rates[pair] = data

        # Формируем сводку
        wallets_info = []
        for code, wallet in portfolio.wallets.items():
            value_in_base = wallet.balance
            if code != base_currency:
                rate = calculate_rate(code, base_currency, pairs)
                if rate:
                    value_in_base = wallet.balance * rate
                else:
                    value_in_base = 0.0

            wallets_info.append(
                {
                    "currency_code": code,
                    "balance": wallet.balance,
                    "value_in_base": value_in_base,
                }
            )

        total = sum(w["value_in_base"] for w in wallets_info)

        return {
            "username": user.username,
            "base_currency": base_currency,
            "wallets": wallets_info,
            "total_value": total,
        }

    @log_action("BUY")
    def buy(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Покупка валюты."""
        user = self._require_login()

        # Валидация
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Проверяем валюту
        currency = get_currency(currency_code)

        # Получаем портфель
        portfolio = self.get_portfolio(user.user_id)

        # Получаем курс
        base_currency = self._settings.get("default_base_currency", "USD")
        rates_data = self._db.get_rates()
        pairs = rates_data.get("pairs", rates_data)
        rate = calculate_rate(currency_code, base_currency, pairs)

        if rate is None and currency_code != base_currency:
            raise ApiRequestError(f"Не удалось получить курс для {currency_code}→{base_currency}")

        # Баланс до операции
        old_balance = 0.0
        if portfolio.has_wallet(currency_code):
            old_balance = portfolio.get_wallet(currency_code).balance

        # Создаём кошелёк если нет
        wallet = portfolio.add_currency(currency_code)
        wallet.deposit(amount)

        # Сохраняем
        self._db.save_portfolio(portfolio)

        # Оценочная стоимость
        estimated_cost = amount * rate if rate else amount

        return {
            "currency_code": currency_code,
            "currency_name": currency.name,
            "amount": amount,
            "rate": rate,
            "base_currency": base_currency,
            "old_balance": old_balance,
            "new_balance": wallet.balance,
            "estimated_cost": estimated_cost,
        }

    @log_action("SELL")
    def sell(self, currency_code: str, amount: float) -> dict[str, Any]:
        """Продажа валюты."""
        user = self._require_login()

        # Валидация
        currency_code = validate_currency_code(currency_code)
        amount = validate_amount(amount)

        # Проверяем валюту
        currency = get_currency(currency_code)

        # Получаем портфель
        portfolio = self.get_portfolio(user.user_id)

        # Проверяем наличие кошелька
        if not portfolio.has_wallet(currency_code):
            raise WalletNotFoundError(currency_code)

        wallet = portfolio.get_wallet(currency_code)
        old_balance = wallet.balance

        # Проверяем баланс и снимаем
        wallet.withdraw(amount)  # Может выбросить InsufficientFundsError

        # Получаем курс
        base_currency = self._settings.get("default_base_currency", "USD")
        rates_data = self._db.get_rates()
        pairs = rates_data.get("pairs", rates_data)
        rate = calculate_rate(currency_code, base_currency, pairs)

        # Сохраняем
        self._db.save_portfolio(portfolio)

        # Оценочная выручка
        estimated_revenue = amount * rate if rate else amount

        return {
            "currency_code": currency_code,
            "currency_name": currency.name,
            "amount": amount,
            "rate": rate,
            "base_currency": base_currency,
            "old_balance": old_balance,
            "new_balance": wallet.balance,
            "estimated_revenue": estimated_revenue,
        }


class RatesService:
    """Сервис для работы с курсами валют."""

    def __init__(self):
        self._db = get_database()
        self._settings = get_settings()

    @log_action("GET_RATE")
    def get_rate(self, from_code: str, to_code: str) -> dict[str, Any]:
        """Получение курса валют."""
        # Валидация
        from_code = validate_currency_code(from_code)
        to_code = validate_currency_code(to_code)

        # Проверяем валюты
        get_currency(from_code)  # Выбросит CurrencyNotFoundError если не найдена
        get_currency(to_code)

        # Тривиальный случай
        if from_code == to_code:
            return {
                "from_code": from_code,
                "to_code": to_code,
                "rate": 1.0,
                "reverse_rate": 1.0,
                "updated_at": datetime.now().isoformat(),
                "fresh": True,
            }

        # Получаем из кэша
        rates_data = self._db.get_rates()
        pairs = rates_data.get("pairs", rates_data)

        # Ищем прямой курс
        pair = f"{from_code}_{to_code}"
        rate_info = pairs.get(pair)

        if rate_info:
            rate = rate_info.get("rate") if isinstance(rate_info, dict) else rate_info
            updated_at = rate_info.get("updated_at") if isinstance(rate_info, dict) else None
            source = rate_info.get("source") if isinstance(rate_info, dict) else "cache"

            ttl = self._settings.get("rates_ttl_seconds", 300)
            fresh = is_rate_fresh(updated_at, ttl)

            return {
                "from_code": from_code,
                "to_code": to_code,
                "rate": rate,
                "reverse_rate": 1.0 / rate if rate else None,
                "updated_at": updated_at,
                "source": source,
                "fresh": fresh,
            }

        # Пробуем обратный курс
        reverse_pair = f"{to_code}_{from_code}"
        reverse_info = pairs.get(reverse_pair)

        if reverse_info:
            reverse_rate = (
                reverse_info.get("rate") if isinstance(reverse_info, dict) else reverse_info
            )
            if reverse_rate and reverse_rate != 0:
                rate = 1.0 / reverse_rate
                updated_at = (
                    reverse_info.get("updated_at") if isinstance(reverse_info, dict) else None
                )

                ttl = self._settings.get("rates_ttl_seconds", 300)
                fresh = is_rate_fresh(updated_at, ttl)

                return {
                    "from_code": from_code,
                    "to_code": to_code,
                    "rate": rate,
                    "reverse_rate": reverse_rate,
                    "updated_at": updated_at,
                    "source": reverse_info.get("source")
                    if isinstance(reverse_info, dict)
                    else "cache",
                    "fresh": fresh,
                }

        # Пробуем через USD
        rate = calculate_rate(from_code, to_code, pairs)
        if rate:
            return {
                "from_code": from_code,
                "to_code": to_code,
                "rate": rate,
                "reverse_rate": 1.0 / rate if rate else None,
                "updated_at": rates_data.get("last_refresh"),
                "source": "calculated",
                "fresh": True,
            }

        raise ApiRequestError(f"Курс {from_code}→{to_code} недоступен. Повторите попытку позже.")

    def get_all_rates(self) -> dict[str, Any]:
        """Получение всех курсов из кэша."""
        return self._db.get_rates()

    def get_rates_for_currency(self, currency_code: str) -> list[dict[str, Any]]:
        """Получение всех курсов для указанной валюты."""
        currency_code = validate_currency_code(currency_code)
        rates_data = self._db.get_rates()
        pairs = rates_data.get("pairs", rates_data)

        results = []
        for pair, data in pairs.items():
            if currency_code in pair:
                from_code, to_code = pair.split("_")
                rate = data.get("rate") if isinstance(data, dict) else data
                updated_at = data.get("updated_at") if isinstance(data, dict) else None

                results.append(
                    {
                        "pair": pair,
                        "from_code": from_code,
                        "to_code": to_code,
                        "rate": rate,
                        "updated_at": updated_at,
                    }
                )

        return results


class ApplicationService:
    """
    Главный сервис приложения.

    Объединяет все сервисы и предоставляет единую точку входа.
    """

    def __init__(self):
        self.users = UserService()
        self.portfolios = PortfolioService(self.users)
        self.rates = RatesService()

    @property
    def current_user(self) -> User | None:
        """Текущий авторизованный пользователь."""
        return self.users.current_user

    def is_logged_in(self) -> bool:
        """Проверка авторизации."""
        return self.users.is_logged_in()
