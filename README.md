# Efecto de los swaps de tasas extranjeras en los fondos de pensiones

Proyecto del curso **Mercados Financieros (EAE3301)**, Instituto de Economía UC, prof. Jaime Casassus.
**Fondo analizado:** Fondo E de **AFP Capital**. Se asignó así: la suma de los dígitos verificadores del grupo es 14, y 14 mod 7 = 0.

**Lenguaje:** Python 3. Librerías: pandas, numpy, scipy, matplotlib y openpyxl (ver `requirements.txt`).

## Estructura

```
data/raw/         Datos originales tal como se descargaron; la fecha de descarga va en el nombre del archivo
data/processed/   Datos intermedios generados por los scripts
src/              Código, un script por módulo
output/figs/      Figuras del informe (qN_*.png = pregunta N)
output/tables/    Tablas del informe
report/           Borradores de las secciones del informe
```

## Cómo reproducir

```bash
python -m pip install -r requirements.txt
python src/module1_curves.py      # Módulo I: curvas Nelson-Siegel (Q2–Q7)
```

Ejecute los scripts desde la raíz del repositorio. Cada uno lee de `data/raw/` y escribe en `data/processed/` y `output/`.

## Fuentes de datos

| Archivo | Fuente | Descarga |
|---|---|---|
| `data/raw/fred_cmt_monthly_eom_2026-11-11.csv` | FRED, Federal Reserve Bank of St. Louis (https://fred.stlouisfed.org). Series DGS1MO, DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5, DGS7, DGS10, DGS20 y DGS30, tomando el último dato hábil de cada mes entre oct-2016 y sep-2026 | 11-nov-2026 |
| `data/raw/fed_svenpy_selected_2026-11-11.csv` | Federal Reserve Board, `feds200628.csv` (https://www.federalreserve.gov/data/yield-curve-tables/feds200628_1.html). Series SVENPY01–SVENPY30 al 29-dic-2023, 31-dic-2024, 31-dic-2025 y 30-sep-2026 | 11-nov-2026 |

## Estado

- [x] Módulo I: estimación de la curva par USD (Nelson-Siegel)
- [ ] Módulo II: posiciones en swaps del Fondo E
- [ ] Módulo III: regulación, PV01, mark-to-market y contribución a la rentabilidad
