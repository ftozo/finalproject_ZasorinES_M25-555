"""
Пользовательские исключения для ValutaTrade Hub.

Модуль содержит иерархию исключений для обработки ошибок в приложении.
"""


class ValutaTradeError(Exception):
    """Базовое исключение для всех ошибок приложения."""

    pass


class InsufficientFundsError(ValutaTradeError):
    """
    Исключение при недостатке средств на счёте.

    Выбрасывается при попытке снять больше средств, чем доступно на кошельке.
    """

    def __init__(self, available: float, required: float, currency_code: str):
        self.available = available
        self.required = required
        self.currency_code = currency_code
        message = (
            f"Недостаточно средств: доступно {available:.4f} {currency_code}, "
            f"требуется {required:.4f} {currency_code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """
    Исключение при неизвестной валюте.

    Выбрасывается когда запрашиваемый код валюты не найден в системе.
    """

    def __init__(self, code: str):
        self.code = code
        message = f"Неизвестная валюта '{code}'"
        super().__init__(message)


class ApiRequestError(ValutaTradeError):
    """
    Исключение при ошибке запроса к внешнему API.

    Выбрасывается при сбоях сетевых запросов или некорректных ответах API.
    """

    def __init__(self, reason: str):
        self.reason = reason
        message = f"Ошибка при обращении к внешнему API: {reason}"
        super().__init__(message)


class UserNotFoundError(ValutaTradeError):
    """Исключение когда пользователь не найден."""

    def __init__(self, username: str):
        self.username = username
        message = f"Пользователь '{username}' не найден"
        super().__init__(message)


class UserAlreadyExistsError(ValutaTradeError):
    """Исключение когда пользователь уже существует."""

    def __init__(self, username: str):
        self.username = username
        message = f"Имя пользователя '{username}' уже занято"
        super().__init__(message)


class InvalidPasswordError(ValutaTradeError):
    """Исключение при неверном пароле."""

    def __init__(self):
        message = "Неверный пароль"
        super().__init__(message)


class ValidationError(ValutaTradeError):
    """Исключение при ошибке валидации данных."""

    def __init__(self, message: str):
        super().__init__(message)


class NotLoggedInError(ValutaTradeError):
    """Исключение когда пользователь не авторизован."""

    def __init__(self):
        message = "Сначала выполните login"
        super().__init__(message)


class WalletNotFoundError(ValutaTradeError):
    """Исключение когда кошелёк не найден."""

    def __init__(self, currency_code: str):
        self.currency_code = currency_code
        message = (
            f"У вас нет кошелька '{currency_code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )
        super().__init__(message)
