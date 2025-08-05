# Recruiit 🧠💼  
**A RAG-Based AI Recruitment Assistant**

Recruiit is an intelligent recruitment tool that leverages vector embeddings, rule-based ranking, and external candidate sourcing via the LinkedIn ContactOut API. It enables companies to find the most relevant candidates from an internal database or the web — automatically and intelligently.

---

## 🚀 Features

- 🔍 **Semantic Resume Search**: Stores candidate resumes using vector embeddings for context-aware matching.
- ⚖️ **Rule-Based Ranking**: Candidates are sorted based on customizable rules (e.g., skills, experience, availability).
- 🌐 **External Candidate Fetching**: If no match is found, it uses the **ContactOut API** to scrape new candidates from LinkedIn.
- 🧠 **SQL Agent**: A natural language to SQL agent to query candidate databases using GPT.
- 📊 **Fast & Scalable**: Designed for small to mid-sized recruitment teams or HR tech startups.

---

## 🧠 Tech Stack

| Tool | Purpose |
|------|---------|
| **Python** | Core backend logic |
| **FAISS / Chroma / SentenceTransformers** | Vector store for resume embeddings |
| **OpenAI / LLM** | Query parsing and SQL agent |
| **ContactOut API** | External candidate sourcing |
| **SQL** | Resume and candidate data storage |
| **FastAPI ** | API wrapper  |

---

## 📂 Folder Structure

recruiit/
│
├── data/ # Sample resumes / job descriptions
├── embeddings/ # Vector DB or serialized vectors
├── sql_agent/ # SQL agent logic
├── recruiter_engine/ # Core logic for matching & ranking
├── contactout_integration/ # LinkedIn + ContactOut fetch logic
├── utils/ # Helper functions
├── requirements.txt # Python dependencies
└── README.md # Project documentation

yaml
Copy
Edit

---

## ⚙️ How to Run

```bash
# Clone the repo
git clone https://github.com/yourusername/recruiit.git
cd recruiit

# (Optional) Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # For Linux/macOS
venv\Scripts\activate     # For Windows

# Install dependencies
pip install -r requirements.txt

# Run main script
python main.py
📌 Use Cases
HR agencies seeking to automate resume screening

Startups building AI-powered recruitment platforms

Internal tools for enterprise hiring workflows

Enhancing ATS (Applicant Tracking Systems) with AI



🙋‍♂️ Author
Rohitash Bishnoi
Agentic AI Intern @ Zocket | Ex Intern @ Blu Parrot, Confedo AI, InstaAd, Drooid
gmail • ✉️ rohitashbishnoi852@gmail.com

