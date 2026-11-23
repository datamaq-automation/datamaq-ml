"""tests/unit/test_foil_learner.py — Pruebas unitarias de FOIL y programación lógica inductiva (Issue #14).

Verifica el cálculo de ganancia de información FOIL (Quinlan 1990), la evaluación de cláusulas
de Horn relacionales sobre hechos de fondo, la cobertura disyuntiva y el cierre de pares positivos.
"""

from __future__ import annotations

import pytest

from src.domain.cargas.foil_learner import (
    BaseConocimientoRelacional,
    ClausulaHorn,
    FOILLearner,
    calcular_ganancia_foil,
)


@pytest.fixture
def base_cuatro_equipos() -> BaseConocimientoRelacional:
    """Fixture con los hechos de fondo del Issue #14: A->B, C->A, D->C."""
    bc = BaseConocimientoRelacional(entidades=["A", "B", "C", "D"])
    bc.agregar_hecho("despues", "A", "B")
    bc.agregar_hecho("despues", "C", "A")
    bc.agregar_hecho("despues", "D", "C")
    return bc


def test_calcular_ganancia_foil_valores_teoricos(
    base_cuatro_equipos: BaseConocimientoRelacional,
) -> None:
    """Verifica las ganancias 3.00 y 3.17 descriptas analíticamente en el Issue #14."""
    pos = {("A", "B"), ("C", "A"), ("C", "B"), ("D", "C"), ("D", "A"), ("D", "B")}
    neg = {
        (x, y)
        for x in base_cuatro_equipos.entidades
        for y in base_cuatro_equipos.entidades
        if x != y
    } - pos

    # Cláusula 1: dependiente(X, Y) :- despues(X, Y)
    cl1 = ClausulaHorn(
        cabeza="dependiente",
        cuerpo_literales=[("despues", "X", "Y")],
    )
    g1, cubiertos_pos1 = calcular_ganancia_foil(cl1, pos, neg, base_cuatro_equipos)
    assert pytest.approx(g1, rel=1e-2) == 3.00
    assert len(cubiertos_pos1) == 3

    # Tras cl1, quedan 3 positivos: (C, B), (D, A), (D, B)
    pos_restantes = pos - cubiertos_pos1
    assert pos_restantes == {("C", "B"), ("D", "A"), ("D", "B")}

    # Cláusula 2: dependiente(X, Y) :- despues(X, Z), despues(Z, Y)
    cl2 = ClausulaHorn(
        cabeza="dependiente",
        cuerpo_literales=[("despues", "X", "Z"), ("despues", "Z", "Y")],
    )
    g2, cubiertos_pos2 = calcular_ganancia_foil(cl2, pos_restantes, neg, base_cuatro_equipos)
    assert pytest.approx(g2, rel=1e-2) == 3.17
    assert cubiertos_pos2 == {("C", "B"), ("D", "A")}

    # Cláusula 3: dependiente(X, Y) :- despues(X, Z), despues(Z, W), despues(W, Y)
    pos_final = pos_restantes - cubiertos_pos2
    assert pos_final == {("D", "B")}
    cl3 = ClausulaHorn(
        cabeza="dependiente",
        cuerpo_literales=[
            ("despues", "X", "Z"),
            ("despues", "Z", "W"),
            ("despues", "W", "Y"),
        ],
    )
    g3, cubiertos_pos3 = calcular_ganancia_foil(cl3, pos_final, neg, base_cuatro_equipos)
    assert pytest.approx(g3, rel=1e-2) == 2.81
    assert cubiertos_pos3 == {("D", "B")}


def test_foil_learner_induccion_completa_cero_negativos(
    base_cuatro_equipos: BaseConocimientoRelacional,
) -> None:
    """Verifica que el learner FOIL induzca un programa lógico que cubra los 6 positivos y 0 negativos."""
    pos = {("A", "B"), ("C", "A"), ("C", "B"), ("D", "C"), ("D", "A"), ("D", "B")}
    neg = {
        (x, y)
        for x in base_cuatro_equipos.entidades
        for y in base_cuatro_equipos.entidades
        if x != y
    } - pos

    learner = FOILLearner(base_cuatro_equipos)
    clausulas = learner.entrenar_relacion(
        objetivo="dependiente",
        positivos=pos,
        negativos=neg,
    )

    assert len(clausulas) == 3
    # Debe cubrir todos los positivos
    for par in pos:
        assert learner.probar("dependiente", par[0], par[1]) is True

    # No debe cubrir ningún negativo
    for par in neg:
        assert learner.probar("dependiente", par[0], par[1]) is False


def test_foil_ganancia_sin_positivos_devuelve_cero(
    base_cuatro_equipos: BaseConocimientoRelacional,
) -> None:
    """Si una hipótesis no cubre ningún positivo restante, la ganancia es exactamente 0.0."""
    cl_inutil = ClausulaHorn(
        cabeza="dependiente",
        cuerpo_literales=[("despues", "X", "X")],  # Falso, ningún equipo va después de sí mismo
    )
    g, cubiertos = calcular_ganancia_foil(
        cl_inutil, {("A", "B")}, {("B", "A")}, base_cuatro_equipos
    )
    assert g == 0.0
    assert cubiertos == set()
