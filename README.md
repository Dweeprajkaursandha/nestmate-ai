# 🏠 NestMate AI — Smart Area-Based Flatmate & Room Finder

An AI-powered flatmate and shared-accommodation matchmaking web application built with **Python (Streamlit)**, **Groq Cloud API (`groq`)**, and **Folium / OpenStreetMap**.

**NestMate AI** uses a **Retrieval-Augmented Generation (RAG)** workflow: it filters candidate room and flatmate listings by locality, monthly rent budget, dietary preference, and gender, then passes matching profiles to high-speed open-weight LLMs on **Groq** to compute compatibility scores (`0–100%`), explain lifestyle alignment, and draft personalized introductory messages.

---

## ✨ Key Features

- **🧠 Groq AI Compatibility Ranking:** Evaluates natural-language lifestyle preferences (sleep schedule, study/work routine, cleanliness, hobbies) against candidate bios using structured JSON mode (`response_format={"type": "json_object"}`).
- **🔄 Automatic Model Fallback & Retry:** Built-in resilience across Groq models (`openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`) to automatically handle `429` rate limits or temporary demand spikes.
- **🗺️ Interactive Locality Map:** Powered by **Folium** and **OpenStreetMap** (`streamlit-folium`) with zero map API keys required. Displays live pins for available rooms across Delhi NCR and Bengaluru with popups and one-click fly-to navigation.
- **🔐 Account Authentication:** Sidebar Login and Sign-Up workflow backed by `users.json`.
- **📸 Room & Profile Publishing:** Logged-in users can post available rooms with photo uploads (Base64 encoded) and immediately appear on the live map and AI search feed.
- **💬 One-Click AI Icebreaker Generator:** Drafts casual, ready-to-send WhatsApp/DM intro messages tailored to shared habits between the user and a selected flatmate.
- **🎨 Dark Velvet & Burnished Gold UI:** Custom CSS glassmorphism interface with quick preference chips, interactive rent sliders, and multi-tab navigation.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend & App Framework** | Python 3.9+, Streamlit |
| **Generative AI & Inference** | Groq Python SDK (`groq`), `openai/gpt-oss-20b`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b` |
| **Maps & Geolocation** | Folium, `streamlit-folium`, OpenStreetMap Tiles |
| **Data & Session Storage** | JSON (`dataset.json`, `users.json`) & Streamlit `session_state` |

---

## 📂 Project Structure

```text
nestmate-ai/
├── streamlit_app.py      # Main Streamlit application, RAG filters, Groq AI & Folium map
├── dataset.json          # Flatmate & room listings with lat/lng coordinates
├── users.json            # Registered user login credentials
├── requirements.txt      # Python dependencies
├── .env                  # Local GROQ_API_KEY (excluded from Git)
├── .gitignore            # Git ignore rules
└── README.md             # Project documentation
