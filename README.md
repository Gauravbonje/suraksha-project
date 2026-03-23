# suraksha-project 
SURAKSHA: Uttar Pradesh Crime Intelligence and Predictive Policing System
SURAKSHA is a comprehensive data engineering and machine learning framework designed to analyze historical crime patterns and predict future hotspots across Uttar Pradesh, India. The system leverages over 10 years of official government data (2014–2023) to provide a granular, district-level intelligence layer for law enforcement decision-making.

Project Core Philosophy
The primary focus of this project is the transformation of unstructured, fragmented government data into high-fidelity intelligence. It emphasizes the rigorous process of information gathering, data cleaning, and feature engineering to reveal a "different picture" of crime trends that are often hidden in raw spreadsheets.

Data Engineering and Information Gathering
The project prioritizes the "Data First" approach. Before any modeling, a significant effort was invested in:

Source Integration: Automated ingestion of 67 NCRB (National Crime Records Bureau) Excel files (2016–2023) and multi-year Kaggle datasets.

Automated Extraction: Developed custom Python logic to scan unstructured spreadsheets, detect specific "State: Uttar Pradesh" header rows, and extract data across all 75+ districts.

Dataset Consolidation: Created a master repository consisting of 7,592 rows covering 20 crime categories, including IPC, SLL, Crimes against Women, Children, SC/STs, Cybercrime, and Juvenile delinquency.

Information Extraction: Beyond raw counts, the system calculates "Crime Intensity Scores" (0–100) and identifies "Signature Crimes" for every district, providing a normalized view of public safety.

Machine Learning and Training Pipeline
The predictive power of SURAKSHA is derived from training models on historical sequences:

Feature Engineering: Implemented temporal lag features (Lag1, Lag2) and three-year rolling means (RollMean3) to capture the momentum of crime.

Model Training: Evaluated multiple algorithms, including Gradient Boosting and Linear Regression, ultimately selecting a Random Forest Regressor.

Performance Metrics: The system achieved an R-squared (R2) score of 0.83 and a Root Mean Square Error (RMSE) of 884 cases, ensuring high reliability in predictions.

2024 Hotspot Prediction: Generated over 1,000 unique predictions for the 2024 calendar year, identifying high-risk district-crime combinations.

Strategic Insights and Analysis
The system generates 15 specialized CSV outputs that provide a multidimensional view of the state:

Regime Analysis: Comparative study of crime reporting and control across different administrative phases (2014–2016 vs. 2017–2023).

COVID-19 Impact: Statistical validation showing a 22% drop in street crimes (kidnapping) vs. a 20.5% rise in domestic-related offences (rape) during 2020 lockdowns.

Law & Order Report Cards: Automated grading (A through F) of districts based on recent 3-year improvement performance.

Deployment and Usage
Mode 1: Interactive Intelligence App (Streamlit)
Designed for live interaction, dynamic filtering, and AI-driven predictions.

Bash
pip install -r requirements.txt
streamlit run app.py
Mode 2: Static Documentation and Geographic Map (index.html)
For offline viewing of the pre-rendered analysis and interactive district profiles.

Run a local server to allow GeoJSON loading:

Bash
python3 -m http.server 8080
Open http://localhost:8080/index.html in any modern browser.

Future Roadmap: Phase 2 (RAG FIR Assistant)
The next evolution of SURAKSHA will include a Retrieval-Augmented Generation (RAG) system:

Concept: An AI-powered FIR drafting assistant using the BNS (Bhartiya Nyaya Sanhita) 2023 corpus.

Functionality: Officers input incident descriptions in natural language; the system retrieves relevant BNS sections and drafts a legally accurate FIR.

Status: Development for Phase 2 will commence shortly as an update to this repository.

Technical Stack
Core: Python (Pandas, Scikit-learn, NumPy)

Visualization: Plotly, Chart.js, HTML5/CSS3

AI/NLP (Next Phase): LangChain, ChromaDB, Ollama (Llama 3.2)
