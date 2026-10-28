#!/usr/bin/env bash
# End-to-end check of the Docker stack: SPA, API, admin assets, Postgres
# migrations, Redis, avatar upload/replace/remove through nginx, and (unless
# SKIP_AI=1) one AI chat round trip.
set -euo pipefail

cd "$(dirname "$0")/.."
compose=(docker compose)
base="${BASE_URL:-http://localhost:8080}"
email="smoke-$(date +%s)@example.com"
password="not-a-common-password-123"
tmp="$(mktemp -d)"
token=""

cleanup() {
    if [ -n "$token" ]; then
        curl -sS -X PATCH "$base/api/auth/me/" \
            -H "Authorization: Bearer $token" \
            -F "remove_profile_picture=true" >/dev/null 2>&1 || true
    fi
    "${compose[@]}" exec -T backend python manage.py shell -c \
        "from api.models import Profile; Profile.objects.filter(email='$email').delete()" \
        >/dev/null 2>&1 || true
    rm -rf "$tmp"
}
trap cleanup EXIT

json_field() {
    python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"
}

expect() {
    local label="$1" want="$2" got="$3"
    if [ "$want" != "$got" ]; then
        echo "FAIL $label: expected $want, got $got" >&2
        exit 1
    fi
    echo "ok   $label"
}

echo "== containers =="
"${compose[@]}" up -d --wait

echo "== web =="
expect "SPA" "200" "$(curl -sS -o /dev/null -w '%{http_code}' "$base/")"
expect "SPA fallback" "200" "$(curl -sS -o /dev/null -w '%{http_code}' "$base/trips")"
expect "API" "200" "$(curl -sS -o /dev/null -w '%{http_code}' "$base/api/home/")"
expect "admin redirect" "302" "$(curl -sS -o /dev/null -w '%{http_code}' "$base/admin/")"
expect "admin static" "200" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$base/static/admin/css/base.css")"

echo "== data =="
expect "redis" "PONG" "$("${compose[@]}" exec -T redis redis-cli ping | tr -d '\r')"
"${compose[@]}" exec -T backend python manage.py showmigrations api \
    | grep -q '\[X\] 0004_delete_placeinfo'
echo "ok   migrations"

echo "== auth + avatar =="
register=$(curl -sS -X POST "$base/api/auth/register/" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}")
token=$(printf '%s' "$register" | json_field access)
[ -n "$token" ]
echo "ok   register"

printf 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=' \
    | base64 -d >"$tmp/avatar.png"

first=$(curl -sS -X PATCH "$base/api/auth/me/" \
    -H "Authorization: Bearer $token" \
    -F "profile_picture=@$tmp/avatar.png;type=image/png")
first_url=$(printf '%s' "$first" | json_field profile_picture)
expect "avatar upload" "200" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$base$first_url")"

second=$(curl -sS -X PATCH "$base/api/auth/me/" \
    -H "Authorization: Bearer $token" \
    -F "profile_picture=@$tmp/avatar.png;type=image/png;filename=replacement.png")
second_url=$(printf '%s' "$second" | json_field profile_picture)
expect "avatar replace" "200" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$base$second_url")"
expect "old avatar deleted" "404" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$base$first_url")"

removed=$(curl -sS -X PATCH "$base/api/auth/me/" \
    -H "Authorization: Bearer $token" -F "remove_profile_picture=true")
expect "avatar remove" "None" "$(printf '%s' "$removed" | json_field profile_picture)"
expect "removed avatar deleted" "404" \
    "$(curl -sS -o /dev/null -w '%{http_code}' "$base$second_url")"

if [ "${SKIP_AI:-0}" != "1" ]; then
    echo "== AI =="
    reply=$(curl -sS -X POST "$base/api/chat/" \
        -H "Authorization: Bearer $token" \
        -H 'Content-Type: application/json' \
        -d '{"message":"Reply with exactly: smoke ok","destination":""}')
    printf '%s' "$reply" | grep -qi 'smoke ok'
    echo "ok   AI chat"
fi

echo "smoke ok"
