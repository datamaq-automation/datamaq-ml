"""tests/unit/cargas/test_fusion_grupos.py — Fusión de grupos que son la misma máquina (datos sintéticos)."""

from datetime import datetime, timezone

from src.application.cargas.dtos.desagregar_cargas import IntervaloMarchaDTO
from src.application.cargas.use_cases.validar_desagregacion import (
    _solapamientos,
    candidatos_a_fusion,
)


def _it(h0: int, h1: int) -> IntervaloMarchaDTO:
    return IntervaloMarchaDTO(
        inicio_utc=datetime(2026, 9, 20, h0, tzinfo=timezone.utc),
        fin_utc=datetime(2026, 9, 20, h1, tzinfo=timezone.utc),
        horas=float(h1 - h0),
        energia_kwh_medida=0.0,
        potencia_media_kw=0.0,
        delta_reactiva_kvar=None,
        confianza=1.0,
    )


def test_dos_grupos_que_coinciden_casi_siempre_son_candidatos_a_fusion() -> None:
    """Grupo A y grupo B tienen cada uno tres intervalos, y cada intervalo de uno coincide con uno del otro."""
    clasificados = [
        ("A", _it(8, 9), "cerrado"),
        ("A", _it(10, 11), "cerrado"),
        ("A", _it(12, 13), "cerrado"),
        ("B", _it(8, 9), "cerrado"),
        ("B", _it(10, 11), "cerrado"),
        ("B", _it(12, 13), "cerrado"),
    ]
    candidatos = candidatos_a_fusion(clasificados)
    assert candidatos == {frozenset({"A", "B"})}
    assert _solapamientos(clasificados)[0] == 3
    assert _solapamientos(clasificados, candidatos)[0] == 0


def test_grupos_que_solo_se_tocan_a_veces_no_se_fusionan() -> None:
    """A tiene tres intervalos; B coincide con solo uno. Para A, 1/3 < 1/2: no es fusión."""
    clasificados = [
        ("A", _it(8, 9), "cerrado"),
        ("A", _it(10, 11), "cerrado"),
        ("A", _it(12, 13), "cerrado"),
        ("B", _it(8, 9), "cerrado"),
        ("B", _it(15, 16), "cerrado"),
    ]
    assert candidatos_a_fusion(clasificados) == set()


def test_grupos_disjuntos_no_son_candidatos() -> None:
    clasificados = [("A", _it(8, 9), "cerrado"), ("B", _it(10, 11), "cerrado")]
    assert candidatos_a_fusion(clasificados) == set()
