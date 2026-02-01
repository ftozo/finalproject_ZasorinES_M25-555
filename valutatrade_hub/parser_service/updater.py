"""
Модуль обновления курсов валют.

Координирует получение данных от всех API-клиентов и их сохранение.
"""

from datetime import datetime
from typing import Any

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import get_logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.storage import RatesStorage

logger = get_logger("parser.updater")


class RatesUpdater:
    """
    Координатор обновления курсов валют.

    Опрашивает все API-клиенты, объединяет данные и сохраняет в хранилище.
    """

    def __init__(
        self,
        clients: list[BaseApiClient] | None = None,
        storage: RatesStorage | None = None,
    ):
        """Инициализация обновителя."""
        self._clients = clients or [CoinGeckoClient(), ExchangeRateApiClient()]
        self._storage = storage or RatesStorage()

    def run_update(self, sources: list[str] | None = None) -> dict[str, Any]:
        """Запуск обновления курсов."""
        logger.info("Начало обновления курсов")
        start_time = datetime.now()

        results = {
            "success": True,
            "sources": {},
            "total_rates": 0,
            "errors": [],
            "started_at": start_time.isoformat(),
        }

        all_rates: dict[str, float] = {}

        for client in self._clients:
            source_name = client.source_name.lower().replace("-", "").replace(" ", "")

            # Фильтрация по источникам
            if sources:
                sources_lower = [s.lower().replace("-", "").replace(" ", "") for s in sources]
                if source_name not in sources_lower:
                    continue

            logger.info(f"Запрос к {client.source_name}...")

            try:
                rates = client.fetch_rates()
                all_rates.update(rates)

                results["sources"][client.source_name] = {
                    "status": "OK",
                    "rates_count": len(rates),
                    "rates": list(rates.keys()),
                }

                logger.info(f"{client.source_name}: получено {len(rates)} курсов")

            except ApiRequestError as e:
                error_msg = str(e)
                results["sources"][client.source_name] = {
                    "status": "ERROR",
                    "error": error_msg,
                }
                results["errors"].append(f"{client.source_name}: {error_msg}")
                results["success"] = False

                logger.error(f"{client.source_name}: {error_msg}")

            except Exception as e:
                error_msg = f"Неожиданная ошибка: {str(e)}"
                results["sources"][client.source_name] = {
                    "status": "ERROR",
                    "error": error_msg,
                }
                results["errors"].append(f"{client.source_name}: {error_msg}")
                results["success"] = False

                logger.exception(f"{client.source_name}: {error_msg}")

        # Сохраняем полученные курсы
        if all_rates:
            self._storage.save_rates_cache(all_rates, "ParserService")
            self._storage.save_rates_to_history(all_rates, "ParserService")
            results["total_rates"] = len(all_rates)
            logger.info(f"Сохранено {len(all_rates)} курсов")
        else:
            logger.warning("Не получено ни одного курса")

        # Финализация
        end_time = datetime.now()
        results["completed_at"] = end_time.isoformat()
        results["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

        # Если хотя бы часть курсов получена, считаем частичным успехом
        if all_rates and results["errors"]:
            results["success"] = "partial"

        return results

    def update_crypto_only(self) -> dict[str, Any]:
        """Обновление только криптовалют."""
        return self.run_update(sources=["coingecko"])

    def update_fiat_only(self) -> dict[str, Any]:
        """Обновление только фиатных валют."""
        return self.run_update(sources=["exchangerateapi"])

    def get_last_update_info(self) -> dict[str, Any]:
        """Получение информации о последнем обновлении."""
        cache = self._storage.get_rates_cache()
        return {
            "last_refresh": cache.get("last_refresh"),
            "source": cache.get("source"),
            "pairs_count": len(cache.get("pairs", {})),
        }


def run_update(sources: list[str] | None = None) -> dict[str, Any]:
    """Удобная функция для запуска обновления."""
    updater = RatesUpdater()
    return updater.run_update(sources)
