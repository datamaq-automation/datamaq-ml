"""src/application/cargas/use_cases/sembrar_firmas.py — Siembra firmas confirmables desde el catálogo por placa.

Cada motor con escalón detectable se vuelve una FirmaConfirmadaDTO candidata: potencia nominal de placa y
reactiva esperada por cos φ típico. Las formas sin escalón único (variador, arranque suave) no se siembran:
ninguna firma de escalón podría emparejarlas. Son candidatas: el dueño las confirma antes de usarlas en el batch.
"""

from src.application.cargas.dtos.desagregar_cargas import FirmaConfirmadaDTO
from src.domain.cargas.catalogo_placa import PlacaMotor, firma_esperada

TOLERANCIA_SEMBRADA_KW = 5.0


def sembrar_firmas(placas: list[PlacaMotor]) -> list[FirmaConfirmadaDTO]:
    firmas = []
    for placa in placas:
        esperada = firma_esperada(placa)
        if not esperada.detectable_como_escalon:
            continue
        firmas.append(
            FirmaConfirmadaDTO(
                machine_id=placa.etiqueta,
                nombre=placa.etiqueta,
                potencia_nominal_kw=esperada.potencia_nominal_kw,
                reactiva_tipica_kvar=esperada.reactiva_esperada_kvar,
                tolerancia_kw=TOLERANCIA_SEMBRADA_KW,
            )
        )
    return firmas
