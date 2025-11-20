#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.prod.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

info() {
  echo "[visilab] $*"
}

fail() {
  echo "[visilab][error] $*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

ensure_docker() {
  info "Verificando Docker..."
  command_exists docker || fail "Docker no está instalado. Instálalo y vuelve a intentarlo."
  if ! docker info >/dev/null 2>&1; then
    fail "Docker está instalado pero no se puede conectar al daemon. Asegúrate de que Docker esté en ejecución."
  fi
}

resolve_compose() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return
  fi
  if command_exists docker-compose; then
    echo "docker-compose"
    return
  fi
  fail "No se encontró Docker Compose. Instálalo (v2 recomendado)."
}

generate_secret() {
  python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
}

ensure_env_file() {
  if [[ ! -f "$ENV_EXAMPLE" ]]; then
    fail "No se encontró .env.example."
  fi
  if [[ ! -f "$ENV_FILE" ]]; then
    info "Creando archivo .env a partir de .env.example..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
  fi
}

ensure_secret_key() {
  local current_line current_value new_secret
  if ! grep -q '^SECRET_KEY=' "$ENV_FILE"; then
    new_secret="$(generate_secret)"
    echo "SECRET_KEY=$new_secret" >> "$ENV_FILE"
    export SECRET_KEY="$new_secret"
    info "SECRET_KEY añadida al archivo .env."
    return
  fi

  current_line="$(grep '^SECRET_KEY=' "$ENV_FILE" | tail -n1)"
  current_value="${current_line#SECRET_KEY=}"

  if [[ -z "$current_value" || "$current_value" == "change-this-to-a-secure-random-key-in-production" ]]; then
    new_secret="$(generate_secret)"
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$new_secret|" "$ENV_FILE"
    export SECRET_KEY="$new_secret"
    info "SECRET_KEY insegura detectada. Se generó una nueva clave segura."
  else
    export SECRET_KEY="$current_value"
  fi
}

ensure_directories() {
  info "Verificando directorios necesarios..."
  mkdir -p "$PROJECT_ROOT/backend/datasets"
  mkdir -p "$PROJECT_ROOT/backend/ai_models"
  mkdir -p "$PROJECT_ROOT/mongodb/data"
  mkdir -p "$PROJECT_ROOT/mongodb/logs"
}

load_env() {
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
}

main() {
  info "Iniciando despliegue de VISILAB Annotator (producción)..."
  ensure_docker
  local compose_cmd
  compose_cmd="$(resolve_compose)"

  ensure_env_file
  ensure_secret_key
  ensure_directories
  load_env

  info "Levantando servicios... Esto puede tardar unos minutos."
  $compose_cmd -f "$COMPOSE_FILE" pull || true
  $compose_cmd -f "$COMPOSE_FILE" up -d --build

  info "Servicios en ejecución:"
  $compose_cmd -f "$COMPOSE_FILE" ps

  info "VISILAB Annotator está disponible en http://localhost:${FRONTEND_PORT:-5000}"
  info "(La API está accesible internamente a través de /api)"
  info "Para ver logs: $compose_cmd -f $COMPOSE_FILE logs -f"
}

main "$@"
