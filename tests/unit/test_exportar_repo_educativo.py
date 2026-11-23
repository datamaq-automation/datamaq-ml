"""tests/unit/test_exportar_repo_educativo.py — Pruebas unitarias de exportación de repositorio educativo."""

from pathlib import Path

import pytest

from src.infrastructure.cli.exportar_repo_educativo import (
    CODIGO_OK,
    es_archivo_permitido,
    exportar_arbol,
    main,
    sanitizar_texto,
)


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


def test_sanitizar_texto() -> None:
    texto_sucio = "En la planta UPP medimos Trafo arriba y Trafo abajo."
    texto_limpio = sanitizar_texto(texto_sucio)
    assert "UPP" not in texto_limpio
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
    (origen / "README.md").write_text("Caso UPP con Trafo arriba.\n", encoding="utf-8")
    (origen / ".env").write_text("SECRET=12345\n", encoding="utf-8")

    copiados, advertencias = exportar_arbol(origen, destino)

    assert copiados == 3  # cargas.py, sintetico.csv, README.md
    assert not advertencias

    # Verificaciones en destino
    assert (destino / "src" / "domain" / "cargas.py").exists()
    assert (destino / "data" / "input" / "sintetico.csv").exists()
    assert (destino / "README.md").exists()

    # Sanitización aplicada
    readme_contenido = (destino / "README.md").read_text(encoding="utf-8")
    assert "UPP" not in readme_contenido
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
        exportar_arbol(origen, destino, sobreescribir=False)


def test_main_cli_ejecucion_ok(tmp_path: Path) -> None:
    origen = tmp_path / "origen"
    destino = tmp_path / "destino"
    origen.mkdir()
    (origen / "archivo.txt").write_text("Hola mundo educativo", encoding="utf-8")

    codigo = main(["--origen", str(origen), "--destino", str(destino)])
    assert codigo == CODIGO_OK
    assert (destino / "archivo.txt").read_text(encoding="utf-8") == "Hola mundo educativo"
