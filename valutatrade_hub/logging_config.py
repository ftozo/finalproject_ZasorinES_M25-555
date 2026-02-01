"""
Конфигурация логирования для ValutaTrade Hub.

Настройка формата, уровня и ротации логов.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "INFO",
    log_format: str = "string",
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """Настройка системы логирования."""
    # Создаём директорию для логов
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Получаем числовой уровень логирования
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Создаём форматтер
    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            "%(levelname)s %(asctime)s %(name)s - %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    # Настраиваем корневой logger
    root_logger = logging.getLogger("valutatrade_hub")
    root_logger.setLevel(numeric_level)

    # Очищаем существующие обработчики
    root_logger.handlers.clear()

    # Обработчик для файла действий
    actions_handler = RotatingFileHandler(
        log_path / "actions.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    actions_handler.setLevel(numeric_level)
    actions_handler.setFormatter(formatter)
    root_logger.addHandler(actions_handler)

    # Обработчик для файла парсера
    parser_handler = RotatingFileHandler(
        log_path / "parser.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    parser_handler.setLevel(numeric_level)
    parser_handler.setFormatter(formatter)

    parser_logger = logging.getLogger("valutatrade_hub.parser")
    parser_logger.handlers.clear()
    parser_logger.addHandler(parser_handler)

    # Консольный обработчик (для отладки)
    if os.environ.get("VALUTATRADE_DEBUG"):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Получение логгера по имени."""
    return logging.getLogger(f"valutatrade_hub.{name}")


# Инициализация логирования при импорте модуля
_logger = setup_logging()
