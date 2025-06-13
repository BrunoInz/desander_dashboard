# Desander Data Analysis Tool / Herramienta de Análisis de Datos de Desander

## 📝 Table of Contents  / Tabla de Contenidos
1. [Overview](#overview)
2. [Features](#features) / [Características](#caracteristicas)
3. [Requirements](#requirements) / [Requisitos](#requisitos)
4. [Installation](#installation) / [Instalación](#instalacion)
5. [Usage](#usage) / [Uso](#uso)
6. [Data Format](#data-format) / [Formato-de-datos](#formato-de-datos)
7. [Screenshots](#screenshots) / [Capturas-de-pantalla](#capturas-de-pantalla)
8. [License](#license) / [Licencia](#licencia)

---

## <a name="overview">🌎 Overview</a>
A Streamlit-based dashboard to explore and analyse drain-weight measurements from desander equipment.  
It helps operators visualise dumping patterns, detect possible choke manifold changes, and export filtered data—without writing a single line of code.

---

## <a name="features">✨ Features</a>
* Interactive filters for serial number, well number, and date range.  
* Adjustable grouping slider (1–24 h) with custom start hour.  
* Automatic trend lines (moving averages & exponential).  
* **Choke-manifold change detector** with smart logic (low-weight baseline & sudden rise within next three dumps).  
* One-click CSV export of any filtered view.  
* Dark-mode friendly Plotly charts.

## <a name="caracteristicas">✨ Características</a>
* Filtros interactivos por número de serie, pozo y rango de fechas.  
* Agrupación temporal configurable (1–24 h) con hora de inicio personalizada.  
* Líneas de tendencia automáticas (promedios móviles y exponencial).  
* **Detector de cambio del choke manifold** (válvula) con lógica avanzada (basado en bajo peso y aumento repentino en las 3 siguientes mediciones).  
* Exportación a CSV con un clic.  
* Gráficas Plotly compatibles con modo oscuro.

---

## <a name="requirements">💾 Requirements</a>
* Python 3.9+  
* Packages (see `requirements.txt`): `streamlit`, `pandas`, `numpy`, `plotly`

## <a name="requisitos">💾 Requisitos</a>
* Python 3.9+  
* Paquetes (ver `requirements.txt`): `streamlit`, `pandas`, `numpy`, `plotly`

---

## <a name="installation">⚙️ Installation</a>
```bash
# 1. Clone the repo
$ git clone https://github.com/your-org/desander-analysis.git
$ cd desander-analysis

# 2. Create & activate virtual environment (optional but recommended)
$ python -m venv .venv
$ source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
$ pip install -r requirements.txt
```

## <a name="instalacion">⚙️ Instalación</a>
```bash
# 1. Clona el repositorio
$ git clone https://github.com/tu-org/desander-analysis.git
$ cd desander-analysis

# 2. (Opcional) Crear y activar entorno virtual
$ python -m venv .venv
$ source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Instalar dependencias
$ pip install -r requirements.txt
```

---

## <a name="usage">🚀 Usage</a>
```bash
# Launch the dashboard / Ejecutar la aplicación
$ streamlit run other_app.py
```
1. Choose a data source: sample data, upload CSVs, or load from directory.  
2. Apply filters & select grouping interval.  
3. Inspect charts, stats, and detected valve changes.  
4. Download your filtered data as CSV.

## <a name="uso">🚀 Uso</a>
1. Selecciona el origen de datos: muestra, subir CSVs o directorio de archivos.  
2. Ajusta filtros y el intervalo de agrupación.  
3. Revisa gráficas, estadísticas y cambios de válvula detectados.  
4. Descarga los datos filtrados en CSV.

---

## <a name="data-format">📄 Data Format</a>
Each CSV row should contain:

| Column | Type | Description |
|--------|------|-------------|
| `time` | datetime (ISO) | Timestamp of measurement (with timezone) |
| `serial_number` | int | Desander unit identifier |
| `well_number` | int | Well number being processed |
| `dump_number` | int | Sequential dump number |
| `drain_weight` | float | Weight drained (kg) |
| `created_at` | datetime | Record creation timestamp (optional) |
| `updated_at` | datetime | Record update timestamp (optional) |

## <a name="formato-de-datos">📄 Formato de datos</a>
Cada fila CSV debe incluir:

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `time` | datetime (ISO) | Marca de tiempo (con zona horaria) |
| `serial_number` | int | Identificador del desander |
| `well_number` | int | Número de pozo |
| `dump_number` | int | Número secuencial de descarga |
| `drain_weight` | float | Peso drenado (kg) |
| `created_at` | datetime | Fecha de creación (opcional) |
| `updated_at` | datetime | Fecha de actualización (opcional) |

---

## <a name="screenshots">🖼️ Screenshots</a> / <a name="capturas-de-pantalla">🖼️ Capturas de pantalla</a>
Add images here to showcase the dashboard.

---
