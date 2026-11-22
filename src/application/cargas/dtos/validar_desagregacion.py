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
    eventos_banco_dp_bajo_dq_alto: int = Field(
        default=0,
        description="Pares con |ΔP| bajo el umbral del banco y |ΔQ| sobre su umbral. Pocos o ninguno apoya banco fijo; muchos lo desmienten (adenda 2026-11-22)",
    )
    eventos_carga_con_banco: int = Field(
        default=0,
        description="Escalones de carga que caen en la misma ventana que una conmutación de banco",
    )
    energia_atribuida_solo_p_kwh: float = Field(
        default=0.0, description="Energía atribuida emparejando solo con ΔP (peso de Q en cero)"
    )
    diferencia_pct_p_vs_pq: float = Field(
        default=0.0,
        description="Cuánto cambia la energía atribuida al usar P y Q frente a solo P, en %",
    )
    pares_candidatos_fusion: int = Field(
        default=0,
        description="Pares de grupos que, por el criterio de fusión, son probablemente la misma máquina",
    )
    solapamientos_tras_fusion: int = Field(
        default=0, description="Solapamientos que quedan después de fusionar los pares candidatos"
    )
    solapamientos: int = Field(
        description="Pares de intervalos de cargas distintas que se superponen"
    )
    horas_solapadas: float
    cargas: list[CargaValidacionDTO] = Field(default_factory=list)
