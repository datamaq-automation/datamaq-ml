"""tests/unit/cargas/test_atribuir_banco.py — Emparejamiento con pesos de P y Q, y conmutaciones de banco (datos sintéticos)."""

from datetime import date, datetime

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    FirmaConfirmadaDTO,
    ParametrosBancoDTO,
)
from src.application.cargas.use_cases.atribuir_cargas_batch import (
    AtribuirCargasBatchUseCase,
    buscar_firma_compatible,
)
from src.domain.cargas.entities import EventoCarga, Medicion

DESDE = datetime(2026, 9, 20, 3, 0)
HASTA = datetime(2026, 9, 21, 3, 0)
X = FirmaConfirmadaDTO(
    machine_id="x",
    nombre="X",
    potencia_nominal_kw=50.0,
    reactiva_tipica_kvar=40.0,
    tolerancia_kw=5.0,
)
Y = FirmaConfirmadaDTO(
    machine_id="y",
    nombre="Y",
    potencia_nominal_kw=48.0,
    reactiva_tipica_kvar=0.0,
    tolerancia_kw=5.0,
)


def _t(h: int, m: int) -> datetime:
    return datetime(2026, 9, 20, h, m)


def _ejecutar(mediciones: list[Medicion], params: ParametrosBancoDTO | None = None):
    return AtribuirCargasBatchUseCase().ejecutar(
        AtribuirCargasBatchRequestDTO(
            device_id="prueba",
            etiqueta_ml="prueba",
            fecha_local=date(2026, 9, 20),
            ventana_desde_utc=DESDE,
            ventana_hasta_utc=HASTA,
            generado_en_utc=DESDE,
            mediciones=mediciones,
            firmas=[X, Y],
            parametros_banco=params or ParametrosBancoDTO(),
        )
    )


def _intervalos(resp, nombre: str) -> list:
    return next(c.intervalos for c in resp.cargas if c.nombre == nombre)


def test_con_delta_q_confiable_el_escalon_se_empareja_por_p_y_q() -> None:
    evento = EventoCarga(instante=_t(10, 0), delta_kw=50.0, delta_kvar=0.0)
    encontrada = buscar_firma_compatible(evento, [X, Y], ParametrosBancoDTO(), usar_q=True)
    assert encontrada is not None and encontrada[0].machine_id == "y"


def test_con_delta_q_contaminada_se_usa_solo_p() -> None:
    evento = EventoCarga(instante=_t(10, 0), delta_kw=50.0, delta_kvar=0.0)
    encontrada = buscar_firma_compatible(evento, [X, Y], ParametrosBancoDTO(), usar_q=False)
    assert encontrada is not None and encontrada[0].machine_id == "x"


def test_peso_de_q_en_cero_equivale_a_usar_solo_p() -> None:
    evento = EventoCarga(instante=_t(10, 0), delta_kw=50.0, delta_kvar=0.0)
    encontrada = buscar_firma_compatible(
        evento, [X, Y], ParametrosBancoDTO(peso_q=0.0), usar_q=True
    )
    assert encontrada is not None and encontrada[0].machine_id == "x"


def test_los_pesos_por_defecto_son_iguales() -> None:
    params = ParametrosBancoDTO()
    assert params.peso_p == 1.0
    assert params.peso_q == 1.0


def test_un_paso_de_banco_no_crea_intervalos_ni_cambia_la_atribucion() -> None:
    base = [
        Medicion(instante=_t(9, 55), potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=_t(10, 0), potencia_kw=60.0, reactiva_kvar=45.0),
    ]
    sin_banco = base + [Medicion(instante=_t(10, 30), potencia_kw=60.0, reactiva_kvar=45.0)]
    con_banco = base + [
        Medicion(instante=_t(10, 30), potencia_kw=60.0, reactiva_kvar=25.0)
    ]  # banco: -20 kvar
    fin = [Medicion(instante=_t(11, 0), potencia_kw=10.0, reactiva_kvar=5.0)]

    a = _intervalos(_ejecutar(sin_banco + fin), "X")
    b = _intervalos(_ejecutar(con_banco + fin), "X")
    assert len(a) == len(b) == 1
    assert abs(a[0].energia_kwh_medida - b[0].energia_kwh_medida) < 0.5


def test_escalon_con_delta_q_contaminada_se_atribuye_por_potencia_activa() -> None:
    """Motor X (50 kW, 40 kvar) y carga Y (48 kW, sin reactiva). El arranque y la parada del motor
    tienen ΔQ = 0 por una conmutación del banco en la misma ventana: el emparejamiento usa solo P,
    así que se atribuye a X (sin contaminación, la ΔQ 0 lo llevaría a Y)."""
    mediciones = [
        Medicion(instante=_t(9, 55), potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=_t(10, 0), potencia_kw=60.0, reactiva_kvar=5.0),  # arranque: ΔQ 0
        Medicion(instante=_t(10, 5), potencia_kw=60.1, reactiva_kvar=-5.0),  # banco: -10 kvar
        Medicion(instante=_t(10, 55), potencia_kw=60.1, reactiva_kvar=5.0),  # banco: +10 kvar
        Medicion(instante=_t(11, 0), potencia_kw=10.1, reactiva_kvar=5.0),  # parada: ΔQ 0
    ]
    resp = _ejecutar(mediciones)
    assert len(_intervalos(resp, "X")) == 1
    assert _intervalos(resp, "Y") == []


def test_sin_banco_el_mismo_escalon_se_atribuye_por_reactiva() -> None:
    """Control del caso anterior: sin la conmutación, la ΔQ 0 sí cuenta y el escalón va a Y."""
    mediciones = [
        Medicion(instante=_t(9, 55), potencia_kw=10.0, reactiva_kvar=5.0),
        Medicion(instante=_t(10, 0), potencia_kw=60.0, reactiva_kvar=5.0),
        Medicion(instante=_t(11, 0), potencia_kw=10.1, reactiva_kvar=5.0),
    ]
    resp = _ejecutar(mediciones)
    assert _intervalos(resp, "X") == []
    assert len(_intervalos(resp, "Y")) == 1
