"""src/application/cargas/use_cases/atribuir_cargas_batch.py — Caso de uso: atribución batch diaria de cargas NILM."""

import math
from collections import defaultdict
from datetime import datetime, time

from src.application.cargas.dtos.desagregar_cargas import (
    AtribuirCargasBatchRequestDTO,
    AtribuirCargasBatchResponseDTO,
    FirmaConfirmadaDTO,
    IntervaloMarchaDTO,
    ResumenMaquinaDTO,
)
from src.domain.cargas.entities import EventoCarga
from src.domain.cargas.services import detectar_eventos


class AtribuirCargasBatchUseCase:
    """Procesa mediciones de una jornada cerrada y atribuye intervalos de marcha a máquinas confirmadas."""

    def ejecutar(self, request: AtribuirCargasBatchRequestDTO) -> AtribuirCargasBatchResponseDTO:
        if not request.firmas or not request.mediciones:
            return AtribuirCargasBatchResponseDTO(
                dispositivo_id=request.dispositivo_id,
                fecha=request.fecha,
                intervalos=[],
                resumen_maquinas=[
                    ResumenMaquinaDTO(
                        machine_id=f.machine_id,
                        nombre=f.nombre,
                        horas_marcha=0.0,
                        ciclos=0,
                        energia_kwh=0.0,
                        potencia_nominal_kw=f.potencia_nominal_kw,
                    )
                    for f in request.firmas
                ],
            )

        umbral_minimo = min(
            max(f.umbral_marcha_kw, f.potencia_nominal_kw - f.tolerancia_kw, 0.1)
            for f in request.firmas
        )
        eventos = detectar_eventos(request.mediciones, umbral_kw=umbral_minimo)

        intervalos = self._emparejar_eventos(request, eventos)
        resumenes = self._consolidar_resumenes(request.firmas, intervalos)

        return AtribuirCargasBatchResponseDTO(
            dispositivo_id=request.dispositivo_id,
            fecha=request.fecha,
            intervalos=intervalos,
            resumen_maquinas=resumenes,
        )

    def _emparejar_eventos(
        self,
        request: AtribuirCargasBatchRequestDTO,
        eventos: list[EventoCarga],
    ) -> list[IntervaloMarchaDTO]:
        limite_fin_jornada = datetime.combine(request.fecha, time(23, 59, 59))
        intervalos: list[IntervaloMarchaDTO] = []
        encendidos_activos: dict[str, EventoCarga] = {}

        for ev in eventos:
            if ev.es_encendido:
                firma = self._buscar_firma_compatible(ev, request.firmas)
                if firma and firma.machine_id not in encendidos_activos:
                    encendidos_activos[firma.machine_id] = ev
            else:
                firma = self._buscar_firma_compatible(ev, request.firmas)
                if firma and firma.machine_id in encendidos_activos:
                    ev_on = encendidos_activos.pop(firma.machine_id)
                    intervalos.append(self._crear_intervalo(firma, ev_on.instante, ev.instante))

        for machine_id, ev_on in encendidos_activos.items():
            firma = next(f for f in request.firmas if f.machine_id == machine_id)
            fin_efectivo = max(ev_on.instante, limite_fin_jornada)
            intervalos.append(self._crear_intervalo(firma, ev_on.instante, fin_efectivo))

        return sorted(intervalos, key=lambda it: it.inicio)

    def _buscar_firma_compatible(
        self,
        evento: EventoCarga,
        firmas: list[FirmaConfirmadaDTO],
    ) -> FirmaConfirmadaDTO | None:
        delta_p = abs(evento.delta_kw)
        delta_q = abs(evento.delta_kvar)

        candidatas: list[tuple[float, FirmaConfirmadaDTO]] = []
        for firma in firmas:
            dist_p = abs(delta_p - firma.potencia_nominal_kw)
            if dist_p <= firma.tolerancia_kw:
                # Distancia euclidiana en el plano P-Q si hay reactiva confirmada o detectada
                dist_q = abs(delta_q - firma.reactiva_tipica_kvar)
                distancia = math.sqrt(dist_p**2 + dist_q**2)
                candidatas.append((distancia, firma))

        if not candidatas:
            return None

        candidatas.sort(key=lambda t: t[0])
        return candidatas[0][1]

    def _crear_intervalo(
        self,
        firma: FirmaConfirmadaDTO,
        inicio: datetime,
        fin: datetime,
    ) -> IntervaloMarchaDTO:
        duracion_segundos = max(0.0, (fin - inicio).total_seconds())
        horas = duracion_segundos / 3600.0
        potencia_media = firma.potencia_nominal_kw
        reactiva_media = firma.reactiva_tipica_kvar
        energia_kwh = round(potencia_media * horas, 3)

        if potencia_media > 0:
            cos_phi = round(math.cos(math.atan2(abs(reactiva_media), abs(potencia_media))), 3)
        else:
            cos_phi = 1.0

        return IntervaloMarchaDTO(
            machine_id=firma.machine_id,
            nombre=firma.nombre,
            inicio=inicio,
            fin=fin,
            duracion_segundos=duracion_segundos,
            potencia_media_kw=potencia_media,
            reactiva_media_kvar=reactiva_media,
            cos_phi_medio=cos_phi,
            energia_kwh=energia_kwh,
        )

    def _consolidar_resumenes(
        self,
        firmas: list[FirmaConfirmadaDTO],
        intervalos: list[IntervaloMarchaDTO],
    ) -> list[ResumenMaquinaDTO]:
        intervalos_por_maquina: dict[str, list[IntervaloMarchaDTO]] = defaultdict(list)
        for it in intervalos:
            intervalos_por_maquina[it.machine_id].append(it)

        resumenes: list[ResumenMaquinaDTO] = []
        for f in firmas:
            its = intervalos_por_maquina[f.machine_id]
            horas_totales = sum(it.duracion_segundos for it in its) / 3600.0
            energia_total = sum(it.energia_kwh for it in its)
            resumenes.append(
                ResumenMaquinaDTO(
                    machine_id=f.machine_id,
                    nombre=f.nombre,
                    horas_marcha=round(horas_totales, 3),
                    ciclos=len(its),
                    energia_kwh=round(energia_total, 3),
                    potencia_nominal_kw=f.potencia_nominal_kw,
                )
            )

        return sorted(resumenes, key=lambda r: r.horas_marcha, reverse=True)
