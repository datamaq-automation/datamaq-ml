"""Issue #20 (validación sin verdad de terreno): cobertura de energía y residuo de un día. Datos sintéticos.

Energía medida y energía atribuida por intervalo de 15 min (kWh). Un día sin etiquetas: solo se puede comparar
lo medido contra lo que el algoritmo atribuyó, y mirar dónde queda el residuo.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_20.py
"""

from __future__ import annotations

MEDIDO = [2.0, 2.0, 5.0, 5.0, 2.0, 2.0, 3.0, 3.0]
ATRIBUIDO = [2.0, 2.0, 4.0, 4.0, 2.0, 2.0, 3.0, 0.0]


def calcular_cobertura(medido: list[float], atribuido: list[float]) -> float:
    """Calcula la cobertura de energía total: sum(atribuido) / sum(medido)."""
    total_m = sum(medido)
    if total_m == 0:
        return 0.0
    return sum(atribuido) / total_m


def calcular_residuo(medido: list[float], atribuido: list[float]) -> list[float]:
    """Calcula el residuo por intervalo: R_i = medido_i - atribuido_i."""
    if len(medido) != len(atribuido):
        raise ValueError("Las series deben tener la misma longitud.")
    return [round(m - a, 2) for m, a in zip(medido, atribuido, strict=False)]


def intervalos_residuo_critico(residuo: list[float], umbral: float = 0.5) -> list[int]:
    """Devuelve los índices de los intervalos cuyo residuo supera el umbral."""
    return [i for i, r in enumerate(residuo) if r > umbral]


def evaluar_consistencia_dia(
    medido: list[float],
    atribuido: list[float],
    umbral_residuo: float = 0.5,
    cobertura_minima: float = 0.70,
) -> tuple[bool, str]:
    """Evalúa la plausibilidad de la desagregación de un día sin verdad de terreno."""
    if len(medido) != len(atribuido):
        return False, "Longitudes dispares de series"

    total_m = sum(medido)
    total_a = sum(atribuido)

    if total_a > total_m:
        return False, "La energía atribuida total excede la energía medida"

    for i, (m, a) in enumerate(zip(medido, atribuido, strict=False)):
        if a > m:
            return False, f"Energía inventada en intervalo {i}: atribuido ({a}) > medido ({m})"

    cob = calcular_cobertura(medido, atribuido)
    if cob < cobertura_minima:
        return False, f"Cobertura insuficiente: {cob:.1%} < {cobertura_minima:.1%}"

    residuos = calcular_residuo(medido, atribuido)
    criticos = intervalos_residuo_critico(residuos, umbral_residuo)
    suma_critica = sum(residuos[i] for i in criticos)
    if total_m > 0 and (suma_critica / total_m) > 0.20:
        return False, (
            f"Residuo concentrado en intervalos {criticos}: suma {suma_critica:.1f} kWh "
            f"({(suma_critica / total_m):.1%} del total)"
        )

    return True, f"Día consistente (cobertura {cob:.1%})"


if __name__ == "__main__":
    total_medido = sum(MEDIDO)
    total_atribuido = sum(ATRIBUIDO)
    cobertura = calcular_cobertura(MEDIDO, ATRIBUIDO)
    residuo = calcular_residuo(MEDIDO, ATRIBUIDO)
    con_residuo = intervalos_residuo_critico(residuo, umbral=0.5)

    print(
        f"energía medida {total_medido:.1f} kWh, atribuida {total_atribuido:.1f} kWh, cobertura {cobertura:.1%}"
    )
    print(f"residuo por intervalo: {residuo}")
    print(
        f"intervalos con residuo > 0,5 kWh: {con_residuo}, suman {sum(residuo[i] for i in con_residuo):.1f} kWh"
    )

    assert total_medido == 24.0 and total_atribuido == 19.0
    assert round(cobertura, 3) == 0.792
    assert con_residuo == [2, 3, 7]
    print("la cobertura no dice dónde falla: el residuo se concentra en los intervalos 2, 3 y 7")
