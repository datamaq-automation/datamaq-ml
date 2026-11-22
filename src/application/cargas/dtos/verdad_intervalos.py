"""src/application/cargas/dtos/verdad_intervalos.py — Verdad de terreno por intervalos: contrato nilm.verdad.v1.

Es la misma forma que `nilm.intervalos.v1` (la salida del batch), con dos diferencias:
- `contrato` es "nilm.verdad.v1" y el origen de cada intervalo es "MEDIDO" (no "INFERIDA"): viene de un
  contactor o de un simulador, no de una inferencia;
- el esquema es estricto (`extra="forbid"`): ninguna clave que no esté en el contrato.
Los campos de energía y potencia son opcionales: un contactor dice si la máquina está en marcha, no cuánto
consume. Un simulador que conoce la potencia puede llenarlos para evaluar el error de energía.

`nilm.intervalos.v1` no cambia ni se toca desde acá: el evaluador compara una salida contra esta verdad.
"""

from datetime import date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from src.application.cargas.dtos.desagregar_cargas import ZONA_HORARIA_DIA

CONTRATO_VERDAD = "nilm.verdad.v1"
ORIGEN_MEDIDO = "MEDIDO"
TOLERANCIA_HORAS = 1e-3


def _exige_utc(valor: datetime) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() != timedelta(0):
        raise ValueError("el instante debe tener zona UTC (sufijo Z)")
    return valor


class IntervaloVerdadDTO(BaseModel):
    """Un intervalo en el que la máquina estuvo en marcha según la verdad."""

    model_config = ConfigDict(extra="forbid")

    inicio_utc: Annotated[datetime, AfterValidator(_exige_utc)]
    fin_utc: Annotated[datetime, AfterValidator(_exige_utc)]
    horas: float = Field(ge=0)
    energia_kwh_medida: float | None = None
    potencia_media_kw: float | None = None
    delta_reactiva_kvar: float | None = None
    confianza: float = Field(default=1.0, ge=0, le=1)
    origen: Literal["MEDIDO"] = ORIGEN_MEDIDO

    @model_validator(mode="after")
    def coherente(self) -> "IntervaloVerdadDTO":
        if self.fin_utc <= self.inicio_utc:
            raise ValueError("fin_utc debe ser posterior a inicio_utc")
        duracion = (self.fin_utc - self.inicio_utc).total_seconds() / 3600.0
        if abs(self.horas - duracion) > TOLERANCIA_HORAS:
            raise ValueError("horas no coincide con fin_utc - inicio_utc")
        return self


class VentanaVerdadDTO(BaseModel):
    """Ventana del día en UTC, desde inclusive y hasta exclusive (la misma forma que en nilm.intervalos.v1)."""

    model_config = ConfigDict(extra="forbid")

    desde: Annotated[datetime, AfterValidator(_exige_utc)]
    hasta: Annotated[datetime, AfterValidator(_exige_utc)]


class CargaVerdadDTO(BaseModel):
    """Una máquina del medidor: su nombre (la clave de emparejamiento) y sus intervalos de marcha."""

    model_config = ConfigDict(extra="forbid")

    load_id: str | None = None
    nombre: str = Field(min_length=1)
    intervalos: list[IntervaloVerdadDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def ordenados_y_sin_solapar(self) -> "CargaVerdadDTO":
        for previo, siguiente in zip(self.intervalos, self.intervalos[1:], strict=False):
            if siguiente.inicio_utc < previo.fin_utc:
                raise ValueError(f"intervalos solapados en la máquina {self.nombre!r}")
        return self


class MedidorVerdadDTO(BaseModel):
    """De dónde sale la verdad. `desfase_reloj_s` es el error de reloj aplicado a la verdad, si se conoce."""

    model_config = ConfigDict(extra="forbid")

    device_id: str
    etiqueta_ml: str
    fuente: Literal["simulador", "automata"]
    desfase_reloj_s: float | None = None


class VerdadIntervalosDTO(BaseModel):
    """Verdad de terreno de un día de un medidor, con la forma de nilm.intervalos.v1."""

    model_config = ConfigDict(extra="forbid")

    contrato: Literal["nilm.verdad.v1"] = CONTRATO_VERDAD
    generado_en_utc: Annotated[datetime, AfterValidator(_exige_utc)]
    fecha_local: date
    zona_horaria: str = ZONA_HORARIA_DIA
    ventana_utc: VentanaVerdadDTO
    medidor: MedidorVerdadDTO
    cargas: list[CargaVerdadDTO] = Field(default_factory=list)

    @model_validator(mode="after")
    def dentro_de_la_ventana_y_nombres_unicos(self) -> "VerdadIntervalosDTO":
        nombres = [c.nombre for c in self.cargas]
        if len(set(nombres)) != len(nombres):
            raise ValueError("nombres de máquina repetidos")
        for carga in self.cargas:
            for intervalo in carga.intervalos:
                if intervalo.inicio_utc < self.ventana_utc.desde:
                    raise ValueError("intervalo antes de la ventana")
                if intervalo.fin_utc > self.ventana_utc.hasta:
                    raise ValueError("intervalo después de la ventana")
        return self
