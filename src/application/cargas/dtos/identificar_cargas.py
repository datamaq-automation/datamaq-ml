"""src/application/cargas/dtos/identificar_cargas.py — Contratos de entrada/salida de IdentificarCargas."""

from datetime import datetime

from pydantic import BaseModel, Field, computed_field, model_validator


class IdentificarCargasRequest(BaseModel):
    medidor: str = Field(min_length=1, examples=["Trafo arriba"])
    desde: datetime
    hasta: datetime

    @model_validator(mode="after")
    def validar_rango(self) -> "IdentificarCargasRequest":
        if self.hasta <= self.desde:
            raise ValueError("'hasta' debe ser posterior a 'desde'.")
        return self


class CargaResponse(BaseModel):
    potencia_tipica_kw: float
    encendidos: int
    apagados: int
    ciclos: int
    ciclos_por_dia: float | None = Field(
        default=None, description="None si el rango es menor a un día"
    )
    on_off: bool = Field(
        default=True,
        description="Encendidos y apagados parecidos: se comporta como un equipo ON/OFF",
    )
    dispersion_kw: float = Field(
        default=0.0, description="Desvío estándar de |ΔP| de los eventos de la carga, en kW"
    )
    reactiva_tipica_kvar: float = 0.0
    cos_phi_estimado: float | None = None
    ratio_qp_mediana: float | None = Field(
        default=None, description="Mediana de |ΔQ|/|ΔP| de los eventos de la carga"
    )

    @computed_field
    def potencia_kw(self) -> float:
        """Alias para compatibilidad con consumidores externos (datamaq-telemetry)."""
        return self.potencia_tipica_kw


class PuntoResponse(BaseModel):
    instante: datetime
    potencia_kw: float


class EventoResponse(BaseModel):
    instante: datetime
    delta_kw: float = Field(description="Positivo: encendido; negativo: apagado")
    carga_kw: float | None = Field(
        description="Potencia típica de la carga a la que pertenece; None si quedó sin grupo"
    )


class BarraHistogramaResponse(BaseModel):
    desde_kw: float
    hasta_kw: float
    cantidad: int


class UmbralResponse(BaseModel):
    kw: float | None = Field(description="Umbral |ΔP| usado; None si no se pudo estimar")
    automatico: bool
    separacion: float | None = Field(default=None, description="η de Otsu (solo si es automático)")
    confiable: bool | None = Field(
        default=None, description="η >= separación mínima (solo si es automático)"
    )
    regimen: str | None = Field(
        default=None,
        description="otsu (η confiable), valle_claro (η bajo y valle claro) o sin_modos_separables",
    )


class ModoResponse(BaseModel):
    desde_kw: float
    hasta_kw: float
    cantidad: int
    centro_kw: float
    dispersion_kw: float = Field(description="σ de |ΔP| dentro de ±3σ del centro")
    radio_kw: float = Field(description="Radio del modo: 2σ")


class AgrupamientoResponse(BaseModel):
    radio_kw: float | None = Field(description="Radio de DBSCAN usado; None si no hubo eventos")
    radio_automatico: bool
    min_eventos: int = Field(description="Eventos mínimos para que un grupo sea una carga")
    min_eventos_automatico: bool


class SaltosBajoUmbralResponse(BaseModel):
    cantidad: int = Field(default=0, description="Cantidad de saltos que quedaron bajo el umbral")
    energia_kwh: float = Field(
        default=0.0, description="Energía estimada de los intervalos bajo el umbral, en kWh"
    )


class IdentificarCargasResponse(BaseModel):
    medidor: str
    mediciones: int
    eventos: int
    encendidos: int = 0
    apagados: int = 0
    eventos_sin_grupo: int = Field(default=0, description="Eventos que DBSCAN dejó como ruido")
    sin_modos_separables: bool = Field(
        default=False,
        description="η bajo y sin valle claro: no se agrupan cargas (no se inventan clústeres)",
    )
    modos: list[ModoResponse] = Field(
        default_factory=list, description="Modos separables por valle, con radio por modo"
    )
    dias: float = Field(default=0.0, description="Días cubiertos por las mediciones")
    potencia_media_kw: float
    cargas: list[CargaResponse]
    umbral: UmbralResponse
    agrupamiento: AgrupamientoResponse
    saltos_bajo_umbral: SaltosBajoUmbralResponse = Field(
        default_factory=lambda: SaltosBajoUmbralResponse(cantidad=0, energia_kwh=0.0),
        description="Saltos y energía desestimados por quedar bajo el umbral",
    )
    serie: list[PuntoResponse] = Field(
        default_factory=list, description="Potencia en el tiempo (paso 1)"
    )
    detalle_eventos: list[EventoResponse] = Field(
        default_factory=list, description="Cada evento, para marcarlo en la serie"
    )
    histograma: list[BarraHistogramaResponse] = Field(
        description="Distribución de |ΔP|: ruido a la izquierda, eventos a la derecha"
    )
