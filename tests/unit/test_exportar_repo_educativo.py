"""tests/unit/test_exportar_repo_educativo.py — Pruebas unitarias de exportación de repositorio educativo."""

import json
from pathlib import Path

import pytest

from src.infrastructure.cli.exportar_repo_educativo import (
    CODIGO_ERROR_PARAMETROS,
    CODIGO_OK,
    CODIGO_VIOLACION_PRIVACIDAD,
    cargar_reemplazos,
    es_archivo_permitido,
    escanear_patrones_prohibidos,
    exportar_arbol,
    main,
    sanitizar_texto,
)

# Nombres ficticios: los reales viven en config/clientes_privados.json, que no se versiona.
REEMPLAZOS = {
    "Acme Industrial": "Planta Piloto",
    "Trafo Norte": "Trafo 1",
    "Trafo Sur": "Trafo 2",
}


def _escribir_clientes(ruta: Path, reemplazos: dict[str, str] = REEMPLAZOS) -> Path:
    ruta.write_text(json.dumps({"reemplazos": reemplazos}), encoding="utf-8")
    return ruta


def test_filtro_rutas_excluidas() -> None:
    # Deben ser excluidos
    assert not es_archivo_permitido(Path(".git/config"))
    assert not es_archivo_permitido(Path(".venv/bin/python"))
    assert not es_archivo_permitido(Path("src/infrastructure/ssh/medicion_repository.py"))
    assert not es_archivo_permitido(Path("data/input/planta_2_a.csv"))
    assert not es_archivo_permitido(Path("data/verdad/verdad.csv"))
    assert not es_archivo_permitido(Path(".env"))
    assert not es_archivo_permitido(Path("ejecucion.log"))
    assert not es_archivo_permitido(Path("__pycache__/foo.pyc"))

    # Deben ser permitidos
    assert es_archivo_permitido(Path("src/domain/cargas/entities.py"))
    assert es_archivo_permitido(Path("data/input/sintetico.csv"))
    assert es_archivo_permitido(Path("docs/cuaderno-alumno.md"))
    assert es_archivo_permitido(Path("pyproject.toml"))
    assert es_archivo_permitido(Path("run.sh"))
    assert es_archivo_permitido(Path("config/clientes_privados.example.json"))
    assert not es_archivo_permitido(Path("config/clientes_privados.json"))


def test_sanitizar_texto() -> None:
    texto_sucio = "En la planta Acme Industrial medimos Trafo Norte y Trafo Sur."
    texto_limpio = sanitizar_texto(texto_sucio, REEMPLAZOS)
    assert "Acme" not in texto_limpio
    assert "Planta Piloto" in texto_limpio
    assert "Trafo 1" in texto_limpio
    assert "Trafo 2" in texto_limpio


def test_exportar_arbol_sintetico(tmp_path: Path) -> None:
    origen = tmp_path / "repo_origen"
    destino = tmp_path / "repo_destino"

    # Estructura de prueba
    (origen / "src" / "domain").mkdir(parents=True)
    (origen / "src" / "infrastructure" / "ssh").mkdir(parents=True)
    (origen / "data" / "input").mkdir(parents=True)
    (origen / ".git").mkdir()

    # Archivos
    (origen / "src" / "domain" / "cargas.py").write_text(
        "class Carga:\n    pass\n", encoding="utf-8"
    )
    (origen / "src" / "infrastructure" / "ssh" / "repo.py").write_text(
        "class SshRepo:\n    pass\n", encoding="utf-8"
    )
    (origen / "data" / "input" / "sintetico.csv").write_text(
        "instante,potencia_kw\n", encoding="utf-8"
    )
    (origen / "data" / "input" / "planta_real.csv").write_text(
        "instante,potencia_kw\n", encoding="utf-8"
    )
    (origen / "README.md").write_text("Caso Acme Industrial con Trafo Norte.\n", encoding="utf-8")
    (origen / ".env").write_text("SECRET=12345\n", encoding="utf-8")

    copiados, advertencias = exportar_arbol(origen, destino, REEMPLAZOS)

    assert copiados == 3  # cargas.py, sintetico.csv, README.md
    assert not advertencias

    # Verificaciones en destino
    assert (destino / "src" / "domain" / "cargas.py").exists()
    assert (destino / "data" / "input" / "sintetico.csv").exists()
    assert (destino / "README.md").exists()

    # Sanitización aplicada
    readme_contenido = (destino / "README.md").read_text(encoding="utf-8")
    assert "Acme" not in readme_contenido
    assert "Planta Piloto" in readme_contenido
    assert "Trafo 1" in readme_contenido

    # Exclusiones respetadas
    assert not (destino / ".git").exists()
    assert not (destino / ".env").exists()
    assert not (destino / "src" / "infrastructure" / "ssh").exists()
    assert not (destino / "data" / "input" / "planta_real.csv").exists()


def test_exportar_falla_si_destino_existe_sin_sobreescribir(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    destino.mkdir()

    with pytest.raises(FileExistsError):
        exportar_arbol(origen, destino, REEMPLAZOS, sobreescribir=False)


def test_main_cli_ejecucion_ok(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    (origen / "archivo.txt").write_text("Hola mundo educativo", encoding="utf-8")

    clientes = _escribir_clientes(tmp_path / "clientes.json")

    codigo = main(["--origen", str(origen), "--destino", str(destino), "--clientes", str(clientes)])
    assert codigo == CODIGO_OK
    assert (destino / "archivo.txt").read_text(encoding="utf-8") == "Hola mundo educativo"


def test_main_cli_falla_sin_archivo_de_clientes(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    origen.mkdir()

    codigo = main(["--origen", str(origen), "--destino", str(tmp_path / "destino")])
    assert codigo == CODIGO_ERROR_PARAMETROS
    assert not (tmp_path / "destino").exists()


def test_main_cli_usa_archivo_de_clientes_por_defecto(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    (origen / "config").mkdir(parents=True)
    _escribir_clientes(origen / "config" / "clientes_privados.json")
    (origen / "nota.md").write_text("Medición en Acme Industrial.", encoding="utf-8")

    destino = tmp_path / "destino"
    assert main(["--origen", str(origen), "--destino", str(destino)]) == CODIGO_OK
    assert (destino / "nota.md").read_text(encoding="utf-8") == "Medición en Planta Piloto."
    assert not (destino / "config" / "clientes_privados.json").exists()


def test_main_cli_rechaza_archivo_de_clientes_invalido(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    origen.mkdir()
    clientes = tmp_path / "clientes.json"
    clientes.write_text(json.dumps({"reemplazos": ["sin", "mapa"]}), encoding="utf-8")

    codigo = main(
        ["--origen", str(origen), "--destino", str(tmp_path / "d"), "--clientes", str(clientes)]
    )
    assert codigo == CODIGO_ERROR_PARAMETROS


def test_escaneo_detecta_nombres_configurados_e_ip() -> None:
    hallazgos = escanear_patrones_prohibidos("acme industrial en 100.64.1.2", REEMPLAZOS)
    assert "acme industrial" in hallazgos
    assert "100.64.1.2" in hallazgos


def test_main_cli_reporta_ip_que_no_se_puede_tapar(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    origen.mkdir()
    (origen / "hosts.txt").write_text("vps 100.64.1.2", encoding="utf-8")
    clientes = _escribir_clientes(tmp_path / "clientes.json")

    codigo = main(
        ["--origen", str(origen), "--destino", str(tmp_path / "d"), "--clientes", str(clientes)]
    )
    assert codigo == CODIGO_VIOLACION_PRIVACIDAD


def test_ejemplo_versionado_es_valido_y_ficticio() -> None:
    ejemplo = Path(__file__).resolve().parents[2] / "config" / "clientes_privados.example.json"
    reemplazos = cargar_reemplazos(ejemplo)
    assert reemplazos
    assert set(reemplazos.values()) >= {"Planta Piloto"}
