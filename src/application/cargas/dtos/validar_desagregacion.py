"""src/application/cargas/dtos/validar_desagregacion.py — Métricas de validación de un día sin verdad de terreno."""

from pydantic import BaseModel, Field


class CargaValidacionDTO(BaseModel):
    """Resumen de una carga del catálogo en el día validado."""

    nombre: str
    intervalos: int
    cerrados: int
    abiertos: int
    cortados: int
    horas: float
    energia_kwh: float


class MetricasDiaDTO(BaseModel):
    """Métricas de la desagregación de un día, sin comparar contra verdad de terreno.

    Invariante: `eventos_atribuidos + eventos_sin_atribuir == eventos`, con
    `eventos_atribuidos = 2 * intervalos_cerrados + intervalos_abiertos`.
    """

    mediciones: int
    huecos_mayores_a_5_min: int
    umbral_kw: float
    energia_medida_kwh: float
    eventos: int
    encendidos: int
    apagados: int
    eventos_atribuidos: int
    eventos_sin_atribuir: int
    intervalos_cerrados: int
    intervalos_abiertos: int
    intervalos_cortados_por_caida: int
    energia_atribuida_kwh: float
    pct_energia_atribuida: float
    energia_atribuida_excede_medida: bool
    solapamientos: int = Field(
        description="Pares de intervalos de cargas distintas que se superponen"
    )
    horas_solapadas: float
    cargas: list[CargaValidacionDTO] = Field(default_factory=list)
