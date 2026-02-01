#!/usr/bin/env python3
"""
ValutaTrade Hub - Главная точка входа.

Запуск приложения:
    poetry run python main.py
    или
    make project
"""

import sys
from pathlib import Path

from valutatrade_hub.cli.interface import CLI
from valutatrade_hub.infra.database import get_database
from valutatrade_hub.infra.settings import get_settings

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """Главная функция запуска приложения."""
    # Инициализация настроек и директорий

    settings = get_settings()
    settings.ensure_directories()

    # Инициализация базы данных
    get_database()

    # Запуск CLI
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
