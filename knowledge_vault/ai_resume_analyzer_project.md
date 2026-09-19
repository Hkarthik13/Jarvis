# Project: AI Resume Analyzer & Matcher

## Overview
AI Resume Analyzer is an intelligent recruitment tool built to evaluate candidate resumes against job descriptions, calculate semantic match percentages, extract key technical competencies, and highlight missing skills.

## Core Technologies Used
- **Backend**: Python 3.11, FastAPI, Pydantic v2, Uvicorn
- **AI / LLM Framework**: Groq API (`llama-3.3-70b-versatile`, `qwen/qwen3.8-27b`), LangChain
- **Embeddings & Vector Store**: FAISS (Facebook AI Similarity Search), SentenceTransformers (`all-MiniLM-L6-v2`)
- **Document Parsing**: PyPDF2, pdfplumber, python-docx for PDF and Word resume parsing
- **Frontend**: React 18, Vite, TailwindCSS, Lucide React icons
- **Database & Cache**: PostgreSQL (candidate records), Redis (rate limiting & task caching)
- **DevOps & Containerization**: Docker, Docker Compose, GitHub Actions CI/CD

## Key Features
1. **Multi-Format Ingestion**: Parses PDFs, DOCX, and text resumes with layout-aware section extraction (Education, Experience, Skills, Certifications).
2. **Semantic Matching**: Computes cosine similarity between candidate embedding vectors and target job requirement embeddings.
3. **Automated ATS Scoring**: Generates 0-100% Applicant Tracking System (ATS) compatibility score.
4. **Skill Gap Analysis**: Pinpoints required technologies missing from the resume and suggests tailored improvements.
5. **Interview Question Generator**: Generates customized technical interview questions based on the candidate's stated projects and tech stack.

## Architecture & Data Flow
1. User uploads resume file via React frontend.
2. FastAPI processes file with `pdfplumber` to extract clean text.
3. Text is chunked and vectorized using dense embedding model.
4. Vector similarity is scored against the job description stored in FAISS.
5. LLM generates structured JSON summary of candidate strengths, weaknesses, and matching verdict.
