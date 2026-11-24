"""
Módulo I — Estimación de la curva par en dólares con Nelson-Siegel (NS) sobre tasas CMT.

Entradas (data/raw, descargadas el 2026-11-11):
  - fred_cmt_monthly_eom_2026-11-11.csv : último dato hábil de cada mes, oct-2016 a sep-2026,
    series FRED DGS1MO, DGS3MO, DGS6MO, DGS1, DGS2, DGS3, DGS5, DGS7, DGS10, DGS20, DGS30.
  - fed_svenpy_selected_2026-11-11.csv   : tasas par Svensson (SVENPY01..30) de la Fed
    (feds200628.csv) al último día hábil de dic-2023, dic-2024, dic-2025 y sep-2026.

Salidas:
  - data/processed/cmt_long.csv, ns_params_tau1.csv, ns_params_opt.csv, ns_tau_grid.csv
  - output/figs/q3_*.png, q5_*.png, q6_*.png, q7_*.png
  - output/tables/q4_q5_resumen.csv, q7_diferencias.csv

Uso: python src/module1_curves.py   (desde la raíz del proyecto)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC = ROOT / "data/raw", ROOT / "data/processed"
FIG, TAB = ROOT / "output/figs", ROOT / "output/tables"
for p in (PROC, FIG, TAB):
    p.mkdir(parents=True, exist_ok=True)

# --- Estilo de gráficos (paleta categórica fija, líneas finas, grilla recesiva) ---
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "font.size": 9, "axes.titlesize": 10,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.6,
    "legend.frameon": False,
})

# ============================================================================
# Q2 — Datos CMT: tabla fecha × madurez
# ============================================================================
SERIES = {  # código FRED -> madurez en años
    "DGS1MO": 1 / 12, "DGS3MO": 3 / 12, "DGS6MO": 6 / 12, "DGS1": 1, "DGS2": 2, "DGS3": 3,
    "DGS5": 5, "DGS7": 7, "DGS10": 10, "DGS20": 20, "DGS30": 30,
}
cmt = pd.read_csv(RAW / "fred_cmt_monthly_eom_2026-11-11.csv", parse_dates=["date"]).set_index("date")
cmt = cmt[list(SERIES)]
assert cmt.shape == (120, 11) and cmt.notna().all().all()
M = np.array(list(SERIES.values()))  # vector de madureces (años)
cmt.stack().rename("yield").reset_index().rename(columns={"level_1": "serie"}).to_csv(PROC / "cmt_long.csv", index=False)

# ============================================================================
# Q3 — Corto (3M), mediano (2A) y largo plazo (10A)
# ============================================================================
fig, ax = plt.subplots(figsize=(7.2, 3.8))
for col, lab, c in [("DGS3MO", "Corto plazo: 3 meses", C1), ("DGS2", "Mediano plazo: 2 años", C2),
                    ("DGS10", "Largo plazo: 10 años", C3)]:
    ax.plot(cmt.index, cmt[col], color=c, label=lab)
ax.set_ylabel("Tasa CMT (% anual)")
ax.set_title("Tasas CMT del Tesoro de EE.UU., último día hábil de cada mes (oct-2016 a sep-2026)", loc="left")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.text(0.01, 0.005, "Fuente: FRED (Federal Reserve Bank of St. Louis), series DGS3MO, DGS2 y DGS10; descarga 11-nov-2026.",
         fontsize=7, color=INK2)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "q3_cmt_corto_mediano_largo.png")
plt.close(fig)

# ============================================================================
# Q4 — Nelson-Siegel con tau fijo: MCO mes a mes
#   y(m) = b0 + b1 * L1(m) + b2 * L2(m)
#   L1(m) = (1 - e^{-m/tau}) / (m/tau)          (carga de pendiente)
#   L2(m) = L1(m) - e^{-m/tau}                  (carga de curvatura)
# ============================================================================
def ns_loadings(m, tau):
    x = m / tau
    L1 = (1 - np.exp(-x)) / x
    L2 = L1 - np.exp(-x)
    return np.column_stack([np.ones_like(m), L1, L2])


def ns_curve(m, beta, tau):
    return ns_loadings(np.atleast_1d(np.asarray(m, float)), tau) @ beta


def fit_ns(Y, tau):
    """Y: matriz T×K de tasas (%). Devuelve betas (T×3), SCR por mes (T) y SCR total."""
    X = ns_loadings(M, tau)
    B, *_ = np.linalg.lstsq(X, Y.T, rcond=None)  # 3×T, una regresión MCO por columna (mes)
    resid = Y.T - X @ B
    scr_t = (resid ** 2).sum(axis=0)
    return B.T, scr_t, scr_t.sum()


Y = cmt.values
N_OBS = Y.size
b_tau1, scr_tau1, SCR1 = fit_ns(Y, 1.0)
params1 = pd.DataFrame(b_tau1, index=cmt.index, columns=["beta0", "beta1", "beta2"]).assign(SCR=scr_tau1)
params1.to_csv(PROC / "ns_params_tau1.csv")

# ============================================================================
# Q5 — Búsqueda de tau óptimo (grilla + refinamiento local)
# ============================================================================
grid = np.round(np.arange(0.05, 10.0001, 0.01), 4)
scr_grid = np.array([fit_ns(Y, t)[2] for t in grid])
pd.DataFrame({"tau": grid, "SCR_total": scr_grid}).to_csv(PROC / "ns_tau_grid.csv", index=False)
i0 = scr_grid.argmin()
ref = minimize_scalar(lambda t: fit_ns(Y, t)[2], bounds=(grid[max(i0 - 1, 0)], grid[min(i0 + 1, len(grid) - 1)]),
                      method="bounded", options={"xatol": 1e-8})
TAU, SCR_OPT = float(ref.x), float(ref.fun)
b_opt, scr_opt_t, _ = fit_ns(Y, TAU)
params = pd.DataFrame(b_opt, index=cmt.index, columns=["beta0", "beta1", "beta2"]).assign(SCR=scr_opt_t, tau=TAU)
params.to_csv(PROC / "ns_params_opt.csv")

resumen = pd.DataFrame({
    "Especificación": ["τ = 1 año (validación, Q4)", "τ óptimo (Q5)"],
    "τ (años)": [1.0, TAU],
    "SCR total (pp²)": [SCR1, SCR_OPT],
    "N observaciones": [N_OBS, N_OBS],
    "N regresiones (meses)": [len(cmt), len(cmt)],
    "RMSE (pb)": [100 * np.sqrt(SCR1 / N_OBS), 100 * np.sqrt(SCR_OPT / N_OBS)],
})
resumen.to_csv(TAB / "q4_q5_resumen.csv", index=False)

fig, ax = plt.subplots(figsize=(6.4, 3.2))
ax.plot(grid, scr_grid, color=C1)
ax.axvline(TAU, color=INK2, lw=0.8, ls="--")
ax.annotate(f"τ* = {TAU:.3f} años\nSCR = {SCR_OPT:.2f} pp²", xy=(TAU, SCR_OPT), xytext=(TAU + 0.8, SCR_OPT + 0.25 * (scr_grid.max() - SCR_OPT) / 4),
            fontsize=8, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
ax.set_xlabel("τ (años)")
ax.set_ylabel("Suma total de SCR (pp²)")
ax.set_yscale("log")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
ax.yaxis.set_minor_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}" if v in (15, 20, 30, 50) else ""))
ax.set_title("SCR total de las 120 regresiones mensuales según τ", loc="left")
fig.tight_layout()
fig.savefig(FIG / "q5_scr_vs_tau.png")
plt.close(fig)

# ============================================================================
# Q6 — Evolución de beta0 (nivel), beta1 (pendiente) y beta2 (curvatura)
# ============================================================================
fig, axs = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
ax = axs[0]
ax.plot(params.index, params.beta0, color=C1, label="β₀ (nivel)")
ax.plot(params.index, params.beta1, color=C2, label="β₁ (pendiente)")
ax.plot(params.index, params.beta2, color=C3, label="β₂ (curvatura)")
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylabel("Puntos porcentuales")
ax.set_title(f"Parámetros Nelson-Siegel mensuales (τ = {TAU:.3f} años)", loc="left")
ax.legend(loc="upper left", ncol=3)
ax = axs[1]  # validación: factores vs. contrapartes empíricas
ax.plot(params.index, params.beta0 + params.beta1, color=C1, label="β₀+β₁ (tasa instantánea implícita)")
ax.plot(cmt.index, cmt.DGS1MO, color=C1, lw=0.9, ls=":", label="CMT 1 mes")
ax.plot(params.index, -params.beta1, color=C2, label="−β₁ (pendiente implícita)")
ax.plot(cmt.index, cmt.DGS10 - cmt.DGS3MO, color=C2, lw=0.9, ls=":", label="CMT 10A − 3M")
ax.axhline(0, color=INK2, lw=0.6)
ax.set_ylabel("Puntos porcentuales")
ax.set_title("Validación: factores vs. proxies observadas", loc="left")
ax.legend(loc="lower left", ncol=2, fontsize=7.5)
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig(FIG / "q6_parametros_ns.png")
plt.close(fig)

# ============================================================================
# Q7 — Comparación con curvas par Svensson (SVENPY) de la Fed
# ============================================================================
sv = pd.read_csv(RAW / "fed_svenpy_selected_2026-11-11.csv", parse_dates=["Date"]).set_index("Date")
mm = np.arange(1, 31)
fine = np.linspace(1 / 12, 30, 400)
rows = []
fig, axs = plt.subplots(2, 2, figsize=(7.4, 5.6), sharex=True)
for ax, (d, srow) in zip(axs.ravel(), sv.iterrows()):
    pdate = params.index[params.index.to_period("M") == d.to_period("M")][0]
    beta = params.loc[pdate, ["beta0", "beta1", "beta2"]].values.astype(float)
    ours = ns_curve(mm, beta, TAU)
    ax.plot(fine, ns_curve(fine, beta, TAU), color=C1, label="NS propio (sobre CMT)")
    ax.plot(mm, srow.values, color=C2, label="Fed Svensson (SVENPY)")
    ax.scatter(M, cmt.loc[pdate].values, s=14, color=INK, zorder=3, label="CMT observadas")
    ax.set_title(pdate.strftime("%d-%m-%Y"), loc="left")
    ax.set_ylabel("Tasa par (%)")
    diff = 100 * (ours - srow.values)  # puntos base
    rows.append({"fecha": pdate.date(), "dif_media_pb": diff.mean(), "dif_abs_media_pb": np.abs(diff).mean(),
                 "dif_max_abs_pb": np.abs(diff).max(), "madurez_dif_max": int(mm[np.abs(diff).argmax()]),
                 "dif_1A": diff[0], "dif_2A": diff[1], "dif_5A": diff[4], "dif_10A": diff[9], "dif_20A": diff[19], "dif_30A": diff[29]})
for ax in axs[1]:
    ax.set_xlabel("Madurez (años)")
h, l = axs[0, 0].get_legend_handles_labels()
fig.legend(h, l, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0))
fig.suptitle("Curvas par estimadas vs. Fed (Gürkaynak-Sack-Wright, Svensson)", x=0.01, ha="left", fontsize=10)
fig.tight_layout(rect=(0, 0.05, 1, 1))
fig.savefig(FIG / "q7_ns_vs_svenpy.png")
plt.close(fig)
q7 = pd.DataFrame(rows)
q7.to_csv(TAB / "q7_diferencias.csv", index=False)

# ---- Consola ----
pd.set_option("display.width", 160)
print("Madureces usadas (años):", [round(x, 4) for x in M])
print(resumen.to_string(index=False))
print("\nPrimer mínimo de grilla:", grid[i0], "| refinado:", TAU)
print("\nParámetros (τ*), descriptivos:\n", params[["beta0", "beta1", "beta2", "SCR"]].describe().round(3))
print("\nMeses con mayor SCR:\n", params.SCR.sort_values(ascending=False).head(5).round(3))
print("\nQ7 diferencias (NS − SVENPY, pb):\n", q7.round(1).to_string(index=False))
