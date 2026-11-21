"""src/application/cargas/dtos/desagregar_cargas.py — Contratos DTO para desagregación y atribución batch de cargas."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from src.domain.cargas.entities import Medicion


class FirmaConfirmadaDTO(BaseModel):
    """Firma de una carga electromecánica confirmada por el usuario o catálogo."""

    machine_id: str
    nombre: str
    potencia_nominal_kw: float
    reactiva_tipica_kvar: float = 0.0
    tolerancia_kw: float = 5.0
    umbral_marcha_kw: float = 1.0


class IntervaloMarchaDTO(BaseModel):
    """Intervalo de marcha efectivo asignado a una máquina."""

    machine_id: str
    nombre: str
    inicio: datetime
    fin: datetime
    duracion_segundos: float
    potencia_media_kw: float
    reactiva_media_kvar: float
    cos_phi_medio: float
    energia_kwh: float


class ResumenMaquinaDTO(BaseModel):
    """Resumen acumulado del horómetro y energía de una máquina en la jornada."""

    machine_id: str
    nombre: str
    horas_marcha: float
    ciclos: int
    energia_kwh: float
    potencia_nominal_kw: float


class AtribuirCargasBatchRequestDTO(BaseModel):
    """Petición de procesamiento batch de desagregación para una jornada cerrada."""

    dispositivo_id: str
    fecha: date
    mediciones: list[Medicion] = Field(default_factory=list)
    firmas: list[FirmaConfirmadaDTO] = Field(default_factory=list)


class AtribuirCargasBatchResponseDTO(BaseModel):
    """Respuesta con los intervalos y el resumen acumulado por máquina."""

    dispositivo_id: str
    fecha: date
    intervalos: list[IntervaloMarchaDTO] = Field(default_factory=list)
    resumen_maquinas: list[ResumenMaquinaDTO] = Field(default_factory=list)
