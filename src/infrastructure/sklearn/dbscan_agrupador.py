"""src/infrastructure/sklearn/dbscan_agrupador.py — Agrupa eventos de carga por |ΔP| con DBSCAN."""

from sklearn.cluster import DBSCAN

from src.domain.cargas.entities import EventoCarga
from src.infrastructure.settings.logger import logger


class DbscanAgrupador:
    """Implementa AgrupadorEventos: encendidos y apagados de la misma carga caen en el mismo grupo."""

    def agrupar(self, eventos: list[EventoCarga], radio_kw: float, min_eventos: int) -> list[int]:
        if not eventos:
            return []

        tiene_reactiva = any(e.delta_kvar != 0.0 for e in eventos)
        if tiene_reactiva:
            muestras = [[abs(e.delta_kw), abs(e.delta_kvar)] for e in eventos]
        else:
            muestras = [[abs(e.delta_kw)] for e in eventos]

        modelo = DBSCAN(eps=radio_kw, min_samples=min_eventos)
        etiquetas = [int(e) for e in modelo.fit_predict(muestras)]
        grupos, ruido = len(set(etiquetas) - {-1}), etiquetas.count(-1)
        logger.info(
            "DBSCAN (%s, eps=%s, min=%s): %d %s",
            "2D P-Q" if tiene_reactiva else "1D P",
            radio_kw,
            min_eventos,
            grupos,
            "grupo" if grupos == 1 else "grupos",
        )
        if ruido:
            logger.warning(
                "%d de %d eventos quedaron como ruido (sin grupo)", ruido, len(etiquetas)
            )
        return etiquetas
