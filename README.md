# ValutaTrade Hub

Платформа для отслеживания и симуляции торговли валютами.

## Описание

ValutaTrade Hub — это консольное приложение, имитирующее работу валютного кошелька. Система позволяет пользователям:

- Регистрироваться и авторизовываться
- Управлять виртуальным портфелем фиатных и криптовалют
- Совершать сделки по покупке/продаже валют
- Отслеживать актуальные курсы в реальном времени

## Структура проекта

```
finalproject_ZasorinES/
│  
├── data/
│    ├── users.json             # список пользователей
│    ├── portfolios.json        # портфели и кошельки
│    ├── rates.json             # текущий кэш курсов
│    └── exchange_rates.json    # история курсов
├── valutatrade_hub/
│    ├── __init__.py
│    ├── logging_config.py      # настройка логирования
│    ├── decorators.py          # декораторы (@log_action)
│    ├── core/
│    │    ├── __init__.py
│    │    ├── currencies.py     # иерархия валют (Currency, Fiat, Crypto)
│    │    ├── exceptions.py     # пользовательские исключения
│    │    ├── models.py         # User, Wallet, Portfolio
│    │    ├── usecases.py       # бизнес-логика
│    │    └── utils.py          # вспомогательные функции
│    ├── infra/
│    │    ├── __init__.py
│    │    ├── settings.py       # Singleton SettingsLoader
│    │    └── database.py       # Singleton DatabaseManager
│    ├── parser_service/
│    │    ├── __init__.py
│    │    ├── config.py         # конфигурация API
│    │    ├── api_clients.py    # клиенты CoinGecko и ExchangeRate-API
│    │    ├── storage.py        # хранилище курсов
│    │    ├── updater.py        # обновление курсов
│    │    └── scheduler.py      # планировщик
│    └── cli/
│         ├── __init__.py
│         └── interface.py      # командный интерфейс
│
├── logs/                       # лог-файлы
├── main.py                     # точка входа
├── Makefile
├── poetry.lock
├── pyproject.toml
├── README.md
└── .gitignore
```

## Установка

### Требования

- Python 3.10+
- Poetry

### Установка зависимостей

```bash
make install
# или
poetry install
```

## Запуск

```bash
make project
# или
poetry run python main.py
```

## Команды CLI

| Команда | Аргументы | Описание |
|---------|-----------|----------|
| `register` | `--username <имя> --password <пароль>` | Регистрация нового пользователя |
| `login` | `--username <имя> --password <пароль>` | Вход в систему |
| `logout` | | Выход из системы |
| `whoami` | | Показать текущего пользователя |
| `show-portfolio` | `[--base <валюта>]` | Показать портфель |
| `buy` | `--currency <код> --amount <кол-во>` | Купить валюту |
| `sell` | `--currency <код> --amount <кол-во>` | Продать валюту |
| `get-rate` | `--from <код> --to <код>` | Получить курс валюты |
| `show-rates` | `[--currency <код>] [--top <N>]` | Показать все курсы |
| `update-rates` | `[--source <источник>]` | Обновить курсы из API |
| `currencies` | | Список поддерживаемых валют |
| `help` | | Справка по командам |
| `exit` | | Выход из приложения |

## Примеры использования

### Регистрация и вход

```
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1).
Войдите: login --username alice --password ****

> login --username alice --password 1234
Вы вошли как 'alice'
```

### Покупка и продажа валюты

```
[alice] > buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
  - BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2,966.86 USD

[alice] > sell --currency BTC --amount 0.01
Продажа выполнена: 0.0100 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
  - BTC: было 0.0500 → стало 0.0400
Оценочная выручка: 593.37 USD
```

### Просмотр портфеля

```
[alice] > show-portfolio
Портфель пользователя 'alice' (база: USD):
--------------------------------------------------
| Валюта | Баланс   | Стоимость (USD) |
+--------+----------+-----------------+
| BTC    | 0.0400   | 2,373.49        |
| USD    | 150.0000 | 150.00          |
--------------------------------------------------
ИТОГО: 2,523.49 USD
```

### Получение курсов

```
> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001685 (обновлено: 2025-10-09 10:29:42)
Обратный курс BTC→USD: 59337.21

> show-rates --top 3
Курсы из кэша (обновлено: 2025-10-09 10:35:00):
  - BTC_USD: 59337.21
  - ETH_USD: 3720.0
  - SOL_USD: 145.12
```

### Обновление курсов

```
> update-rates
INFO: Starting rates update...
INFO: Fetching from CoinGecko... OK (7 rates)
INFO: Fetching from ExchangeRate-API... OK (8 rates)
INFO: Writing 15 rates to data/rates.json...
Update successful. Total rates updated: 15. Last refresh: 2026-01-31T13:21:54
```

## Настройка Parser Service

### API ключ для ExchangeRate-API

1. Зарегистрируйтесь на https://www.exchangerate-api.com/
2. Получите API ключ
3. Установите переменную окружения:

```bash
export EXCHANGERATE_API_KEY=ваш_ключ_api
```

### CoinGecko

Публичный API CoinGecko работает без ключа. Для production-использования рекомендуется получить ключ на https://www.coingecko.com/en/api

## Настройки

Настройки можно изменить через переменные окружения:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `EXCHANGERATE_API_KEY` | Ключ API для ExchangeRate-API | |
| `VALUTATRADE_DATA_PATH` | Путь к файлам данных | `data` |
| `VALUTATRADE_LOG_PATH` | Путь к лог-файлам | `logs` |
| `VALUTATRADE_LOG_LEVEL` | Уровень логирования | `INFO` |
| `VALUTATRADE_RATES_TTL` | TTL кэша курсов (сек) | `300` |
| `VALUTATRADE_BASE_CURRENCY` | Базовая валюта | `USD` |

## Поддерживаемые валюты

### Фиатные
- USD (US Dollar)
- EUR (Euro)
- GBP (British Pound)
- RUB (Russian Ruble)
- JPY (Japanese Yen)
- CNY (Chinese Yuan)
- CHF (Swiss Franc)
- CAD (Canadian Dollar)
- AUD (Australian Dollar)

### Криптовалюты
- BTC (Bitcoin)
- ETH (Ethereum)
- SOL (Solana)
- XRP (Ripple)
- ADA (Cardano)
- DOGE (Dogecoin)
- LTC (Litecoin)

## Makefile команды

```bash
make install        # Установка зависимостей
make project        # Запуск приложения
make build          # Сборка пакета
make publish        # Публикация (dry-run)
make package-install # Установка собранного пакета
make lint           # Проверка кода (ruff)
```

## Логирование

Логи сохраняются в директории `logs/`:
- `actions.log` — операции пользователей (buy/sell/register/login)
- `parser.log` — операции парсера курсов

## Технологии

- **Python 3.10+**
- **Poetry** — управление зависимостями
- **Ruff** — линтинг и форматирование
- **PrettyTable** — форматированный вывод таблиц
- **Requests** — HTTP-запросы к API

## Демо

Полный цикл работы проекта register → login → buy/sell → show-portfolio → get-rate; отдельно — update-rates и show-rates хранится в demo.cast