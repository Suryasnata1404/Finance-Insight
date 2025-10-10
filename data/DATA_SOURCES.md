# 📊 DATA_SOURCES.md  
**Project:** Finance Insight — Financial Text Processing & NER Preparation  

---

## 📁 Overview  
This document lists all the raw datasets collected, their sources, and the corresponding processing steps completed.  
All data is stored locally for privacy and size reasons and **not uploaded to GitHub**.  

---

## 🗞️ NEWS DATASETS
| No. | Dataset Name | Source / Link | Format | Description |
|-----|---------------|----------------|----------|--------------|
| 1 | Financial PhraseBank | [Kaggle](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news) | `.csv` | Labeled financial news sentences with sentiment annotations. |
| 2 | US Financial News Articles | [Kaggle](https://www.kaggle.com/datasets/jeet2016/us-financial-news-articles) | `.csv` | U.S. finance news articles covering stocks, markets, and companies. |

---

## 🧾 SEC FILINGS DATASETS
| No. | Dataset Name | Source / Link | Format | Description |
|-----|---------------|----------------|----------|--------------|
| 3 | SEC Financial Statement Extracts | [Kaggle](https://www.kaggle.com/datasets/securities-exchange-commission/financial-statement-extracts) | `.json` | Structured SEC filing extracts containing company-level financial statements. |
| 4 | SEC Filings (10-K, 10-Q) | [SEC.gov](https://www.sec.gov/edgar/search) | `.txt`, `.pdf` | Annual (10-K) and Quarterly (10-Q) reports from companies like Apple and Tesla. |

---

## 📈 REPORTS / ANALYST DATASETS
| No. | Dataset Name | Source / Link | Format | Description |
|-----|---------------|----------------|----------|--------------|
| 5 | NYSE & Earnings Call Transcripts | [Kaggle](https://www.kaggle.com/datasets/dgawlik/nyse) | `.csv`, `.txt` | Financial analyst reports, NYSE earnings transcripts, and related company data. |

---

## 🌐 WIKIPEDIA FINANCIAL TEXTS
| No. | Page Title | Link | Format | Description |
|-----|-------------|------|----------|--------------|
| 6 | M&A by Microsoft | [Wikipedia](https://en.wikipedia.org/wiki/List_of_mergers_and_acquisitions_by_Microsoft) | `.txt` | List of Microsoft mergers and acquisitions. |
| 7 | M&A by Amazon | [Wikipedia](https://en.wikipedia.org/wiki/List_of_mergers_and_acquisitions_by_Amazon) | `.txt` | List of Amazon mergers and acquisitions. |
| 8 | Accounting | [Wikipedia](https://en.wikipedia.org/wiki/Accounting) | `.txt` | General accounting definitions and principles. |
| 9 | Financial Economics | [Wikipedia](https://en.wikipedia.org/wiki/Financial_economics) | `.txt` | Financial economics fundamentals and key concepts. |
| 10 | Stock Market | [Wikipedia](https://en.wikipedia.org/wiki/Stock_market) | `.txt` | Stock market definitions, structure, and operation details. |

---

## ⚙️ Processing Summary

### 🧩 Data Unification (`prepare_dataset.py`)
- Unified raw data from multiple formats: **CSV, JSON, TXT, PDF, HTML**
- Removed duplicates using SHA-256 hash matching  
- Normalized whitespace and encoding  
- **✅ Total unique records:** `23,474`  
- **🗑️ Duplicates removed:** `1,711,908`

### 🧼 Text Preprocessing (`preprocess_data.py`)
- Cleaned and normalized financial text:
  - Removed HTML tags and special symbols  
  - Standardized currencies, abbreviations (EPS, EBITDA, P/E), and dates  
  - Normalized whitespace and casing  
- **✅ Cleaned records saved:** `23,474` → `data/processed/preprocessed_dataset.jsonl`

### 🧠 Linguistic Feature Extraction (`tokenize_features.py`)
- Performed:
  - **Tokenization**
  - **Part-of-Speech (POS) Tagging**
  - **Lemmatization**
- Extracted token-level features for each record
- **✅ Records processed:** `23,474`
- **📊 Token statistics file:** `data/processed/token_stats.csv`

---

## 🧮 Dataset Statistics Summary
| Step | Records | File Path |
|------|----------|------------|
| Unified Corpus | 23,474 | `data/processed/merged_dataset.jsonl` |
| Preprocessed Data | 23,474 | `data/processed/preprocessed_dataset.jsonl` |
| Tokenized Features | 23,474 | `data/processed/linguistic_features.jsonl` |

---

## 🧰 Tools & Libraries Used
| Category | Libraries |
|-----------|------------|
| Core Data | `pandas`, `json`, `os`, `re` |
| Text Cleaning | `unicodedata`, `hashlib`, `BeautifulSoup` |
| PDF Handling | `pdfplumber`, `pypdf` |
| NLP Processing | `spaCy (en_core_web_sm)` |
| Visualization (EDA) | `matplotlib`, `seaborn`, `tqdm` |

---

> ⚠️ *Note:*  
> The raw and processed data files are stored locally for internal research purposes only.  
> Large `.jsonl`, `.csv`, and `.pdf` files are **excluded from GitHub** via `.gitignore` to keep the repository clean and lightweight.
