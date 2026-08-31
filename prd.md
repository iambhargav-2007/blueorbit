[product-requirements-document.md](https://github.com/user-attachments/files/31639240/product-requirements-document.md)
# Product Requirement Document (PRD)
## Project: Blue Orbit (ORCA - Marine EcOsystem Reasoning with Collaborative Agents)
### Document Version: 1.0.0
### Date: 2026-08-31

---

## 1. Executive Summary & Problem Definition

### 1.1 Context
The marine ecosystem is a cornerstone of global food security, coastal resilience, maritime commerce, and the blue economy. Every day, global agencies—including ISRO and Copernicus—generate vast volumes of high-resolution satellite Earth Observation (EO) and meteorological data. However, this raw data remains largely inaccessible to key marine stakeholders, especially traditional fishermen, coastal authorities, and maritime operators. The barrier to entry includes massive file sizes, complex file formats (such as NetCDF4), spatial-temporal gaps due to cloud cover, and the technical expertise required to interpret multi-dimensional scientific variables.

### 1.2 The Opportunity
By merging advanced **Agentic AI**, **Geospatial Analytics**, and **Conversational Intelligence**, we can abstract the complexity of satellite oceanography. **Blue Orbit (ORCA)** is an intelligent, multi-agent conversational platform that enables users to interact naturally with marine datasets. It interprets unstructured multilingual inputs (including voice), decomposes complex workflows, executes parallel spatial-temporal reasoning over heterogeneous data streams, and delivers explainable, localized, and actionable recommendations.

### 1.3 Core Value Proposition
*   **For Fishermen:** Safe, localized navigation paths and precise, scientifically calculated Potential Fishing Zones (PFZ) delivered via multilingual text and voice briefs (ASR & TTS).
*   **For Coast Guards & Maritime Authorities:** Immediate, automated geofencing warnings preventing international boundary crossings and marine reserve poaching, alongside predictive weather risk matrices.
*   **For Researchers & Operators:** A unified conversational playground to explore spatial-temporal trends, explaining *why* local productivity is shifting.

---

## 2. Multi-Agent Architecture & System Topology

To minimize network latencies, prevent infinite LLM reasoning loops, and guarantee high system reliability during a live demo, Blue Orbit is built on a **Stateful, Non-Sequential Directed Acyclic Graph (DAG)** orchestration model. 

Instead of allowing agents to chat freely and unguided, an **Orchestrator Node** acts as a compiler, parsing the user's intent, populating a shared memory state, and triggering specialized computational agents in parallel.

```
                  ┌────────────────────────────────────────┐
                  │          USER INPUT (Voice/Text)       │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Localization Agent (ASR)         │
                  │  Detects language & normalizes to EN   │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │           Orchestrator Agent           │
                  │  Extracts parameters & triggers DAG    │
                  └───────────────────┬────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│  Ocean Science Agent  │ │ Weather Safety Agent  │ │   Geofencing Agent    │
├───────────────────────┤ ├───────────────────────┤ ├───────────────────────┤
│ • KD-Tree spatial     │ │ • Pulls live Open-    │ │ • Spatial polygon     │
│   nearest lookup      │ │   Meteo variables     │ │   overlaps via        │
│ • Species-specific    │ │ • Computes wind, wave │ │   Shapely             │
│   HSI index models    │ │   & storm safety      │ │ • Computes distance   │
│ • SST thermal fronts  │ │   index metrics       │ │   to IMBL boundary    │
└───────────┬───────────┘ └───────────┬───────────┘ └───────────┬───────────┘
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Routing & Navigation Agent       │
                  │ Calculates safe paths using A* grid    │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │      Synthesizer & XAI Agent           │
                  │ Fuses reports & generates explanation   │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Localization Agent (TTS)         │
                  │  Generates regional audio brief (.mp3) │
                  └───────────────────┬────────────────────┘
                                      ▼
                  ┌────────────────────────────────────────┐
                  │        Interactive React Map UI        │
                  └────────────────────────────────────────┘
```

### 2.1 The Shared Graph State (`AgentState`)
Every node in the DAG reads from and writes to a central, schema-validated dictionary:

```python
from typing import TypedDict, List, Dict, Optional

class AgentState(TypedDict):
    # User Input Context
    user_query: str
    input_language: str                # e.g., "gu", "mr", "ta", "hi", "en"
    detected_intent: str               # e.g., "PFZ_FINDER", "SAFETY_CHECK", "ROUTE_PLAN"
    
    # Extracted Parameters
    latitude: float
    longitude: float
    target_date: str                   # YYYY-MM-DD
    target_species: str                # e.g., "Tuna", "Sardine", "Mackerel"
    
    # Intermediate Outputs (Agent Reports)
    ocean_report: Optional[Dict]       # {sst, chlorophyll, sst_gradient, hsi_score, is_pfz}
    weather_report: Optional[Dict]     # {wind_speed, wave_height, wave_period, safety_index}
    geofence_report: Optional[Dict]    # {distance_to_imbl, is_violating, active_sanctuary}
    routing_path: Optional[List[Dict]] # List of coordinates: [{"lat": x, "lon": y}]
    
    # Final Outputs
    english_recommendation: str
    translated_recommendation: str
    audio_brief_url: Optional[str]     # Path to generated local .mp3 speech file
```

---

## 3. Comprehensive Technical Stack

| System Layer | Technology Chosen | Justification & Winning Advantage |
| :--- | :--- | :--- |
| **Frontend UI** | React.js (Vite template) | Super-fast compilation, zero-latency state updates, native hot-reloading for testing. |
| **CSS & Components**| Tailwind CSS + Shadcn/ui | Accelerated building of professional dark-theme dashboards, control gauges, sliders, and chats. |
| **Map Rendering** | Leaflet.js (`react-leaflet`) | **100% free, open-source, and keyless**. Supports raster overlay maps, route polylines, and boundary geofences out of the box. |
| **Backend API** | FastAPI (Python 3.12) | Asynchronous native operations (asyncio), automatic OpenAPI/Swagger documentation generation, and high-performance routing. |
| **Memory Database** | Pandas + PyArrow (Parquet) | Loads our 200,000-row spatial database directly into backend RAM in **under 10ms**. Bypasses slow, complex SQL server setups. |
| **Spatial Indexing** | Scikit-learn (`KDTree`) | Microsecond nearest-neighbor matching. Bypasses computationally heavy database queries for coordinate alignment. |
| **Spatial Math** | Shapely & Geopandas | High-speed point-in-polygon calculations for geofencing boundaries without overhead. |
| **Inference Engine** | Groq API (`Llama-3-8B-Instruct`) | The fastest public inference engine (300+ tokens/sec). Delivers conversational, sub-second responses for interactive UI queries. |
| **Speech Pipeline** | `edge-tts` (Python library) | Free, neural-quality text-to-speech engine supporting realistic Indian regional accents natively (Gujarati, Marathi, Tamil, etc.). |

---

## 4. Data Dictionary & In-Memory Spatial Alignment Engine

### 4.1 Ingested Spatial-Temporal Data Layers

#### 1. Satellite Sea Surface Temperature (SST)
*   **Source:** Copernicus Marine Service (CMEMS) - `SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001`
*   **Attributes Ingested:** `time`, `lat`, `lon`, `analysed_sst` (converted to Celsius: $\text{Kelvin} - 273.15$)
*   **Resolution:** $0.05^\circ \times 0.05^\circ$ (~5 km grid)

#### 2. Satellite Chlorophyll-a
*   **Source:** Copernicus Marine Service (CMEMS) - `OCEANCOLOUR_GLO_BGC_L4_NRT`
*   **Attributes Ingested:** `time`, `lat`, `lon`, `CHL` ($\text{mg/m}^3$)
*   **Resolution:** $0.04^\circ \times 0.04^\circ$

#### 3. Weather & Sea-State Parameters
*   **Source:** Open-Meteo Historical & Live Marine API
*   **Attributes Ingested:** `time`, `wind_speed_10m` (converted to knots), `wind_direction_10m`, `wave_height` (meters), `wave_direction`, `wave_period` (seconds)

#### 4. Geospatial Boundaries (GIS Layers)
*   **Source:** MarineRegions.org (EEZ & International Maritime Boundary Lines) & Protected Planet (Marine Protected Areas)
*   **Format:** GeoJSON (`india_imbl.geojson` & `india_sanctuaries.geojson`)

---

### 4.2 The Spatial Alignment Engine & KD-Tree Lookup
Because satellite instruments operate on slightly offset coordinate grids, merging files via exact float joins causes empty results. We coarsen coordinates to a uniform grid and build a **KD-Tree index in memory** upon server startup to perform microsecond nearest-neighbor matching.

```python
import pandas as pd
import numpy as np
from sklearn.neighbors import KDTree

class MarineDatabaseManager:
    def __init__(self, sst_csv_path, chlor_csv_path, weather_csv_path):
        # 1. Load CSVs into RAM
        df_sst = pd.read_csv(sst_csv_path)
        df_chl = pd.read_csv(chlor_csv_path)
        df_wth = pd.read_csv(weather_csv_path)
        
        # 2. Coordinate Rounding & Consolidation
        df_sst['lat_round'] = np.round(df_sst['lat'] / 0.05) * 0.05
        df_sst['lon_round'] = np.round(df_sst['lon'] / 0.05) * 0.05
        
        df_chl['lat_round'] = np.round(df_chl['lat'] / 0.05) * 0.05
        df_chl['lon_round'] = np.round(df_chl['lon'] / 0.05) * 0.05
        
        # 3. Join Datasets on Rounded Space & Time Grid
        self.df_merged = pd.merge(df_sst, df_chl, on=['time', 'lat_round', 'lon_round'], how='inner')
        self.df_merged = pd.merge(self.df_merged, df_wth, on=['time', 'lat_round', 'lon_round'], how='inner')
        
        # 4. Extract Coordinate Arrays & Fit Spatial Index
        self.coords_array = self.df_merged[['lat_round', 'lon_round']].drop_duplicates().values
        self.spatial_tree = KDTree(self.coords_array)
        
    def find_nearest_index(self, input_lat: float, input_lon: float) -> tuple:
        """Finds closest grid coordinates in less than 2 milliseconds."""
        dist, ind = self.spatial_tree.query([[input_lat, input_lon]], k=1)
        nearest_coord = self.coords_array[ind[0][0]]
        return nearest_coord[0], nearest_coord[1]
```

---

## 5. Core Mathematical & Algorithmic Models

To make Blue Orbit scientifically robust, your agents execute actual physical and mathematical formulas:

### 5.1 SST Spatial Gradient Model (Thermal Front Detection)
Large schools of fish congregate at cold-to-warm boundary boundaries (fronts) due to upwelling nutrients. We compute a localized spatial gradient proxy ($|\nabla SST|$) at each coordinate $(x, y)$ by measuring its temperature deviation against the day's regional average:

$$|\nabla SST_{(x,y)}| = \left| SST_{(x,y)} - \overline{SST}_{\text{Regional}} \right|$$

Any grid cell where $|\nabla SST| \ge 0.35^\circ\text{C}$ is tagged as a candidate thermal front.

### 5.2 Species-Specific Habitat Suitability Index (HSI)
Different fish profiles prefer distinct physical conditions. We model the Tuna and Sardine suitabilities using mathematical Gaussian envelope functions, combining them through their geometric mean:

$$HSI = \sqrt{SI_{\text{SST}} \times SI_{\text{Chl}}}$$

Where the individual Suitability Indexes ($SI$) are derived from optimal standard deviations:

$$SI_{\text{SST}} = \exp\left( -0.5 \left( \frac{SST - \mu_{\text{SST}}}{\sigma_{\text{SST}}} \right)^2 \right)$$

$$SI_{\text{Chl}} = \exp\left( -0.5 \left( \frac{\log_{10}(Chl) - \log_{10}(\mu_{\text{Chl}})}{\sigma_{\text{Chl}}} \right)^2 \right)$$

#### Configuration Profiles:
*   **Yellowfin Tuna:** Optimal SST ($\mu_{\text{SST}}$) = $27.5^\circ\text{C}$, $\sigma_{\text{SST}} = 1.5^\circ\text{C}$; Optimal Chlorophyll ($\mu_{\text{Chl}}$) = $0.30\text{ mg/m}^3$, $\sigma_{\text{Chl}} = 0.15\text{ mg/m}^3$.
*   **Indian Oil Sardine:** Optimal SST ($\mu_{\text{SST}}$) = $26.0^\circ\text{C}$, $\sigma_{\text{SST}} = 2.0^\circ\text{C}$; Optimal Chlorophyll ($\mu_{\text{Chl}}$) = $0.85\text{ mg/m}^3$, $\sigma_{\text{Chl}} = 0.35\text{ mg/m}^3$.

A grid point is officially designated as a **Potential Fishing Zone (PFZ)** if:
$$(HSI \ge 0.72) \land (|\nabla SST| \ge 0.25^\circ\text{C})$$

---

### 5.3 Sea-Venture Safety Index (0–100 Score)
We calculate a real-time risk index to protect fishermen. The index starts at 100 and scales down linearly as wind, gusts, and wave heights rise:

$$\text{Safety Score} = 100 - \left( 1.5 \times W_{\text{speed}} \right) - \left( 18.0 \times H_{\text{wave}} \right) - \left( 5.0 \times \text{Gusts} \right)$$

#### Alert Status Thresholds:
*   **Score 75 - 100:** **Safe (Green)** - Conditions clear.
*   **Score 45 - 74:** **Caution (Yellow)** - Moderate swell. Small vessels are advised to stay near the coast.
*   **Score 0 - 44:** **Dangerous (Red)** - High waves or storm systems. Complete ban on sea ventures.

---

### 5.4 Safe Route Optimization Pathfinder ($A^*$)
To calculate fuel-efficient, safe navigation paths to a target fishing zone, the routing engine converts our marine grid into a cost map. The cost of traversing any grid coordinate $C(x, y)$ is calculated as:

$$\text{Cost}(x,y) = \text{Distance}_{\text{Euclidean}} + \text{Hazard\_Multiplier}(x,y) + \text{Geofence\_Penalty}(x,y)$$

Where:
*   $\text{Hazard\_Multiplier}$ increases to infinity if wave heights exceed $2.2$ meters or wind speeds exceed $22$ knots.
*   $\text{Geofence\_Penalty}$ is set to infinity if the cell intersects with marine sanctuary boundaries or crosses the IMBL border.

The **$A^*$ algorithm** then identifies the path of least resistance from the harbor point to the PFZ destination.

---

## 6. Detailed Agent Blueprints

### 6.1 Orchestrator Agent (The Compiler Node)
*   **Core Role:** Evaluates user inputs, translates them into structured targets, and determines execution nodes.
*   **Input Data:** Freeform user voice or text.
*   **Implementation Strategy:** Uses Pydantic schemas with an LLM function-calling prompt to force JSON extraction:

```json
{
  "intent": "PFZ_SEARCH_WITH_WEATHER_SAFETY",
  "latitude": 18.97,
  "longitude": 72.82,
  "target_date": "2026-08-31",
  "target_species": "Tuna",
  "input_language": "gu"
}
```

---

### 6.2 Ocean Science Agent (Scientific Reasoning)
*   **Core Role:** Evaluates the spatial biological viability of coordinates and conducts temporal trend diagnostics.
*   **Input Data:** Merged SST and Chlorophyll arrays.
*   **Logic Loops:**
    1.  **Direct Search:** Queries database at target coordinates, computes dynamic fronts, and applies species Suitability Indices.
    2.  **Productivity Trend Analysis:** If asked *why* fish counts are low, it pulls a 7-day rolling window of temperatures preceding the target date. If the temperature rose $>1.8^\circ\text{C}$ within 4 days, it diagnoses a "Local Marine Heatwave" causing plankton dispersion.

---

### 6.3 Weather Safety Agent (Meteorological Risk Guard)
*   **Core Role:** Performs weather forecasting calculations and triggers storm alerts.
*   **Input Data:** Real-time and historical Open-Meteo feeds.
*   **Logic Loops:**
    1.  **Safety Score:** Runs the Sea-Venture Safety equation over hourly forecast data.
    2.  **Cyclone Detection:** Tracks barometric pressure trends over the past 24 hours. A rapid rate of change of:
        $$\frac{\Delta \text{Pressure}}{\Delta t} \ge 8\text{ hPa over 12 hours}$$
        immediately triggers an automated storm evacuation alert.

---

### 6.4 Geofencing Agent (Legal & Spatial Buffer Check)
*   **Core Role:** Keeps vessels within legal and safe waters.
*   **Input Data:** Vessel GPS location and GeoJSON spatial polygons.
*   **Logic Loops:**
    1.  Loads the coordinates of the **Indo-Pak IMBL** and sanctuary vectors into Shapely shapes.
    2.  Calculates the shortest distance from the boat's location to the nearest border line.
    3.  If distance $\le 5\text{ km}$, writes a critical geofence violation state, triggering warning banners and push notifications on the client map.

---

### 6.5 Routing & Navigation Agent
*   **Core Role:** Plots optimal routes avoiding dangerous weather cells and legal buffers.
*   **Input Data:** Starting point, destination PFZ, and cost grid.
*   **Logic Loops:** Executes the $A^*$ cost pathfinder and outputs a structured sequence of geographic points to the Leaflet map overlay.

---

### 6.6 Synthesizer & Explainable AI (XAI) Agent
*   **Core Role:** Fuses data-driven agent reports into an easily digestible summary, explaining *why* coordinates are recommended.
*   **Input Data:** Output state from the Ocean, Weather, and Geofencing nodes.
*   **Logic Loop:** Leverages plain text templates containing raw scientific indices to justify suggestions:
    *   *Sample Response:* `"Mumbai Coast is tagged Safe (Safety Score: 88). A prime Sardine PFZ is located 12 km Southwest (HSI: 0.82) due to an active thermal gradient of 0.42°C. The route is clear of marine sanctuaries."`

---

### 6.7 Localization Agent (Multilingual Input/Output Bridge)
*   **Core Role:** Handles translation, voice transcription, and neural regional voice broadcasting.
*   **Input Data:** User vocal audio or regional text.
*   **Logic Loop:** Uses ASR to transcribe to English, routes output English briefs through translation layers, and triggers `edge-tts` to stream native audio files to the frontend UI.

---

## 7. Dual Execution Modes: Live vs. Cache Sandbox

To provide both absolute presentation safety and live-production capability, Blue Orbit features a backend toggle switch: `LIVE_MODE = True/False`.

```
                    ┌──────────────────────────────┐
                    │      Backend Boot Lifecycle  │
                    └──────────────┬───────────────┘
                                   ▼
                       /────────────────────────\
                      <      Is LIVE_MODE=True?  >
                       \────────────────────────/
                                   │
                     Yes ┌─────────┴─────────┐ No
                         ▼                   ▼
            ┌────────────────────────┐  ┌────────────────────────┐
            │ Calculate Target Date: │  │  Load October 2025    │
            │   (Today - 48 hours)   │  │  30-Day Cache Parquet  │
            └────────────┬───────────┘  │  Database directly    │
                         ▼              │  into Server RAM       │
            ┌────────────────────────┐  └────────────┬───────────┘
            │  Programmatically      │               │
            │  Subset & Download     │               │
            │  Copernicus daily NC   │               │
            └────────────┬───────────┘               │
                         ▼                           ▼
            ┌────────────────────────┐  ┌────────────────────────┐
            │ Flatten, Align, and    │  │  Ready for Instant     │
            │ Build KD-Tree over NRT │  │  Spatial-Temporal      │
            │  Live Ocean variables  │  │  Reasoning Queries     │
            └────────────┬───────────┘  └────────────────────────┘
                         ▼
            ┌────────────────────────┐
            │  Ready for Instant     │
            │  Spatial-Temporal      │
            │  Reasoning Queries     │
            └────────────────────────┘
```

### 7.1 Cache Sandbox Mode (`LIVE_MODE = False`)
*   **Operation:** Ingests a high-resolution 30-day block of October 2025 satellite data locally.
*   **Advantage:** **100% offline-capable, lightning-fast (<50ms responses), and immune to API server downtimes.** Guaranteed to perform flawlessly during stressful evaluation windows.

### 7.2 Live Mode (`LIVE_MODE = True`)
*   **Operation:** Upon startup, calculates $T-2$ days (to allow Copernicus Level 4 processing pipelines to finalize) and downloads the daily cropped NetCDF file programmatically.
*   **Advantage:** Proves the system is fully production-ready and active, actively pulling actual marine data from 48 hours ago.

### 7.3 Future Cloud Scale Plan (ETL Serverless Architecture)
To transition Blue Orbit from a prototype to a national public utility:
1.  **Serverless Ingestion Pipeline:** Run an AWS Lambda function triggered via a daily cron job at 02:00 AM.
2.  **Automated ETL Processing:** The function downloads daily Sentinel/Oceansat NetCDF files from Copernicus/Bhuvan APIs, crops the Indian Exclusive Economic Zone bounding boxes, rounds them to our uniform grid, and appends them to a cloud-hosted database.
3.  **TimescaleDB Database:** Replace the local Parquet files with **TimescaleDB** (PostgreSQL with PostGIS extensions) to support high-concurrent geo-spatial queries from hundreds of thousands of active fishing vessels.

---

## 8. Frontend UI/UX Specifications

The visual interface is built as a split-screen dashboard to present rich, data-driven outputs seamlessly:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  BLUE ORBIT (ORCA) ── Navigational Intelligence Control Panel        [ LIVE MODE: ON ] │
├─────────────────────────────────────────┬──────────────────────────────────────────────┤
│  CHAT & RECOMMENDATION PANEL             │  GEOSPATIAL VISUALIZATION (Leaflet Map)      │
│                                         │                                              │
│  ┌───────────────────────────────────┐  │  ┌────────────────────────────────────────┐  │
│  │ User: "Nearest Tuna PFZ today?"   │  │  │  ▲ [Disputed Border] (Red Line)        │  │
│  └───────────────────────────────────┘  │  │  │                                        │  │
│  ┌───────────────────────────────────┐  │  │  │     (A* Safe Route Line)               │  │
│  │ Agent: "I have calculated a Tuna  │  │  │     /                                  │  │
│  │ PFZ 15 km Southwest of Mumbai.    │  │  │    /                                   │  │
│  │ Safety score is 85. Play Audio..."│  │  │  [Boat]                                │  │
│  └───────────────────────────────────┘  │  │  (SST / CHL Color Gradients Map)       │  │
│                                         │  │                                        │  │
│  ┌───────────────────────────────────┐  │  └────────────────────────────────────────┘  │
│  │ ◯ Mic Button (Voice Input)        │  ├──────────────────────────────────────────────┤
│  └───────────────────────────────────┘  │  VESSEL GPS TELEMETRY SIMULATOR              │
│                                         │  Drag to simulate boat movement:             │
│  GAUGES:                                │  Lat: [───|──────────] 18.97                 │
│  Safety Index: [████████░░] 80%         │  Lon: [──────|───────] 72.82                 │
│  HSI Score:    [█████████░] 90%         │                                              │
└─────────────────────────────────────────┴──────────────────────────────────────────────┘
```

### 8.1 Key Interactive UI Elements
1.  **Left Panel - Conversational Chat Interface:**
    *   A clean, modern chat feed with typing indicators showing agent collaboration logs.
    *   A prominent **"Mic"** button with a live waveform visualizer allowing fishermen to record voice queries.
    *   An HTML5 **audio player widget** that automatically plays regional translation briefs (.mp3) generated on-the-fly.
    *   **Interactive Metric Gauges:** Displays the current Sea-Venture Safety Index (color-coded: green/yellow/red) and the calculated HSI score.
2.  **Right Panel - Leaflet.js Interactive Map:**
    *   **Raster Layer Overlays:** Renders color-interpolated heatmaps representing Sea Surface Temperature and Chlorophyll concentration grids.
    *   **Polyline Paths:** Draws the safe, optimized navigation corridor generated by the $A^*$ routing agent in bright green.
    *   **Boundary Polygons:** Highlights restricted marine sanctuaries in semi-transparent red polygons and draws a thick dashed red line representing the International Maritime Boundary Line (IMBL).
3.  **Vessel GPS Telemetry Slider (The Judges' Favorite):**
    *   A custom interactive control allowing users to manually drag sliders to adjust the boat's latitude and longitude.
    *   *Demo Integration:* Dragging the boat closer than 5 km to the Pakistan border instantly flashes a red warning alert on the screen and triggers a loud voice siren, proving that the **Geofencing Agent** operates in true real-time.

---

## 9. End-to-End Workflow Sequences (User Journeys)

### 9.1 Scenario 1: Natural Language Fishing Query
**User input (Gujarati Voice):** "આજે ટ્યુના પકડવા માટે સૌથી નજીકનું સ્થળ કયું છે અને શું ત્યાં જવું સલામત છે?" *(Where is the nearest place to catch Tuna today, and is it safe to go there?)*

1.  **Localization Agent (Input):** Transcribes voice input and translates it to English. Sets `input_language = "gu"`.
2.  **Orchestrator Agent:** Runs LLM parameter extraction. Sets:
    *   `latitude = 18.97`, `longitude = 72.82` (extracted from browser mock GPS).
    *   `target_species = "Tuna"`.
    *   `target_date = "2026-08-31"`.
3.  **Ocean Science Agent (Parallel Execution):** Coordinates with the `KDTree` spatial database. Calculates local SSTs and Chlorophyll-a values. Runs the Gaussian math model for Tuna and isolates the nearest grid cell where `is_pfz == True` (e.g., at $19.12^\circ\text{N}, 71.55^\circ\text{E}$ with an $HSI = 0.84$). Writes this to `ocean_report`.
4.  **Weather Safety Agent (Parallel Execution):** Hits the Open-Meteo Live API for tomorrow's forecast at the target PFZ coordinate. Resolves wind at 11 knots and waves at 0.9 meters. Computes a safety score of $87.2$ (tagged as Safe/Green). Writes to `weather_report`.
5.  **Geofencing Agent (Parallel Execution):** Computes distance from vessel path to the IMBL and sanctuary shapes. Distance to Pak border is 224 km, distance to sanctuary is 42 km. Geofence is clear. Writes `is_violating = False` to `geofence_report`.
6.  **Routing Agent:** Takes the safe starting harbor coordinates and calculated PFZ. Constructs a cost grid and calculates an optimized path bypassing high-wave cells. Writes coordinates array to `routing_path`.
7.  **Synthesizer Agent:** Gathers all reports. Fuses information into an evidence-backed statement:
    *   *Text:* `"I found a prime Tuna fishing zone 34 km Northwest of your position. The area is highly suitable (HSI: 0.84) with clear thermal boundaries. Weather is perfectly safe (Wave height: 0.9m, wind: 11 knots). No boundary hazards detected."`
8.  **Localization Agent (Output):** Translates the English text back to clean Gujarati and runs `edge-tts` to generate a natural voice file (`response_321.mp3`).
9.  **Frontend Interface:** Receives the REST response. Draws the green route line on the Leaflet map, highlights the target PFZ circle, updates the safety gauges, and plays the Gujarati audio brief automatically.

---

## 10. Development Milestones & Team Allocation (36 Hours)

To execute this plan smoothly, your team of 6 must follow this structured timeline:

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ 36-HOUR HACKATHON MILESTONE TIMELINE                                           │
├─────────────────────────────────────────┬──────────────────────────────────────┤
│ M1 & M3: DAG Orchestrator & API Config  │ ██████████████░░░░░░░░░░░░░░░░░  12h │
│ M2: Database & KD-Tree Lookup Engine    │ ████████░░░░░░░░░░░░░░░░░░░░░░░  06h │
│ M2 & M3: Ocean HSI & Weather Core Tools │ ░░░░░░████████████░░░░░░░░░░░░░  18h │
│ M5: Localization & edge-tts Integration │ ░░░░░░░░░░░░██████████░░░░░░░░░  24h │
│ M4: React Leaflet map & UI gauges       │ ░░░░░░░░░░░░████████████████░░  30h │
│ Whole Team: System Integration & Pitch   │ ░░░░░░░░░░░░░░░░░░░░░░░░██████  36h │
└─────────────────────────────────────────┴──────────────────────────────────────┘
```

*   **Member 1 (Agent Architect):** Owns agent logic loops, orchestrator JSON prompts, and Pydantic validation boundaries.
*   **Member 2 (Data Engineer):** Implements the in-memory coordinate rounding joins, build the KD-Tree indexing system, and codes the scientific HSI Gaussian profiles and gradient calculations.
*   **Member 3 (Backend Developer):** Builds the FastAPI framework endpoints, connects the live Open-Meteo web-scraping routers, and codes the $A^*$ safe-routing script.
*   **Member 4 (Frontend Developer):** Designs the responsive React/Vite dashboard, programs the Leaflet maps, customizes layer overlays, and binds interactive sliders for telemetry simulation.
*   **Member 5 (Localization Specialist):** Configures translation pipelines, implements ASR voice handlers, and sets up the asynchronous `edge-tts` audio rendering script.
*   **Member 6 (Product Specialist & Presenter):** Designs vector layouts (PPTX slides), designs clear UI mockups, compiles data presentation guides, and conducts validation testing of edge cases (such as storm anomalies and border crossing coordinates).

---

## 11. Success Metrics & Validation Guidelines

Before presenting your work to the evaluators, your team must verify the following:

1.  **Response Time Latency:** In Cached Sandbox Mode, the conversational response (including multi-agent coordination) must resolve in **under 1.5 seconds**.
2.  **Accuracy Check:** Query a coordinate next to the Pakistan boundary line (e.g., $23.4^\circ\text{N}, 68.1^\circ\text{E}$). The frontend must immediately display a red flashing geofence alert, and the synthesizer must issue an explicit border warning.
3.  **Physical Validity:** Ensure that when wind speeds exceed 25 knots or wave heights exceed 2.5 meters in the API, the safety gauge changes to deep red, and the route pathfinder blocks any routes traversing that area.
4.  **Localization Clarity:** The voice brief generated in regional Indian languages must be clearly audible, using realistic neural accents without standard robotic distortions.
