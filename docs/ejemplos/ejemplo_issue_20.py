"""Issue #20 (validación sin verdad de terreno): cobertura de energía y residuo de un día. Datos sintéticos.

Energía medida y energía atribuida por intervalo de 15 min (kWh). Un día sin etiquetas: solo se puede comparar
lo medido contra lo que el algoritmo atribuyó, y mirar dónde queda el residuo.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_20.py
"""

MEDIDO = [2.0, 2.0, 5.0, 5.0, 2.0, 2.0, 3.0, 3.0]
ATRIBUIDO = [2.0, 2.0, 4.0, 4.0, 2.0, 2.0, 3.0, 0.0]

if __name__ == "__main__":
    total_medido = sum(MEDIDO)
    total_atribuido = sum(ATRIBUIDO)
    cobertura = total_atribuido / total_medido
    residuo = [round(m - a, 2) for m, a in zip(MEDIDO, ATRIBUIDO, strict=False)]
    con_residuo = [i for i, r in enumerate(residuo) if r > 0.5]
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
