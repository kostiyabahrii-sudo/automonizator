#!/usr/bin/env bash
# Додає в crontab поточного користувача завдання, яке кожні 15 хв запускає
# scheduler.py. Сам scheduler.py публікує пін лише тоді, коли настав час
# (раз у 5-6 год з випадковим зсувом) — решту запусків він миттєво завершує,
# тож фонового навантаження на пам'ять по суті немає.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="$(command -v python3)"
CRON_LINE="*/15 * * * * cd ${REPO_DIR} && ${PYTHON_BIN} -m pinterest_autopost.scheduler >> ${REPO_DIR}/logs/cron.log 2>&1"

( crontab -l 2>/dev/null | grep -vF "pinterest_autopost.scheduler" ; echo "${CRON_LINE}" ) | crontab -

echo "Додано в crontab:"
echo "${CRON_LINE}"
echo
echo "Перевірити: crontab -l"
echo "Прибрати:   crontab -l | grep -v pinterest_autopost.scheduler | crontab -"
