#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# run.sh — Orquestador de Entorno y Tareas del Backend (FastAPI / Clean Arch)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"
UVICORN_BIN="${VENV_DIR}/bin/uvicorn"
PYTEST_BIN="${VENV_DIR}/bin/pytest"
RUFF_BIN="${VENV_DIR}/bin/ruff"
PORT="${PORT:-8000}"

port_in_use() {
    python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("0.0.0.0", port))
    sys.exit(0)
except OSError:
    sys.exit(1)
finally:
    s.close()
PY
}

resolve_port() {
    local port="${PORT:-8000}"
    while ! port_in_use "$port"; do
        echo "⚠️ Puerto $port está ocupado; probando $(($port + 1))..." >&2
        port=$((port + 1))
    done
    printf '%s' "$port"
}

ensure_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "📦 Creando entorno virtual en ${VENV_DIR}..."
        python3 -m venv "$VENV_DIR"
        "$PIP_BIN" install --upgrade pip
        if [[ -f "requirements-dev.txt" ]]; then
            echo "📥 Instalando dependencias desde requirements-dev.txt..."
            "$PIP_BIN" install -r requirements-dev.txt
        elif [[ -f "requirements.txt" ]]; then
            echo "📥 Instalando dependencias desde requirements.txt..."
            "$PIP_BIN" install -r requirements.txt
        fi
    fi
}

resolver_modo() {
    # Traduce el modo a la fuente que entiende la app (settings.MEDICIONES_SOURCE):
    # "dev" -> "local" (CSV en data/input), "prod" -> "ssh" (VPS). Retorna 1 si $1 no es un modo.
    case "$1" in
        dev)  export MEDICIONES_SOURCE="local" ;;
        prod) export MEDICIONES_SOURCE="ssh" ;;
        *)    return 1 ;;
    esac
    return 0
}

validar_ssh_prod() {
    # Preflight: valida conectividad SSH a VPS si está en modo prod
    if [[ "${MEDICIONES_SOURCE:-local}" == "ssh" ]]; then
        echo "🔐 Modo PROD: validando conectividad SSH a VPS..."
        if ! ssh -o BatchMode=yes -o ConnectTimeout=5 vps true 2>/dev/null; then
            echo "❌ No se puede conectar a VPS 'vps' via SSH."
            echo "   Asegúrate de:"
            echo "   1. Estar conectado a Tailscale"
            echo "   2. Tener ~/.ssh/config con entrada: Host vps ..."
            echo "   3. Clave pública instalada en VPS"
            exit 1
        fi
        echo "✅ Conectividad SSH validada"
    fi
}

mostrar_menu() {
    cat <<'TXT'
Uso: ./run.sh [COMANDO] [OPCIONES]
Detalle de un comando: ./run.sh ayuda <comando>

DATOS
  simulate       genera un tablero sintético con cargas conocidas
  disaggregate   desagrega un día con firmas confirmadas (batch diario)

APRENDIZAJE
  train          encuentra las cargas sin etiquetas (no supervisado)
  supervise      entrena un clasificador con la verdad de un medidor simulado

EVALUACIÓN
  evaluate       compara lo encontrado con la verdad conocida

SERVIDOR Y DESARROLLO
  dev, start     levantan el servidor FastAPI (start dev | start prod)
  test, gauntlet, audit, lint, format, install

Para empezar: ./run.sh simulate --dias 14
              y después: ./run.sh train sintetico
TXT
}

mostrar_ayuda_comando() {
    case "$1" in
        simulate)
            cat <<'TXT'
simulate · genera un tablero sintético con cargas conocidas
  Parte de:  nada (crea datos de prueba)
  Escribe:   data/input/sintetico.csv y su verdad en data/verdad/
  Ejemplo:   ./run.sh simulate --dias 14
TXT
            ;;
        train)
            cat <<'TXT'
train · identifica las cargas sin etiquetas (aprendizaje no supervisado)
  Parte de:  un CSV de mediciones por medidor en data/input/
  Hace:      detecta saltos de potencia → elige el umbral → agrupa por tamaño → resume
  Ejercicio: E6 (agrupamiento por densidad)
  Ejemplos:  ./run.sh train sintetico
             ./run.sh train sintetico --desde AAAA-MM-DD --hasta AAAA-MM-DD
TXT
            ;;
        supervise)
            cat <<'TXT'
supervise · entrena un clasificador con la verdad de un medidor simulado (supervisado)
  Parte de:  un medidor simulado con su verdad (./run.sh simulate)
  Hace:      aprende con un árbol de decisión y muestra las reglas
  Ejercicio: E3 (árboles de decisión)
  Ejemplo:   ./run.sh supervise
TXT
            ;;
        evaluate)
            cat <<'TXT'
evaluate · compara lo identificado con la verdad conocida
  Parte de:  el resultado de train y la verdad de un medidor simulado
  Hace:      calcula sensibilidad y precisión por carga
  Ejercicio: E5 (separación entre entrenamiento y verdad)
  Ejemplo:   ./run.sh evaluate
TXT
            ;;
        disaggregate)
            cat <<'TXT'
disaggregate · desagrega un día y calcula horas de marcha por máquina (batch diario)
  Parte de:  un CSV del día y un catálogo de firmas confirmadas
  Ejemplo:   ./run.sh disaggregate --help
TXT
            ;;
        "")
            mostrar_menu
            ;;
        *)
            imprimir_error_comando "No conozco el comando «$1»." \
                "ayuda pide el nombre exacto de un comando del menú." \
                "corré ./run.sh para ver la lista y después ./run.sh ayuda <comando>."
            return 1
            ;;
    esac
}

imprimir_error_comando() {
    echo "✘ ERROR  $1" >&2
    echo "  Por qué:  $2" >&2
    echo "  Cómo:     $3" >&2
}

COMMAND="${1:-menu}"

case "$COMMAND" in
    dev)
        ensure_venv
        PORT="$(resolve_port)"
        echo "🚀 Iniciando servidor FastAPI en modo desarrollo (reload) en puerto $PORT..."
        exec "$UVICORN_BIN" src.main:app --reload --host 0.0.0.0 --port "$PORT"
        ;;
    start)
        ensure_venv
        PORT="$(resolve_port)"
        if resolver_modo "${2:-dev}"; then
            :  # resolver_modo ya exportó MEDICIONES_SOURCE
        fi
        if [[ "${MEDICIONES_SOURCE:-local}" == "ssh" ]]; then
            echo "🚀 Iniciando servidor FastAPI en modo producción (datos desde VPS) en puerto $PORT..."
        else
            echo "🚀 Iniciando servidor FastAPI en modo desarrollo (datos locales) en puerto $PORT..."
        fi
        validar_ssh_prod  # Exit si SSH falla
        exec "$UVICORN_BIN" src.main:app --host 0.0.0.0 --port "$PORT"
        ;;
    train)
        ensure_venv
        ARGS=("${@:2}")
        if resolver_modo "${ARGS[0]:-}"; then
            ARGS=("${ARGS[@]:1}")  # Remover el primer argumento si era dev/prod
        fi
        echo "🧠 Identificando cargas (resultados en data/output/)..."
        exec "$PYTHON_BIN" -m src.infrastructure.cli.entrenar_cargas "${ARGS[@]}"
        ;;
    simulate)
        ensure_venv
        echo "🧪 Generando un tablero simulado con cargas conocidas..."
        exec "$PYTHON_BIN" -m src.infrastructure.cli.simular_tablero "${@:2}"
        ;;
    evaluate)
        ensure_venv
        ARGS=("${@:2}")
        if resolver_modo "${ARGS[0]:-}"; then
            ARGS=("${ARGS[@]:1}")
        fi
        echo "📏 Comparando lo identificado con la verdad conocida..."
        exec "$PYTHON_BIN" -m src.infrastructure.cli.evaluar_cargas "${ARGS[@]}"
        ;;
    supervise)
        ensure_venv
        ARGS=("${@:2}")
        if resolver_modo "${ARGS[0]:-}"; then
            ARGS=("${ARGS[@]:1}")
        fi
        echo "🎓 Entrenando un clasificador con la verdad de un medidor simulado..."
        exec "$PYTHON_BIN" -m src.infrastructure.cli.supervisar_cargas "${ARGS[@]}"
        ;;
    disaggregate)
        ensure_venv
        ARGS=("${@:2}")
        if resolver_modo "${ARGS[0]:-}"; then
            ARGS=("${ARGS[@]:1}")
        fi
        echo "⚙️ Desagregando cargas y atribuyendo horómetros (modo batch diario)..."
        exec "$PYTHON_BIN" -m src.infrastructure.cli.desagregar_cargas "${ARGS[@]}"
        ;;
    test)
        ensure_venv
        echo "🧪 Ejecutando suite de pruebas con pytest..."
        exec "$PYTEST_BIN" "${@:2}"
        ;;
    gauntlet)
        ensure_venv
        echo "🛡️  Ejecutando Guantelete de Restricciones Arquitectónicas..."
        exec "$PYTHON_BIN" tests/test_architecture.py
        ;;
    audit)
        ensure_venv
        echo "🧹 Ejecutando auditorías determinísticas (Clean Design & God Components)..."
        "$PYTHON_BIN" tests/test_clean_design.py
        "$PYTHON_BIN" tests/test_god_components.py
        ;;
    lint)
        ensure_venv
        echo "🔍 Verificando linter y formato con ruff..."
        "$RUFF_BIN" check .
        "$RUFF_BIN" format --check .
        ;;
    format)
        ensure_venv
        echo "✨ Aplicando formato automático con ruff..."
        "$RUFF_BIN" format .
        "$RUFF_BIN" check --fix .
        ;;
    install)
        ensure_venv
        echo "📥 Actualizando dependencias en ${VENV_DIR}..."
        if [[ -f "requirements-dev.txt" ]]; then
            "$PIP_BIN" install -r requirements-dev.txt
        elif [[ -f "requirements.txt" ]]; then
            "$PIP_BIN" install -r requirements.txt
        fi
        ;;
    menu|help|--help|-h)
        mostrar_menu
        ;;
    ayuda)
        mostrar_ayuda_comando "${2:-}" || exit 1
        ;;
    *)
        echo "❌ Comando desconocido: $COMMAND"
        echo "Ejecute ./run.sh help para ver los comandos disponibles."
        exit 1
        ;;
esac
