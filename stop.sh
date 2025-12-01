#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROD_COMPOSE="$PROJECT_ROOT/docker-compose.prod.yml"
DEV_COMPOSE="$PROJECT_ROOT/dev-tools/docker-compose.dev.yml"

info() {
  echo "[view-annotator-stop] $*"
}

fail() {
  echo "[view-annotator-stop][error] $*" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
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
  fail "No se encontró Docker Compose instalado."
}

stop_stack() {
  local compose_cmd="$1"
  local file="$2"
  [[ -f "$file" ]] || return
  $compose_cmd -f "$file" down --remove-orphans
}

select_mode() {
  if [[ -n "${1:-}" ]]; then
    echo "$1"
    return
  fi
  # Por defecto, detener producción
  echo "prod"
}

main() {
  local compose_cmd mode
  compose_cmd="$(resolve_compose)"
  mode="$(select_mode "${1:-}")"

  case "$mode" in
    prod|production)
      info "Deteniendo entorno de producción..."
      stop_stack "$compose_cmd" "$PROD_COMPOSE"
      ;;
    dev|development)
      info "Deteniendo entorno de desarrollo..."
      stop_stack "$compose_cmd" "$DEV_COMPOSE"
      ;;
    all|both)
      info "Deteniendo producción y desarrollo..."
      stop_stack "$compose_cmd" "$PROD_COMPOSE"
      stop_stack "$compose_cmd" "$DEV_COMPOSE"
      ;;
    "")
      # No hacer nada si el modo está vacío (ya se mostró error en select_mode)
      ;;
    *)
      fail "Opción inválida '$mode'. Usa: $0 [prod|dev|all] o ejecuta sin argumentos para modo interactivo"
      ;;
  esac

  info "Listo."
}

main "$@"
