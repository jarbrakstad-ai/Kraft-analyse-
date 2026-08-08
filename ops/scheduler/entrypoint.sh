#!/bin/bash
set -euo pipefail

# Cron jobs start with a bare environment, so dump the container's env
# (DATABASE_URL, ENTSOE_API_KEY, MET_FROST_CLIENT_ID, ...) to a file each
# crontab line sources before running. Skip the handful of vars that are
# noisy or wrong outside this exact shell invocation.
printenv | grep -vE '^(HOME|PWD|OLDPWD|SHLVL|_)=' > /app/cron.env

touch /var/log/cron.log
echo "Kraft-analyse scheduler starting. Installed crontab:"
cat /etc/cron.d/kraft-analyse
echo "---"

tail -F /var/log/cron.log &
exec cron -f
