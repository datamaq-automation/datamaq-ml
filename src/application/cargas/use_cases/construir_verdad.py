"""src/application/cargas/use_cases/construir_verdad.py — Arma la verdad nilm.verdad.v1 desde un simulador.

El simulador conoce la potencia de cada carga, así que la verdad que arma trae energía (potencia × horas) y
el error de energía se puede evaluar. Una verdad de autómata no la tendría: solo marcha o parada.
La línea de tiempo del simulador es UTC; la ventana cubre el desfase de reloj en ambos extremos.
"""

from datetime import UTC, datetime, timedelta

from src.application.cargas.dtos.verdad_intervalos import (
    CargaVerdadDTO,
    IntervaloVerdadDTO,
    MedidorVerdadDTO,
    VentanaVerdadDTO,
    VerdadIntervalosDTO,
)


def construir_verdad_simulada(
    maquinas: list[tuple[str, float]],
    tramos_por_maquina: list[list[tuple[datetime, datetime]]],
    inicio: datetime,
    dias: int,
    desfase_s: float,
    etiqueta: str,
    device_id: str,
) -> VerdadIntervalosDTO:
    """`maquinas` son (nombre, potencia nominal kW) en el mismo orden que `tramos_por_maquina`."""
    if len(maquinas) != len(tramos_por_maquina):
        raise ValueError("Cada máquina necesita su lista de intervalos.")
    inicio_utc = inicio.replace(tzinfo=UTC)
    margen = timedelta(seconds=abs(desfase_s) + 1)
    cargas = [
        CargaVerdadDTO(
            nombre=nombre,
            intervalos=[_intervalo(desde, hasta, potencia) for desde, hasta in tramos],
        )
        for (nombre, potencia), tramos in zip(maquinas, tramos_por_maquina, strict=True)
    ]
    return VerdadIntervalosDTO(
        generado_en_utc=inicio_utc + timedelta(days=dias),
        fecha_local=inicio.date(),
        ventana_utc=VentanaVerdadDTO(
            desde=inicio_utc - margen,
            hasta=inicio_utc + timedelta(days=dias) + margen,
        ),
        medidor=MedidorVerdadDTO(
            device_id=device_id,
            etiqueta_ml=etiqueta,
            fuente="simulador",
            desfase_reloj_s=desfase_s,
        ),
        cargas=cargas,
    )


def _intervalo(desde: datetime, hasta: datetime, potencia_kw: float) -> IntervaloVerdadDTO:
    desde_utc, hasta_utc = desde.replace(tzinfo=UTC), hasta.replace(tzinfo=UTC)
    horas = round((hasta_utc - desde_utc).total_seconds() / 3600.0, 6)
    return IntervaloVerdadDTO(
        inicio_utc=desde_utc,
        fin_utc=hasta_utc,
        horas=horas,
        energia_kwh_medida=round(potencia_kw * horas, 3),
        potencia_media_kw=potencia_kw,
    )
