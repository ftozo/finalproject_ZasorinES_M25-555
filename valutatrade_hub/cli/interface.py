"""
Командный интерфейс (CLI) для ValutaTrade Hub.
"""

import shlex
from typing import Any

from prettytable import PrettyTable

from valutatrade_hub.core.currencies import (
    get_crypto_currencies,
    get_fiat_currencies,
)
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidPasswordError,
    NotLoggedInError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
    WalletNotFoundError,
)
from valutatrade_hub.core.usecases import ApplicationService
from valutatrade_hub.core.utils import format_datetime
from valutatrade_hub.parser_service.updater import RatesUpdater


class CLI:
    """
    Командный интерфейс приложения.

    Обрабатывает пользовательские команды и выводит результаты.
    """

    def __init__(self):
        self._app = ApplicationService()
        self._running = True

        # Регистрация команд
        self._commands = {
            "help": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "register": self._cmd_register,
            "login": self._cmd_login,
            "logout": self._cmd_logout,
            "whoami": self._cmd_whoami,
            "show-portfolio": self._cmd_show_portfolio,
            "portfolio": self._cmd_show_portfolio,
            "buy": self._cmd_buy,
            "sell": self._cmd_sell,
            "get-rate": self._cmd_get_rate,
            "rate": self._cmd_get_rate,
            "show-rates": self._cmd_show_rates,
            "rates": self._cmd_show_rates,
            "update-rates": self._cmd_update_rates,
            "currencies": self._cmd_currencies,
        }

    def run(self):
        """Запуск интерактивного CLI."""
        self._print_welcome()

        while self._running:
            try:
                # Формируем приглашение
                prompt = self._get_prompt()
                user_input = input(prompt).strip()

                if not user_input:
                    continue

                self._process_command(user_input)

            except KeyboardInterrupt:
                print("\n")
                self._cmd_exit({})
            except EOFError:
                print()
                self._cmd_exit({})

    def _get_prompt(self) -> str:
        """Формирование приглашения командной строки."""
        user = self._app.current_user
        if user:
            return f"[{user.username}] > "
        return "> "

    def _print_welcome(self):
        """Вывод приветственного сообщения."""
        print("=" * 50)
        print("  ValutaTrade Hub - Симулятор торговли валютами")
        print("=" * 50)
        print("Введите 'help' для списка команд")
        print()

    def _process_command(self, user_input: str):
        """Обработка пользовательской команды."""
        try:
            # Парсинг команды и аргументов
            tokens = shlex.split(user_input)
        except ValueError as e:
            print(f"Ошибка разбора команды: {e}")
            return

        if not tokens:
            return

        command = tokens[0].lower()
        args = self._parse_args(tokens[1:])

        if command not in self._commands:
            print(f"Неизвестная команда: '{command}'. Введите 'help' для справки.")
            return

        try:
            self._commands[command](args)
        except NotLoggedInError:
            print("Сначала выполните login")
        except UserNotFoundError as e:
            print(str(e))
        except UserAlreadyExistsError as e:
            print(str(e))
        except InvalidPasswordError:
            print("Неверный пароль")
        except ValidationError as e:
            print(str(e))
        except CurrencyNotFoundError as e:
            print(str(e))
            print("Используйте 'currencies' для списка поддерживаемых валют")
        except InsufficientFundsError as e:
            print(str(e))
        except WalletNotFoundError as e:
            print(str(e))
        except ApiRequestError as e:
            print(str(e))
            print("Попробуйте выполнить 'update-rates' для обновления курсов")
        except Exception as e:
            print(f"Ошибка: {e}")

    def _parse_args(self, tokens: list[str]) -> dict[str, Any]:
        """
        Парсинг аргументов команды.

        Поддерживает формат: --key value или --key=value
        """
        args = {}
        i = 0

        while i < len(tokens):
            token = tokens[i]

            if token.startswith("--"):
                if "=" in token:
                    # Формат --key=value
                    key, value = token[2:].split("=", 1)
                    args[key] = value
                elif i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                    # Формат --key value
                    key = token[2:]
                    args[key] = tokens[i + 1]
                    i += 1
                else:
                    # Флаг без значения
                    args[token[2:]] = True
            else:
                # Позиционный аргумент
                if "positional" not in args:
                    args["positional"] = []
                args["positional"].append(token)

            i += 1

        return args

    # ==================== Команды ====================

    def _cmd_help(self, args: dict):
        """Вывод справки."""
        print("\nДоступные команды:")
        print("-" * 50)

        commands = [
            ("register", "--username <имя> --password <пароль>", "Регистрация"),
            ("login", "--username <имя> --password <пароль>", "Вход в систему"),
            ("logout", "", "Выход из системы"),
            ("whoami", "", "Текущий пользователь"),
            ("show-portfolio", "[--base <валюта>]", "Показать портфель"),
            ("buy", "--currency <код> --amount <кол-во>", "Купить валюту"),
            ("sell", "--currency <код> --amount <кол-во>", "Продать валюту"),
            ("get-rate", "--from <код> --to <код>", "Получить курс"),
            ("show-rates", "[--currency <код>] [--top <N>]", "Показать курсы"),
            ("update-rates", "[--source <источник>]", "Обновить курсы"),
            ("currencies", "", "Список валют"),
            ("help", "", "Эта справка"),
            ("exit", "", "Выход"),
        ]

        for cmd, args_desc, desc in commands:
            if args_desc:
                print(f"  {cmd} {args_desc}")
            else:
                print(f"  {cmd}")
            print(f"      {desc}")

        print()

    def _cmd_exit(self, args: dict):
        """Выход из приложения."""
        print("До свидания!")
        self._running = False

    def _cmd_register(self, args: dict):
        """Регистрация нового пользователя."""
        username = args.get("username")
        password = args.get("password")

        if not username:
            print("Укажите имя пользователя: --username <имя>")
            return
        if not password:
            print("Укажите пароль: --password <пароль>")
            return

        user = self._app.users.register(username, password)
        print(f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}).")
        print(f"Войдите: login --username {user.username} --password ****")

    def _cmd_login(self, args: dict):
        """Вход в систему."""
        username = args.get("username")
        password = args.get("password")

        if not username:
            print("Укажите имя пользователя: --username <имя>")
            return
        if not password:
            print("Укажите пароль: --password <пароль>")
            return

        user = self._app.users.login(username, password)
        print(f"Вы вошли как '{user.username}'")

    def _cmd_logout(self, args: dict):
        """Выход из системы."""
        if not self._app.is_logged_in():
            print("Вы не авторизованы")
            return

        username = self._app.current_user.username
        self._app.users.logout()
        print(f"Вы вышли из аккаунта '{username}'")

    def _cmd_whoami(self, args: dict):
        """Показать текущего пользователя."""
        user = self._app.current_user
        if user:
            print(f"Вы вошли как: {user.username} (id={user.user_id})")
            print(f"Дата регистрации: {format_datetime(user.registration_date)}")
        else:
            print("Вы не авторизованы")

    def _cmd_show_portfolio(self, args: dict):
        """Показать портфель пользователя."""
        base = args.get("base", "USD").upper()

        summary = self._app.portfolios.get_portfolio_summary(base)

        print(f"\nПортфель пользователя '{summary['username']}' (база: {base}):")
        print("-" * 50)

        if not summary["wallets"]:
            print("Портфель пуст")
        else:
            table = PrettyTable()
            table.field_names = ["Валюта", "Баланс", f"Стоимость ({base})"]
            table.align["Баланс"] = "r"
            table.align[f"Стоимость ({base})"] = "r"

            for wallet in summary["wallets"]:
                table.add_row(
                    [
                        wallet["currency_code"],
                        f"{wallet['balance']:.4f}",
                        f"{wallet['value_in_base']:.2f}",
                    ]
                )

            print(table)

        print("-" * 50)
        print(f"ИТОГО: {summary['total_value']:,.2f} {base}")
        print()

    def _cmd_buy(self, args: dict):
        """Покупка валюты."""
        currency = args.get("currency")
        amount = args.get("amount")

        if not currency:
            print("Укажите валюту: --currency <код>")
            return
        if not amount:
            print("Укажите количество: --amount <число>")
            return

        try:
            amount = float(amount)
        except ValueError:
            print("'amount' должен быть числом")
            return

        result = self._app.portfolios.buy(currency, amount)

        print(f"\nПокупка выполнена: {result['amount']:.4f} {result['currency_code']}", end="")
        if result.get("rate"):
            print(
                f" по курсу {result['rate']:.2f} {result['base_currency']}/{result['currency_code']}"
            )
        else:
            print()

        print("Изменения в портфеле:")
        print(
            f"  - {result['currency_code']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}"
        )

        if result.get("estimated_cost"):
            print(
                f"Оценочная стоимость покупки: {result['estimated_cost']:,.2f} {result['base_currency']}"
            )
        print()

    def _cmd_sell(self, args: dict):
        """Продажа валюты."""
        currency = args.get("currency")
        amount = args.get("amount")

        if not currency:
            print("Укажите валюту: --currency <код>")
            return
        if not amount:
            print("Укажите количество: --amount <число>")
            return

        try:
            amount = float(amount)
        except ValueError:
            print("'amount' должен быть числом")
            return

        result = self._app.portfolios.sell(currency, amount)

        print(f"\nПродажа выполнена: {result['amount']:.4f} {result['currency_code']}", end="")
        if result.get("rate"):
            print(
                f" по курсу {result['rate']:.2f} {result['base_currency']}/{result['currency_code']}"
            )
        else:
            print()

        print("Изменения в портфеле:")
        print(
            f"  - {result['currency_code']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}"
        )

        if result.get("estimated_revenue"):
            print(
                f"Оценочная выручка: {result['estimated_revenue']:,.2f} {result['base_currency']}"
            )
        print()

    def _cmd_get_rate(self, args: dict):
        """Получение курса валюты."""
        from_code = args.get("from")
        to_code = args.get("to")

        if not from_code:
            print("Укажите исходную валюту: --from <код>")
            return
        if not to_code:
            print("Укажите целевую валюту: --to <код>")
            return

        result = self._app.rates.get_rate(from_code, to_code)

        updated = result.get("updated_at", "N/A")
        if updated and updated != "N/A":
            updated = (
                format_datetime(updated)
                if not isinstance(updated, str)
                else updated[:19].replace("T", " ")
            )

        print(f"\nКурс {result['from_code']}→{result['to_code']}: {result['rate']:.8f}", end="")
        print(f" (обновлено: {updated})")

        if result.get("reverse_rate"):
            print(
                f"Обратный курс {result['to_code']}→{result['from_code']}: {result['reverse_rate']:.2f}"
            )

        if not result.get("fresh", True):
            print("⚠ Данные могут быть устаревшими. Выполните 'update-rates' для обновления.")
        print()

    def _cmd_show_rates(self, args: dict):
        """Показать все курсы."""
        currency = args.get("currency")
        top = args.get("top")

        rates_data = self._app.rates.get_all_rates()
        pairs = rates_data.get("pairs", rates_data)
        last_refresh = rates_data.get("last_refresh", "N/A")

        if isinstance(last_refresh, str) and last_refresh != "N/A":
            last_refresh = last_refresh[:19].replace("T", " ")

        print(f"\nКурсы из кэша (обновлено: {last_refresh}):")
        print("-" * 40)

        # Фильтрация
        filtered_pairs = []
        for pair, data in pairs.items():
            rate = data.get("rate") if isinstance(data, dict) else data

            if currency:
                if currency.upper() not in pair:
                    continue

            filtered_pairs.append((pair, rate))

        if not filtered_pairs:
            if currency:
                print(f"Курс для '{currency.upper()}' не найден в кэше.")
            else:
                print(
                    "Локальный кэш курсов пуст. Выполните 'update-rates', чтобы загрузить данные."
                )
            return

        # Сортировка
        if top:
            try:
                top = int(top)
                filtered_pairs.sort(key=lambda x: x[1] or 0, reverse=True)
                filtered_pairs = filtered_pairs[:top]
            except ValueError:
                pass

        # Вывод
        for pair, rate in filtered_pairs:
            print(f"  - {pair}: {rate}")

        print()

    def _cmd_update_rates(self, args: dict):
        """Обновление курсов валют."""
        source = args.get("source")

        print("INFO: Starting rates update...")

        sources = None
        if source:
            sources = [source]

        updater = RatesUpdater()
        result = updater.run_update(sources)

        # Вывод результатов
        for source_name, source_result in result.get("sources", {}).items():
            status = source_result.get("status")
            if status == "OK":
                count = source_result.get("rates_count", 0)
                print(f"INFO: Fetching from {source_name}... OK ({count} rates)")
            else:
                error = source_result.get("error", "Unknown error")
                print(f"ERROR: Failed to fetch from {source_name}: {error}")

        total = result.get("total_rates", 0)
        if total > 0:
            print(f"INFO: Writing {total} rates to data/rates.json...")

        if result.get("success"):
            print(
                f"Update successful. Total rates updated: {total}. "
                f"Last refresh: {result.get('completed_at', 'N/A')[:19]}"
            )
        elif result.get("success") == "partial":
            print("Update completed with errors. Check logs/parser.log for details.")
        else:
            print("Update failed. Check logs/parser.log for details.")

    def _cmd_currencies(self, args: dict):
        """Показать список поддерживаемых валют."""
        print("\nПоддерживаемые валюты:")
        print("-" * 50)

        print("\nФиатные валюты:")
        fiat = get_fiat_currencies()
        for currency in fiat:
            print(f"  {currency.get_display_info()}")

        print("\nКриптовалюты:")
        crypto = get_crypto_currencies()
        for currency in crypto:
            print(f"  {currency.get_display_info()}")

        print()


def main():
    """Точка входа CLI."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
