"""
Декораторы для ValutaTrade Hub.

Содержит декоратор @log_action для логирования доменных операций.
"""

import functools
import time
from datetime import datetime
from typing import Any, Callable

from valutatrade_hub.core.exceptions import NotLoggedInError
from valutatrade_hub.logging_config import get_logger


def log_action(
    action_name: str | None = None,
    verbose: bool = False,
) -> Callable:
    """
    Декоратор для логирования доменных операций.

    Логирует на уровне INFO следующую информацию:
    - timestamp (ISO)
    - action (название операции)
    - параметры вызова
    - result (OK/ERROR)
    - error_type/error_message при исключениях
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = get_logger("actions")
            operation = action_name or func.__name__.upper()
            timestamp = datetime.now().isoformat()

            # Формируем контекст для логирования
            log_context = {
                "timestamp": timestamp,
                "action": operation,
            }

            # Извлекаем ключевые параметры из kwargs
            if "username" in kwargs:
                log_context["username"] = kwargs["username"]
            if "user_id" in kwargs:
                log_context["user_id"] = kwargs["user_id"]
            if "currency_code" in kwargs:
                log_context["currency"] = kwargs["currency_code"]
            if "amount" in kwargs:
                log_context["amount"] = kwargs["amount"]
            if "from_code" in kwargs:
                log_context["from"] = kwargs["from_code"]
            if "to_code" in kwargs:
                log_context["to"] = kwargs["to_code"]

            # Также проверяем позиционные аргументы для self
            # (первый аргумент методов класса)

            if verbose:
                log_context["args"] = str(args[1:]) if args else "()"
                log_context["kwargs"] = str(kwargs)

            try:
                result = func(*args, **kwargs)
                log_context["result"] = "OK"

                # Для verbose режима добавляем информацию о результате
                if verbose and result is not None:
                    log_context["return_value"] = str(result)[:100]

                # Формируем сообщение лога
                log_message = _format_log_message(log_context)
                logger.info(log_message)

                return result

            except Exception as e:
                log_context["result"] = "ERROR"
                log_context["error_type"] = type(e).__name__
                log_context["error_message"] = str(e)

                log_message = _format_log_message(log_context)
                logger.error(log_message)

                # Пробрасываем исключение дальше
                raise

        return wrapper

    return decorator


def _format_log_message(context: dict[str, Any]) -> str:
    """Форматирование сообщения лога."""
    parts = [context.get("action", "UNKNOWN")]

    if "username" in context:
        parts.append(f"user='{context['username']}'")
    elif "user_id" in context:
        parts.append(f"user_id={context['user_id']}")

    if "currency" in context:
        parts.append(f"currency='{context['currency']}'")

    if "from" in context and "to" in context:
        parts.append(f"pair='{context['from']}'->'{context['to']}'")

    if "amount" in context:
        parts.append(f"amount={context['amount']}")

    parts.append(f"result={context.get('result', 'UNKNOWN')}")

    if context.get("result") == "ERROR":
        parts.append(f"error={context.get('error_type', 'Unknown')}")
        if "error_message" in context:
            parts.append(f"msg='{context['error_message'][:50]}'")

    return " ".join(parts)


def timed(func: Callable) -> Callable:
    """Декоратор для измерения времени выполнения функции."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        logger = get_logger("performance")
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000  # в миллисекундах
            logger.debug(f"{func.__name__} completed in {elapsed:.2f}ms")
            return result
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"{func.__name__} failed after {elapsed:.2f}ms: {e}")
            raise

    return wrapper


def require_login(func: Callable) -> Callable:
    """
    Декоратор для проверки авторизации пользователя.

    Проверяет наличие текущей сессии в объекте self.
    """

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs) -> Any:
        if not hasattr(self, "current_user") or self.current_user is None:
            raise NotLoggedInError()
        return func(self, *args, **kwargs)

    return wrapper
