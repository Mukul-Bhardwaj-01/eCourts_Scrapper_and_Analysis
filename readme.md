
# ⚖️ eCourts Legal Analytics

An AI-powered legal analytics platform that automates extraction, analysis, summarization, and visualization of case information from the Indian eCourts portal.

## 🚀 Overview

eCourts Legal Analytics is designed to assist practicing advocates and legal professionals by reducing the manual effort involved in tracking and analyzing court cases. The platform combines browser automation, document processing, generative AI, and interactive dashboards to provide actionable legal insights.

The system accepts multiple CNR (Case Number Record) identifiers, automatically retrieves case information from the eCourts portal, extracts relevant metadata, downloads the latest court orders, generates AI-powered summaries, and presents the results through Excel reports and interactive dashboards.

---

## ✨ Features

### 🔍 Automated Case Extraction

* Bulk processing of multiple CNR numbers
* Automated navigation of the Indian eCourts portal
* Human-in-the-loop CAPTCHA handling
* Extraction of structured case information

### 📄 Court Order Processing

* Automatic download of the latest interim/final orders
* PDF text extraction and cleaning
* Metadata extraction and document analytics

### 🤖 AI-Powered Legal Summaries

* Integration with Groq LLM APIs
* Automatic extraction of:

  * Latest hearing outcome
  * Next action required
  * Key parties involved
* Caseload-level AI analysis

### 📊 Interactive Analytics Dashboard

* Case-type distribution analysis
* Hearing prioritization dashboard
* Adjournment tracking
* Court workload analysis
* Timeline visualizations
* Judge-wise and court-wise analytics

### 📈 Reporting

* Automated Excel report generation
* Email delivery support
* Summary statistics and performance metrics

---

## 🏗️ System Workflow

```text
User Details
      ↓
Enter Multiple CNR Numbers
      ↓
Selenium Automation
      ↓
Manual CAPTCHA Verification
      ↓
Case Data Extraction
      ↓
Latest Court Order Download
      ↓
PDF Processing
      ↓
Groq AI Summarization
      ↓
Excel Report Generation
      ↓
Interactive Dashboard
```

---

## 🛠️ Tech Stack

### Backend

* Python

### Automation

* Selenium
* WebDriver Manager

### AI & NLP

* Groq API
* LLaMA Models

### Data Processing

* Pandas
* pdfplumber

### Visualization

* Plotly
* Streamlit

### Reporting

* OpenPyXL
* Excel Automation

---

## 📊 Key Analytics

The dashboard provides:

* Case Type Distribution
* Pending vs Disposed Cases
* Hearing Timeline Analysis
* Adjournment Analytics
* Upcoming Hearing Prioritization
* Court Workload Distribution
* Judge-wise Analysis
* Monthly Filing Trends
* AI-generated Caseload Insights

---

## ⚠️ Challenges Solved

* Handling CAPTCHA-protected government portals
* Processing inconsistent HTML structures
* Extracting meaningful information from legal PDFs
* Summarizing unstructured legal text using LLMs
* Designing scalable multi-case workflows
* Building interactive analytics for legal practitioners

---

## 🎯 Use Cases

* Practicing Advocates
* Law Firms
* Legal Researchers
* Litigation Management
* Court Case Analytics

---

## 📌 Future Enhancements

* OCR support for scanned court orders
* Case status notifications
* Hearing date reminders
* Multi-user authentication
* Database integration
* Predictive legal analytics
* Advanced AI legal reasoning

---

## 👨‍💻 Author

**Mukul Bhardwaj**

B.E. Computer Science Engineering
UIET, Panjab University

---

*This project was developed as an exploration of legal technology, automation, generative AI, and data analytics.*
