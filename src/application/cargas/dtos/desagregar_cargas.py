"""src/application/cargas/dtos/desagregar_cargas.py — Contratos DTO de la desagregación batch diaria.

La salida es el contrato `nilm.intervalos.v1` que consume datamaq-telemetry (informe de la
investigación, §5): claves exactas, sin campos extra. Los instantes de la salida llevan zona UTC
(`Z`). Internamente, los instantes de las mediciones y de la ventana son UTC sin zona.
"""

from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from src.domain.cargas.banco_capacitores import (
    TOLERANCIA_COINCIDENCIA,
    UMBRAL_P_BANCO_KW,
    UMBRAL_Q_BANCO_KVAR,
)
from src.domain.cargas.entities import Medicion

CONTRATO_INTERVALOS = "nilm.intervalos.v1"
ZONA_HORARIA_DIA = "America/Argentina/Buenos_Aires"


class FirmaConfirmadaDTO(BaseModel):
    """Firma de una carga electromecánica confirmada en el catálogo.

    `machine_id` es el identificador de la firma dentro del catálogo (no sale en el JSON).
    `load_id` es el uuid de `loads.id` en telemetry, si la carga ya está mapeada; si no, None.
    """

    machine_id: str
    nombre: str
    potencia_nominal_kw: float
    reactiva_tipica_kvar: float = 0.0
    tolerancia_kw: float = 5.0
    umbral_marcha_kw: float = 1.0
    load_id: str | None = None
    dispersion_kw: float | None = None  # dispersión medida del grupo (descubrimiento); opcional


class ParametrosBancoDTO(BaseModel):
    """Cómo tratar las conmutaciones de banco y cuánto pesa la reactiva en el emparejamiento.

    Los pesos por defecto son iguales (1 y 1), que es lo que corre hoy. El default de ΔP sobre ΔQ no se fija
    todavía: se decide con datos reales (adenda del 2026-11-22). Con peso_q = 0 el emparejamiento usa solo P.
    """

    umbral_p_kw: float = UMBRAL_P_BANCO_KW
    umbral_q_kvar: float = UMBRAL_Q_BANCO_KVAR
    tolerancia: timedelta = TOLERANCIA_COINCIDENCIA
    peso_p: float = Field(default=1.0, ge=0.0)
    peso_q: float = Field(default=1.0, ge=0.0)


class ParametrosMotorDTO(BaseModel):
    """Parámetros de detección y emparejamiento del motor. Los defaults reproducen el comportamiento previo.

    `muestras_debounce`: 1 no filtra nada; 2 descarta picos de una lectura (con costo: también ciclos reales
    de menos de 2 muestras). Ver el informe de debounce en el PR.
    """

    muestras_debounce: int = Field(default=1, ge=1)
    tolerancia_por_dispersion: bool = False
    factor_dispersion: float = Field(default=2.0, gt=0)
    tolerancia_min_kw: float = Field(default=2.0, ge=0)
    tolerancia_max_kw: float = Field(default=8.0, gt=0)


class AtribuirCargasBatchRequestDTO(BaseModel):
    """Petición de desagregación de un día cerrado de un medidor.

    `device_id` es la clave del medidor (uuid de `devices.id` en telemetry). `etiqueta_ml` es el
    nombre humano que usa datamaq-ml y no identifica nada por sí solo.
    `ventana_desde_utc` (inclusive) y `ventana_hasta_utc` (exclusive) delimitan el día local en UTC.
    """

    device_id: str
    etiqueta_ml: str
    fecha_local: date
    ventana_desde_utc: datetime
    ventana_hasta_utc: datetime
    generado_en_utc: datetime
    mediciones: list[Medicion] = Field(default_factory=list)
    firmas: list[FirmaConfirmadaDTO] = Field(default_factory=list)
    parametros_banco: ParametrosBancoDTO = Field(default_factory=ParametrosBancoDTO)
    parametros_motor: ParametrosMotorDTO = Field(default_factory=ParametrosMotorDTO)
    umbral_deteccion_kw: float | None = Field(
        default=None,
        description="Umbral |ΔP| de detección; None = el mínimo de las firmas (comportamiento previo)",
    )


class IntervaloMarchaDTO(BaseModel):
    """Intervalo de marcha de una carga, con magnitudes medidas (no nominales).

    `energia_kwh_medida` sale de la energía acumulada del medidor si la fuente la trae; si no, de
    integrar la potencia. En ambos casos se resta la carga base previa al encendido. `delta_reactiva_kvar`
    es la reactiva media del intervalo menos la base; None si la fuente no trae reactiva.
    `confianza` está en [0, 1]: qué tan cerca estuvieron los saltos de encendido y apagado de la firma.
    """

    inicio_utc: datetime
    fin_utc: datetime
    horas: float
    energia_kwh_medida: float
    potencia_media_kw: float
    delta_reactiva_kvar: float | None
    confianza: float
    origen: Literal["INFERIDA"] = "INFERIDA"


class CargaDTO(BaseModel):
    """Una carga del catálogo y sus intervalos del día."""

    load_id: str | None
    nombre: str
    intervalos: list[IntervaloMarchaDTO] = Field(default_factory=list)


class MedidorDTO(BaseModel):
    """Medidor procesado. `ultima_lectura_utc` es la última medición real del día; None si no hubo."""

    device_id: str
    etiqueta_ml: str
    ultima_lectura_utc: datetime | None


class VentanaUtcDTO(BaseModel):
    """Ventana del día en UTC: desde inclusive, hasta exclusive."""

    desde: datetime
    hasta: datetime


class AtribuirCargasBatchResponseDTO(BaseModel):
    """Salida del batch: el contrato `nilm.intervalos.v1`."""

    contrato: Literal["nilm.intervalos.v1"] = CONTRATO_INTERVALOS
    generado_en_utc: datetime
    fecha_local: date
    zona_horaria: str = ZONA_HORARIA_DIA
    ventana_utc: VentanaUtcDTO
    medidor: MedidorDTO
    cargas: list[CargaDTO] = Field(default_factory=list)
