"""src/application/cargas/use_cases/evaluar_contra_verdad.py — Compara la salida inferida con la verdad de terreno.

Entrada: la salida del batch (nilm.intervalos.v1) y la verdad (nilm.verdad.v1). Las máquinas se emparejan por
nombre: el nombre del catálogo de firmas tiene que coincidir con el de la verdad.
"""

from collections import Counter
from dataclasses import dataclass, field

from src.application.cargas.dtos.desagregar_cargas import AtribuirCargasBatchResponseDTO, CargaDTO
from src.application.cargas.dtos.verdad_intervalos import CargaVerdadDTO, VerdadIntervalosDTO
from src.domain.cargas.evaluacion_verdad import (
    TOLERANCIA_EVENTO_S,
    ResultadoMaquina,
    Tramo,
    evaluar,
)


def _tramos_inferidos(cargas: list[CargaDTO]) -> dict[str, list[Tramo]]:
    return {
        carga.nombre: [Tramo(i.inicio_utc, i.fin_utc) for i in carga.intervalos] for carga in cargas
    }


def _tramos_verdaderos(cargas: list[CargaVerdadDTO]) -> dict[str, list[Tramo]]:
    return {
        carga.nombre: [Tramo(i.inicio_utc, i.fin_utc) for i in carga.intervalos] for carga in cargas
    }


def _energias_inferidas(cargas: list[CargaDTO]) -> dict[str, float]:
    return {c.nombre: sum(i.energia_kwh_medida for i in c.intervalos) for c in cargas}


def _energias_verdaderas(cargas: list[CargaVerdadDTO]) -> dict[str, float | None]:
    """Energía de la verdad por máquina: solo si todos sus intervalos la traen (el simulador sí)."""
    return {
        c.nombre: _suma_si_completa([i.energia_kwh_medida for i in c.intervalos]) for c in cargas
    }


def _suma_si_completa(valores: list[float | None]) -> float | None:
    if any(v is None for v in valores):
        return None
    return sum(v for v in valores if v is not None)


def evaluar_contra_verdad(
    inferido: AtribuirCargasBatchResponseDTO,
    verdad: VerdadIntervalosDTO,
    tolerancia_s: float = TOLERANCIA_EVENTO_S,
) -> list[ResultadoMaquina]:
    return evaluar(
        _tramos_inferidos(inferido.cargas),
        _tramos_verdaderos(verdad.cargas),
        tolerancia_s=tolerancia_s,
        energias_inferidas=_energias_inferidas(inferido.cargas),
        energias_verdaderas=_energias_verdaderas(verdad.cargas),
    )


@dataclass(frozen=True)
class EvaluacionDia:
    """Decisión sobre un día según su calidad, con sus resultados si se evaluó.

    - OK: se evalúa y cuenta en el resumen.
    - DUDOSA: se evalúa y queda marcada; fuera del resumen salvo `incluir_dudosos`.
    - NO_UTILIZABLE: se rechaza (no se evalúa) salvo `incluir_no_utilizables`.
    """

    estado: str
    motivos: tuple[str, ...]
    evaluado: bool
    en_resumen: bool
    resultados: list[ResultadoMaquina] = field(default_factory=list)


def evaluar_dia(
    inferido: AtribuirCargasBatchResponseDTO,
    verdad: VerdadIntervalosDTO,
    tolerancia_s: float = TOLERANCIA_EVENTO_S,
    incluir_dudosos: bool = False,
    incluir_no_utilizables: bool = False,
) -> EvaluacionDia:
    calidad = verdad.medidor.calidad_efectiva
    motivos = tuple(calidad.motivos)
    if calidad.estado == "NO_UTILIZABLE" and not incluir_no_utilizables:
        return EvaluacionDia(calidad.estado, motivos, evaluado=False, en_resumen=False)
    resultados = evaluar_contra_verdad(inferido, verdad, tolerancia_s)
    if calidad.estado == "OK":
        en_resumen = True
    elif calidad.estado == "DUDOSA":
        en_resumen = incluir_dudosos
    else:
        en_resumen = True  # NO_UTILIZABLE evaluado a pedido: el pedido lo incluye.
    return EvaluacionDia(calidad.estado, motivos, True, en_resumen, resultados)


def resumen_exclusiones(evaluaciones: list[EvaluacionDia]) -> dict[str, object]:
    """Cuántos días no se evaluaron, y por qué motivo (estado y motivos del día)."""
    rechazados = [e for e in evaluaciones if not e.evaluado]
    por_motivo = Counter(m for e in rechazados for m in e.motivos)
    return {
        "dias": len(evaluaciones),
        "excluidos": len(rechazados),
        "por_motivo": dict(sorted(por_motivo.items())),
    }
