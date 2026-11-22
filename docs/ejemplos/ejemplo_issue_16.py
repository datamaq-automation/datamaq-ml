"""Issue #16 (sobreajuste y validación): profundidad del árbol con 20 % de etiquetas cambiadas. Datos sintéticos.

Requiere docs/material-ensenanza/practicas/practica_supervisado_arranques.py, que llega con el PR de #25
(rama feat/issue-25-verdad-de-terreno). Hasta que se mergee a develop, correr este script desde esa rama.
Ejecutar desde la raíz del repo: python docs/ejemplos/ejemplo_issue_16.py
"""

import importlib.util
import random

from sklearn.tree import DecisionTreeClassifier

spec = importlib.util.spec_from_file_location(
    "p", "docs/material-ensenanza/practicas/practica_supervisado_arranques.py"
)
practica = importlib.util.module_from_spec(spec)
spec.loader.exec_module(practica)

datos = practica.ejemplos(dias=14, semilla=3)
Xe = [s.rasgos for s, _ in datos[:60]]
ye = [e for _, e in datos[:60]]
Xp = [s.rasgos for s, _ in datos[60:260]]
yp = [e for _, e in datos[60:260]]

r = random.Random(7)
clases = sorted(set(ye))
ruidosa = [y if r.random() > 0.2 else r.choice([c for c in clases if c != y]) for y in ye]
cambiadas = sum(a != b for a, b in zip(ye, ruidosa, strict=False))

if __name__ == "__main__":
    print(f"entrenamiento de 60 con {cambiadas} etiquetas cambiadas; prueba limpia de 200")
    resultados = {}
    for prof in (2, 4, None):
        arbol = DecisionTreeClassifier(max_depth=prof, random_state=0).fit(Xe, ruidosa)
        resultados[prof] = (arbol.score(Xe, ruidosa), arbol.score(Xp, yp), arbol.get_n_leaves())
        print(
            f"profundidad {str(prof):>4}: entrenamiento {resultados[prof][0]:.3f}  prueba {resultados[prof][1]:.3f}  hojas {resultados[prof][2]}"
        )
    assert cambiadas == 19
    assert [round(resultados[p][1], 3) for p in (2, 4, None)] == [0.780, 0.650, 0.575]
    assert [round(resultados[p][0], 3) for p in (2, 4, None)] == [0.717, 0.800, 0.983]
