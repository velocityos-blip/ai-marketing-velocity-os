#!/bin/sh
set -eu
cd "$(dirname "$0")"
umask 077
if [ ! -f .env ]; then
  : "${VOS_API_HOST:?Set VOS_API_HOST to the DNS hostname pointing to this server}"
  case "$VOS_API_HOST" in *[!a-zA-Z0-9.-]*|'') exit 2;; esac
  temp=$(mktemp .env.XXXXXXXX)
  trap 'rm -f "$temp"' EXIT
  {
    printf 'VOS_API_HOST=%s\n' "$VOS_API_HOST"
    for key in MONGO_ROOT_PASSWORD VOS_DB_PASSWORD JWT_SECRET_KEY; do
      secret=$(openssl rand -hex 32)
      printf '%s=%s\n' "$key" "$secret"
    done
  } > "$temp"
  ln "$temp" .env
fi
docker compose up --build --detach --wait
