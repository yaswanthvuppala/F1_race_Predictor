# 🏎️ F1 Race Predictor

An advanced Formula 1 race prediction platform using **XGBoost machine learning models** (`XGBRanker`) to forecast race outcomes. 

### 🚀 Live Deployment
The platform is deployed live and fully operational on Render:
**🔗 Deployed Link:** [https://f1-race-predictor-k4p7.onrender.com/](https://f1-race-predictor-k4p7.onrender.com/)

---

## 📂 Repository Structure

- `app.py` - Flask web application serving predictions and custom scenario simulations.
- `train_and_save.py` - Local pre-training script generating optimized lightweight model files.
- `model_before.json` & `model_after.json` - Serialized machine learning models for instant startup.
- `F1_racePredictor_beforeQualifiying.py` - Local script training the pre-qualifying model.
- `F1_racepredictor_AfterQyualifiying.py` - Local script training the post-qualifying model.
- `compare_f1_predictors.py` - Runs both models on the test data and outputs graphical comparison assets.
- `create_2026_data.py` - Simulates upcoming 2026 season layouts based on championship standings.
- `f1_2022.csv` to `f1_2026.csv` - Formula 1 race result datasets.

---

## 📊 Machine Learning Model Architecture

The platform uses two separate **XGBRanker** models to cover different parts of the race weekend:

1. **Before-Qualifying Model (`model_before.json`)**:
   - Forecasts outcomes *before* qualifying positions are known.
   - Evaluates long-term driver form, team form, and historical finishing rates.
2. **After-Qualifying Model (`model_after.json`)**:
   - Forecasts outcomes *after* qualifying is completed.
   - Adds crucial starting grid positions and derived historical conversion indicators.
   - Boosted with a balanced `GRID_WEIGHT` of `1.0` to avoid qualifying bias and prioritize race-craft.

### ⚡ Optimized Startup & Deploy Architecture
To ensure stability on the Render free tier (512MB RAM & throttled CPU), we use an **offline-trained, serialized model architecture**:
- Models are trained locally on your system using `train_and_save.py` and saved as JSON.
- The Flask app loads these JSON files **instantaneously (< 1ms)** at boot time with virtually zero RAM/CPU footprint, avoiding Gunicorn worker timeouts and OOM (Out of Memory) crashes on Render.

---

## ⚙️ Setup & Local Development

### 1. Install Dependencies
Ensure you have the required packages installed:
```bash
pip install pandas numpy xgboost scikit-learn flask gunicorn
```

### 2. (Optional) Re-train and Save Models Locally
To re-train the models from scratch on the CSV datasets and serialize them:
```bash
python train_and_save.py
```

### 3. Launch the Web Dashboard
Start the local Flask server:
```bash
python app.py
```
Open your browser and navigate to: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🖥️ Interactive Web Dashboard Features

- **Model Accuracy Explorer:** Visually analyzes the cumulative correct predictions progression (75% for pre-qualifying, 100% for post-qualifying).
- **Race Calendar Explorer:** Selects any completed or upcoming race from the 2026 season to view rankings, historical driver form, and podium layouts.
- **Interactive Live Custom Grid Simulator:** Drag, drop, or manually edit starting grid positions (1-20) for any upcoming race, triggering real-time ML model re-evaluation to simulate what-if scenarios.

---

## 📈 Dataset Split
- **Training Data**: `f1_2022.csv`, `f1_2023.csv`, `f1_2024.csv`, and `f1_2025.csv`.
- **Test Data / Active Season**: `f1_2026.csv`.
- Championship standings are computed dynamically to generate realistic starting grids for upcoming, un-raced events.
