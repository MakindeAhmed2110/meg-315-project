# AD-HTC Biogas Pro

Streamlit application for AD-HTC (Anaerobic Digestion and Hydrothermal Carbonization) biogas kinetics, boiler balance, power cycle, and thermodynamic diagrams. Includes an animated process-flow schematic with calculated values.

## Prerequisites

- Python 3.9 or later
- pip

## Setup

1. Open a terminal in the project folder.

2. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
   On macOS/Linux:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Run the application

From the project folder, with the virtual environment activated:

```bash
streamlit run app.py
```

The app will open in your browser. If it does not, go to the URL shown in the terminal (usually http://localhost:8501).

## Using the app

1. **Step 1 – Initial parameters:** Choose biomass type, mass flow, and temperature. Click **Analyze** to run kinetics.
2. **Step 2 – Results:** View biogas and reactor results.
3. **Step 3 – Boiler details:** Enter boiler water capacity and steam temperature.
4. **Step 4 – Combustion & power cycle:** Set compressor/turbine/generator efficiencies, air mass flow, pressure ratio, and ambient temperature.
5. **Step 5 – Thermodynamic diagrams:** View steam (h–s) and gas (T–s) cycle diagrams.
6. **Step 6 – Schematic:** View the animated AD-HTC fuel-enhanced gas power cycle schematic with your calculated values.

Use the left menu to move between steps and see short result summaries.
