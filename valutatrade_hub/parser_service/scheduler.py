"""
Планировщик периодического обновления курсов.

Позволяет настроить автоматическое обновление по расписанию.
"""

import threading
from typing import Callable

from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = get_logger("parser.scheduler")


class RatesScheduler:
    """
    Планировщик периодического обновления курсов.

    Запускает обновление с заданным интервалом в фоновом потоке.
    """

    def __init__(
        self,
        interval_seconds: int = 300,
        updater: RatesUpdater | None = None,
        on_update: Callable[[dict], None] | None = None,
    ):
        """Инициализация планировщика."""
        self._interval = interval_seconds
        self._updater = updater or RatesUpdater()
        self._on_update = on_update

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def is_running(self) -> bool:
        """Проверка, запущен ли планировщик."""
        return self._running

    @property
    def interval(self) -> int:
        """Интервал обновления в секундах."""
        return self._interval

    @interval.setter
    def interval(self, value: int):
        """Установка интервала обновления."""
        if value < 60:
            logger.warning(f"Интервал {value}с слишком мал, установлен минимум 60с")
            value = 60
        self._interval = value

    def start(self):
        """Запуск планировщика."""
        if self._running:
            logger.warning("Планировщик уже запущен")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        logger.info(f"Планировщик запущен с интервалом {self._interval}с")

    def stop(self, timeout: float = 5.0):
        """Остановка планировщика."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        logger.info("Планировщик остановлен")

    def _run_loop(self):
        """Основной цикл планировщика."""
        logger.debug("Цикл планировщика запущен")

        # Первое обновление сразу
        self._do_update()

        while self._running:
            # Ожидаем интервал или сигнал остановки
            if self._stop_event.wait(timeout=self._interval):
                break  # Получен сигнал остановки

            if self._running:
                self._do_update()

        logger.debug("Цикл планировщика завершён")

    def _do_update(self):
        """Выполнение одного обновления."""
        try:
            logger.debug("Запуск планового обновления")
            result = self._updater.run_update()

            if self._on_update:
                try:
                    self._on_update(result)
                except Exception as e:
                    logger.error(f"Ошибка в callback: {e}")

        except Exception as e:
            logger.exception(f"Ошибка при плановом обновлении: {e}")

    def trigger_update(self) -> dict:
        """Принудительный запуск обновления (вне расписания)."""
        logger.info("Принудительное обновление")
        return self._updater.run_update()

    def get_status(self) -> dict:
        """Получение статуса планировщика."""
        last_update = self._updater.get_last_update_info()

        return {
            "running": self._running,
            "interval_seconds": self._interval,
            "last_update": last_update.get("last_refresh"),
            "pairs_count": last_update.get("pairs_count", 0),
        }


# Глобальный экземпляр планировщика
_scheduler: RatesScheduler | None = None


def get_scheduler() -> RatesScheduler:
    """Получение глобального планировщика."""
    global _scheduler
    if _scheduler is None:
        _scheduler = RatesScheduler()
    return _scheduler


def start_scheduler(interval_seconds: int = 300):
    """Запуск глобального планировщика."""
    scheduler = get_scheduler()
    scheduler.interval = interval_seconds
    scheduler.start()


def stop_scheduler():
    """Остановка глобального планировщика."""
    if _scheduler:
        _scheduler.stop()
