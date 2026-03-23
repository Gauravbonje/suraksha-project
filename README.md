# SURAKSHA: Uttar Pradesh Crime Intelligence and Predictive Policing System


---

## Overview

SURAKSHA is a comprehensive data engineering and machine learning framework designed to analyze historical crime patterns and predict future hotspots across Uttar Pradesh, India.

The system leverages over 10 years of official government crime data (2014–2023) to provide a granular, district-level intelligence layer for law enforcement decision-making.

---

## Key Features

* Crime hotspot prediction (2024 forecasts)
* Machine learning-based intelligence layer
* District-level crime insights across 75+ districts
* Crime Intensity Scoring (0–100)
* Signature crime identification
* COVID-era crime trend analysis
* District Law & Order grading system

---

## Project Core Philosophy

SURAKSHA follows a Data First approach focused on transforming unstructured and fragmented government data into high-fidelity intelligence.

The project emphasizes rigorous information gathering, data cleaning, and feature engineering to uncover patterns that are often hidden in raw spreadsheets.

---

## Data Engineering and Information Gathering

### Source Integration

* Automated ingestion of 67 NCRB Excel files (2016–2023)
* Integration of multi-year Kaggle datasets

### Automated Extraction

* Custom Python logic to scan unstructured spreadsheets
* Detection of "State: Uttar Pradesh" headers
* Extraction of structured data across 75+ districts

### Dataset Consolidation

* Master dataset of 7,592 rows
* Coverage of 20 crime categories including IPC, SLL, Crimes against Women, Children, SC/STs, Cybercrime, and Juvenile cases

### Information Extraction

* Computation of Crime Intensity Scores (0–100)
* Identification of Signature Crimes for each district

---

## Machine Learning and Training Pipeline

### Feature Engineering

* Temporal lag features: Lag1, Lag2
* Rolling mean feature: RollMean3
* Captures time-based crime trends and momentum

### Model Training

* Evaluated Linear Regression and Gradient Boosting
* Selected Random Forest Regressor as the final model

### Performance Metrics

* R-squared (R²): 0.83
* Root Mean Square Error (RMSE): 884 cases

### 2024 Hotspot Prediction

* Generated over 1,000 predictions
* Identifies high-risk district and crime-type combinations

---

## Strategic Insights and Analysis

### Regime Analysis

* Comparative study between 2014–2016 and 2017–2023
* Evaluates impact of administrative phases on crime trends

### COVID-19 Impact

* 22% reduction in street crimes
* 20.5% increase in domestic-related offences

### Law and Order Report Cards

* District grading system from A to F
* Based on last 3-year performance trends

---

## Deployment and Usage

### Mode 1: Streamlit Application

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Mode 2: Static Web Dashboard

```bash
python3 -m http.server 8080
```

Open in browser:

http://localhost:8080/index.html

---

## Project Structure

```
SURAKSHA/
│── data/
│── notebooks/
│── models/
│── outputs/
│── app.py
│── index.html
│── requirements.txt
│── README.md
```

---

## Future Roadmap

### Phase 2: RAG-based FIR Assistant

Concept:

An AI-powered FIR drafting assistant using the Bhartiya Nyaya Sanhita (BNS) 2023 corpus.

Functionality:

* Accepts natural language incident descriptions
* Retrieves relevant legal sections
* Generates legally structured FIR drafts

Status:

Development planned as the next phase of the project.

---

## Technical Stack

### Core

* Python
* Pandas
* NumPy
* Scikit-learn

### Visualization

* Plotly
* Chart.js
* HTML5
* CSS3

### AI and NLP (Upcoming)

* LangChain
* ChromaDB
* Ollama (Llama 3.2)

---

## Why This Project Matters

* Enables data-driven policing
* Improves resource allocation
* Supports proactive crime prevention
* Converts raw datasets into actionable intelligence

---

## Author

Gaurav Yadav

---

## License

This project is intended for research and educational purposes.
