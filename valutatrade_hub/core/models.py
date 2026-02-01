"""
Модуль доменных моделей ValutaTrade Hub.

Содержит основные классы: User, Wallet, Portfolio.
"""

import hashlib
import secrets
from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import (
    InsufficientFundsError,
    ValidationError,
    WalletNotFoundError,
)


class User:
    """
    Класс пользователя системы.

    Хранит информацию о пользователе, включая зашифрованный пароль.
    """

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str | None = None,
        hashed_password: str | None = None,
        salt: str | None = None,
        registration_date: datetime | None = None,
    ):
        """Инициализация пользователя."""
        self._user_id = user_id
        self.username = username  # Используем сеттер для валидации

        if hashed_password and salt:
            # Загрузка существующего пользователя
            self._hashed_password = hashed_password
            self._salt = salt
        elif password:
            # Создание нового пользователя
            self._salt = secrets.token_hex(8)
            self._hashed_password = self._hash_password(password, self._salt)
        else:
            raise ValidationError("Необходимо указать пароль или хешированный пароль с солью")

        self._registration_date = registration_date or datetime.now()

    @property
    def user_id(self) -> int:
        """Уникальный идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str):
        """Установка имени пользователя с валидацией."""
        if not value or not value.strip():
            raise ValidationError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Хешированный пароль."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Соль для хеширования."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Дата регистрации."""
        return self._registration_date

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Хеширование пароля."""
        combined = f"{password}{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()

    @staticmethod
    def validate_password(password: str) -> bool:
        """Валидация пароля."""
        if not password or len(password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов")
        return True

    def verify_password(self, password: str) -> bool:
        """Проверка введённого пароля."""
        hashed = self._hash_password(password, self._salt)
        return hashed == self._hashed_password

    def change_password(self, new_password: str):
        """Изменение пароля пользователя."""
        self.validate_password(new_password)
        self._salt = secrets.token_hex(8)
        self._hashed_password = self._hash_password(new_password, self._salt)

    def get_user_info(self) -> dict[str, Any]:
        """Возвращает информацию о пользователе (без пароля)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        """Сериализация пользователя в словарь для сохранения."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Создание пользователя из словаря."""
        registration_date = data.get("registration_date")
        if isinstance(registration_date, str):
            registration_date = datetime.fromisoformat(registration_date)

        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=registration_date,
        )

    def __repr__(self) -> str:
        return f"User(id={self._user_id}, username='{self._username}')"


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """Инициализация кошелька."""
        if not currency_code or not currency_code.strip():
            raise ValidationError("Код валюты не может быть пустым")
        self._currency_code = currency_code.upper().strip()
        self._balance = 0.0
        self.balance = balance  # Используем сеттер для валидации

    @property
    def currency_code(self) -> str:
        """Код валюты."""
        return self._currency_code

    @property
    def balance(self) -> float:
        """Текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float):
        """Установка баланса с валидацией."""
        if not isinstance(value, (int, float)):
            raise ValidationError("Баланс должен быть числом")
        if value < 0:
            raise ValidationError("Баланс не может быть отрицательным")
        self._balance = float(value)

    def deposit(self, amount: float):
        """Пополнение баланса."""
        if not isinstance(amount, (int, float)):
            raise ValidationError("Сумма должна быть числом")
        if amount <= 0:
            raise ValidationError("Сумма пополнения должна быть положительной")
        self._balance += float(amount)

    def withdraw(self, amount: float):
        """Снятие средств."""
        if not isinstance(amount, (int, float)):
            raise ValidationError("Сумма должна быть числом")
        if amount <= 0:
            raise ValidationError("Сумма снятия должна быть положительной")
        if amount > self._balance:
            raise InsufficientFundsError(
                available=self._balance,
                required=amount,
                currency_code=self._currency_code,
            )
        self._balance -= float(amount)

    def get_balance_info(self) -> str:
        """Возвращает информацию о текущем балансе."""
        return f"{self._currency_code}: {self._balance:.4f}"

    def to_dict(self) -> dict[str, Any]:
        """Сериализация кошелька в словарь."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Wallet":
        """Создание кошелька из словаря."""
        return cls(
            currency_code=data["currency_code"],
            balance=data.get("balance", 0.0),
        )

    def __repr__(self) -> str:
        return f"Wallet({self._currency_code}: {self._balance:.4f})"


class Portfolio:
    """Управление всеми кошельками одного пользователя."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None):
        """Инициализация портфеля."""
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets or {}

    @property
    def user_id(self) -> int:
        """Идентификатор владельца."""
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str, initial_balance: float = 0.0) -> Wallet:
        """Добавление нового кошелька в портфель."""
        currency_code = currency_code.upper().strip()
        if not currency_code:
            raise ValidationError("Код валюты не может быть пустым")

        if currency_code not in self._wallets:
            self._wallets[currency_code] = Wallet(currency_code, initial_balance)
        return self._wallets[currency_code]

    def get_wallet(self, currency_code: str) -> Wallet:
        """Получение кошелька по коду валюты."""
        currency_code = currency_code.upper().strip()
        if currency_code not in self._wallets:
            raise WalletNotFoundError(currency_code)
        return self._wallets[currency_code]

    def has_wallet(self, currency_code: str) -> bool:
        """Проверяет наличие кошелька."""
        return currency_code.upper().strip() in self._wallets

    def get_total_value(
        self, base_currency: str = "USD", rates: dict[str, float] | None = None
    ) -> float:
        """Рассчитывает общую стоимость портфеля в базовой валюте."""
        if rates is None:
            rates = {}

        base_currency = base_currency.upper()
        total = 0.0

        for code, wallet in self._wallets.items():
            if code == base_currency:
                total += wallet.balance
            else:
                # Ищем курс в формате CODE_BASE
                pair = f"{code}_{base_currency}"
                if pair in rates:
                    total += wallet.balance * rates[pair]
                else:
                    # Попробуем обратный курс
                    reverse_pair = f"{base_currency}_{code}"
                    if reverse_pair in rates and rates[reverse_pair] != 0:
                        total += wallet.balance / rates[reverse_pair]
                    # Если курса нет, просто пропускаем

        return total

    def to_dict(self) -> dict[str, Any]:
        """Сериализация портфеля в словарь."""
        return {
            "user_id": self._user_id,
            "wallets": {
                code: {"balance": wallet.balance} for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Portfolio":
        """Создание портфеля из словаря."""
        wallets = {}
        wallets_data = data.get("wallets", {})
        for code, wallet_data in wallets_data.items():
            if isinstance(wallet_data, dict):
                balance = wallet_data.get("balance", 0.0)
            else:
                balance = float(wallet_data)
            wallets[code] = Wallet(code, balance)

        return cls(user_id=data["user_id"], wallets=wallets)

    def __repr__(self) -> str:
        wallet_info = ", ".join(f"{code}: {w.balance:.4f}" for code, w in self._wallets.items())
        return f"Portfolio(user_id={self._user_id}, wallets=[{wallet_info}])"
