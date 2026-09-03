# Blue Orbit (ORCA)

> **Agentic AI-Powered Marine Intelligence Platform for Decision Support**  
> *Smart India Hackathon (SIH) 2026 Project*

---

## 🌊 About Blue Orbit / ORCA

**Blue Orbit (ORCA)** is designed to provide explainable marine decision support by analyzing oceanographic, meteorological, and geospatial intelligence. 

The architecture is planned to include specialized components:
- **Ocean Intelligence Agent** (SST, Chlorophyll-a, Ocean dynamics)
- **Weather & Marine Safety Agent** (Wind, waves, alerts, severe conditions)
- **Geospatial & Geofencing Agent** (EEZ, marine protected zones, borders)
- **Routing Agent** (Safe and fuel-efficient marine navigational paths)
- **Orchestration & Synthesizer Layer** (Explainable fishing and safety recommendations)
- **Voice & Multilingual Interaction** (Fisherfolk-friendly communication)

---

## 📍 Current Project Status — Step 1: Full-Stack Foundation

> **Current Milestone: Step 1 (Foundation)**  
> This repository currently contains the initial full-stack project scaffold. No AI agents, LLM orchestration, or scientific calculation pipelines are implemented yet.

In this step, we have established:
- A lightweight **FastAPI** backend with CORS enabled and basic health endpoints (`/` and `/api/health`).
- A clean **React + Vite** frontend with a live connectivity check button.
- Organized folder structure for upcoming data, notebooks, tests, and documentation.

---

## 📁 Repository Structure

```text
blue-orbit/
├── backend/
│   ├── app/
│   │   ├── __init__.py      # App package initializer
│   │   └── main.py          # FastAPI application & endpoints
│   ├── requirements.txt     # Python backend dependencies
│   ├── .env.example         # Template for environment variables
│   └── .venv/               # Python virtual environment (ignored by git)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main UI component with backend check
│   │   ├── App.css          # Component styling
│   │   ├── index.css        # Global CSS variables & layout
│   │   └── main.jsx         # React application entry point
│   ├── index.html           # HTML template
│   ├── package.json         # Node.js dependencies and scripts
│   └── vite.config.js       # Vite build configuration
│
├── data/                    # Data storage placeholders for future steps
│   ├── ocean/               # Satellite & oceanographic data
│   ├── weather/             # Meteorological data
│   └── geospatial/          # Shapefiles, boundaries, marine zones
│
├── notebooks/               # Jupyter notebooks for data exploration
├── tests/                   # Automated unit & integration tests
├── docs/                    # Architecture diagrams & documentation
├── .gitignore               # Ignored files for Python, Node, Vite, env
└── README.md                # Project documentation (this file)
```

---

## 🚀 Getting Started (Manual Setup & Run)

### Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** & **npm**

---

### 1. Backend Setup & Startup

1. Open a terminal in the project root:
   ```bash
   cd blueorbit
   ```

2. Create and activate a Python virtual environment:
   - **Windows (PowerShell):**
     ```powershell
     python -m venv backend/.venv
     .\backend\.venv\Scripts\Activate.ps1
     ```
   - **macOS / Linux:**
     ```bash
     python3 -m venv backend/.venv
     source backend/.venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```

4. Start the FastAPI development server:
   - **From `backend/` directory:**
     ```bash
     cd backend
     uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
     ```

5. Verify backend in your browser or terminal:
   - Root endpoint: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
   - Interactive Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### 2. Frontend Setup & Startup

1. Open a second terminal and navigate to `frontend/`:
   ```bash
   cd blueorbit/frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

4. Open [http://localhost:5173](http://localhost:5173) in your browser.
5. Click **"Check Backend"** to test frontend-to-backend communication. You should see `Backend Status: Healthy`.

---

## 🛠️ Next Steps

- **Step 2**: Ingest and structure mock/real oceanographic (SST, Chlorophyll) and weather data.
- **Step 3**: Introduce baseline algorithmic analysis (Potential Fishing Zones & Safety indicators).
- **Step 4**: Build specialized Agentic workflows (ORCA Agent layer).
