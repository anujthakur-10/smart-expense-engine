# 🧠 SMART EXPENSE ENGINE - COMPLETE PROJECT KNOWLEDGE BASE

**Instructions for the AI Assistant reading this file:**
You are acting as a Technical Writer and Academic Thesis Assistant. The human user is providing this document to you as the ultimate source of truth for their 4th-year CSE-AIML Major Project. 
Do NOT hallucinate features. Rely entirely on the technical mechanisms, architectures, and algorithms described below when generating report chapters, diagrams, or explanations for the user.

---

## 1. PROJECT OVERVIEW
* **Project Title:** Smart Expense Engine and Predictive Analytics
* **Target Audience:** Indian Kirana stores and micro-SMEs.
* **Core Objective:** To automate the ingestion of dirty, bilingual (Hindi/English) handwritten and printed invoices, extract structured financial data, compute Indian GST automatically, detect duplicate/fraudulent invoices, and predict future expenses using multi-model Time-Series Machine Learning.

## 2. TECHNOLOGY STACK
* **Frontend:** React.js (v18), Vite, Recharts (for Tableau-style minimalist white-themed analytics), Lucide React (icons).
* **Backend:** FastAPI (Python), Uvicorn (Async server).
* **Database & Auth:** Supabase (PostgreSQL), Supabase Auth (JWT).
* **Machine Learning & CV:** 
  * Computer Vision: OpenCV (cv2)
  * OCR: PaddleOCR
  * Forecasting: XGBoost, LightGBM, Meta Prophet, scikit-learn, Pandas.
  * Academic Deep Learning: HuggingFace Transformers (Donut Model).

## 3. ARCHITECTURE & DATA FLOW (End-to-End)
1. User uploads an invoice (JPEG/PNG/PDF) via React frontend.
2. File is sent to FastAPI `/api/upload` endpoint.
3. **Image Preprocessor** cleans the image (removes shadows, binarizes).
4. **OCR Engine** extracts raw text (bilingual).
5. **Invoice Parser** uses Regex to find Vendor Name, Date, Amounts, and GSTIN.
6. **GST Engine** calculates CGST/SGST/IGST based on GSTIN state codes.
7. **Fraud Detector** hashes the data to check for duplicates in PostgreSQL.
8. Data is saved in Supabase.
9. **Forecaster** pulls historical data and predicts next month's expenses on the dashboard.

---

## 4. DEEP-DIVE: TECHNICAL MODULES & NOVELTY

### 4.1 Image Preprocessing Pipeline (OpenCV)
*The Novelty:* Real-world Indian shop receipts are crumpled, poorly lit, and faded. 
*The Pipeline (6-Stages):*
1. **Grayscale Conversion:** Reduces to 1-channel intensity.
2. **Shadow Removal:** Uses Morphological Dilation (7x7 kernel) to estimate background illumination and normalize lighting.
3. **Denoising:** `cv2.fastNlMeansDenoising` removes camera sensor noise without blurring text edges.
4. **CLAHE:** Enhances local contrast so faded thermal prints become readable.
5. **Adaptive Binarization:** Gaussian adaptive thresholding converts the image to pure black & white.
6. **Deskewing:** Detects text angle using `minAreaRect` on contours and rotates the image to 0 degrees.

### 4.2 The OCR Engine (PaddleOCR)
*The Novelty:* Commercial OCRs fail at Hindi handwriting.
*The Logic:* Uses a **Dual-Pass Strategy**. 
1. Runs English (Latin) model pass.
2. Runs Hindi (Devanagari) model pass.
3. Compares bounding box confidence scores and merges the highest confidence text. This perfectly extracts bilingual bills.

### 4.3 Invoice Parsing & Indian GST Engine
*The Novelty:* Fully automated compliance without manual entry.
*The Logic:*
1. **Parsing:** Uses Regular Expressions (Regex) to isolate the 15-character GSTIN (`^[0-9]{2}[A-Z]{5}...`).
2. **Tax Splitting (Crucial):** Extracts the first 2 digits of the GSTIN (State Code). 
3. Compares Vendor's State Code with User's State Code.
   * If `Intra-state` (Same code): Splits the tax 50/50 into **CGST** and **SGST**.
   * If `Inter-state` (Different code): Allocates 100% of the tax to **IGST**.

### 4.4 Fraud & Duplicate Detection Shield
*The Novelty:* Prevents SMEs from paying the same bill twice.
*The Logic (3-Tier Check):*
1. **Hash Match (100% Confidence):** Generates a SHA-256 cryptographic hash of `(vendor_name + invoice_number + total_amount)`. If hash exists in DB = Exact Duplicate.
2. **Exact Match (95% Confidence):** Checks if the same invoice number exists for the same vendor (case-insensitive).
3. **Fuzzy Match (75% Confidence):** If invoice number is missing, checks if the *same vendor* billed the *same amount* within a *±3 days window*. Flags as "Possible Duplicate".

### 4.5 Predictive Analytics (Time-Series Forecasting)
*The Novelty:* Multi-model competitive forecasting with India-specific feature engineering.
*The Logic:*
* **Models Used:** Prophet, XGBoost, LightGBM.
* **Feature Engineering:** Adds an `is_festive` flag (True for Oct, Nov, Dec) because Indian SMEs see massive expense spikes during Diwali/New Year. Also uses lag features (previous 1/2/3 months) and cyclical encoding (sine/cosine of months).
* **Comparison:** The system runs all 3 models, evaluates them using MAE (Mean Absolute Error), RMSE, and MAPE, and dynamically selects the model with the lowest error for the dashboard display.

### 4.6 Track-B: Academic Fine-Tuning (Donut Transformer)
*The Novelty:* While Track-A (PaddleOCR) runs the production app, Track-B provides academic weight for the thesis.
*The Logic:*
* A Python script runs in Google Colab (T4 GPU).
* Downloads the **CORD Dataset** (Consolidated Receipt Dataset - 1,000 receipt images).
* Fine-tunes the `naver-clova-ix/donut-base` model.
* Donut is an OCR-free Transformer (Vision Encoder + Text Decoder) that converts raw pixels directly into structured JSON tags (e.g., `<s_total>500</s_total>`).

---

## 5. DATABASE SCHEMA (PostgreSQL / Supabase)

**Table: invoices**
* `id` (UUID, Primary Key)
* `user_id` (UUID, Foreign Key to Supabase Auth)
* `invoice_number` (String)
* `vendor_name` (String)
* `invoice_date` (Date)
* `subtotal`, `cgst`, `sgst`, `igst`, `total_amount` (Float)
* `vendor_gstin` (String)
* `is_inter_state` (Boolean)
* `status` (Enum: pending, reviewed, approved)
* `is_duplicate` (Boolean)
* `invoice_hash` (String, Unique)

**Table: vendors**
* `id` (UUID, Primary Key)
* `vendor_name` (String)
* `gstin` (String)
* `state_code` (String)

---

## 6. FRONTEND DESIGN SYSTEM
* **Aesthetic:** Clean, minimal, "Tableau-inspired" white/off-white theme.
* No glassmorphism, no heavy shadows. 
* Uses solid emerald green (`#10b981`) as the primary accent color.
* Charts use crisp white backgrounds, light grey grids, and distinct solid line colors (red, green, blue).

## 7. AUTHENTICATION (The ES256 Bypass Note)
* Uses Supabase JWTs. 
* Note on implementation: Supabase recently switched token signing algorithms to `ES256` (Elliptic Curve). For the local academic build, the backend `auth.py` was configured with `verify_signature=False` in PyJWT to allow seamless API communication without complex JWKS public key rotation handling, relying on the frontend SDK for session integrity.

---
**END OF CONTEXT FILE**
