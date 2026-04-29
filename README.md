# Scentrix — Fragrance Recommendation System

## Overview
Scentrix is a high-performance fragrance discovery system designed to help users navigate the complex world of perfumes through an intuitive, data-driven approach. The system deconstructs the olfactive universe into molecular components—notes, accords, and categories—to find the perfect match for any user preference.

Built with a focus on efficiency and scalability, Scentrix was specifically engineered to operate within a tight 512MB memory constraint. This was achieved by moving heavy machine learning computations offline and utilizing a hybrid recommendation strategy that combines deterministic rule-based logic with pre-computed semantic embeddings.

## Live Demo
- Frontend: [https://scentrix-one.vercel.app](https://scentrix-one.vercel.app)
- Backend: [https://scentrix-backend-prod.onrender.com](https://scentrix-backend-prod.onrender.com)

## Architecture
The system follows a modern decoupled architecture:

- **Frontend**: Next.js 15 application deployed on Vercel, providing a responsive and cinematic user interface.
- **Backend**: FastAPI service deployed on Render, handling request orchestration and recommendation logic.
- **Data**: A unified JSON Single Source of Truth (SSOT) containing 4,577 elite fragrance records, optimized for fast lookups and low memory footprint.
- **ML Strategy**: 
  - **Offline**: Semantic embeddings are generated using sentence-transformers and stored in a compressed format.
  - **Runtime**: Recommendation scoring is performed using NumPy-based cosine similarity, ensuring sub-100ms response times without loading heavy model weights into RAM.

## Key Features
- **Hybrid Recommendation Engine**: Combines structural data (notes/accords) with semantic meaning (descriptions) for high-precision matching.
- **Memory-Safe Pipeline**: Optimized to run on resource-constrained environments (512MB RAM) through pre-computed vectors and lazy-loading.
- **Deterministic Quiz System**: A multi-step discovery process that seeds recommendation sessions with unique user preference vectors.
- **Fallback-Safe Architecture**: Designed to operate even when external database dependencies (Redis/Neo4j) are unavailable.
- **High Performance**: Optimized scoring loops delivering recommendations in under 50ms.

## Recommendation Logic
The engine utilizes a multi-factor scoring algorithm that evaluates fragrances across several dimensions:
- **Structural Similarity**: Overlap analysis of top, middle, and base notes.
- **Accord Profiling**: Evaluation of primary olfactive accords (e.g., woody, floral, citrus).
- **Metadata Matching**: Filtering and boosting based on gender, concentration, and brand reputation.
- **Semantic DNA**: Pre-computed vector similarity based on deep fragrance descriptions.
- **Popularity Weighting**: Prioritizing fragrances with high community engagement (Elite Pool).

## Performance
- **Latency**: 40–50ms average for recommendation generation.
- **Memory Overhead**: ~7MB for the entire embedding index.
- **Total Footprint**: Fully operational within a 512MB environment.

## Tech Stack
- **Backend**: FastAPI, Python 3.11
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Processing**: NumPy, Sentence-Transformers (Offline)
- **Infrastructure**: Render (API), Vercel (UI), Supabase (PostgreSQL)

## Setup Instructions

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Design Decisions
- **No Runtime ML**: Loading large LLMs or BERT models into production RAM was avoided to maintain 512MB compatibility and eliminate cold-start latency.
- **Offline Embeddings**: By pre-computing vectors, we achieve the benefits of semantic search with the speed of raw matrix multiplication.
- **JSON as SSOT**: Using a structured JSON file as the primary source of truth allows for extremely fast I/O and simplifies deployment by reducing external DB round-trips for core catalog data.
- **Fallback Architecture**: The system proactively handles infrastructure outages (e.g., Neo4j or Redis downtime) by falling back to local memory-safe discovery modes.

## Future Work

### Feedback Loop (User Interaction Logging)
- Track user actions such as clicks, skips, and selections
- Store interaction data for analysis
- Enable data-driven improvement of recommendations

### Evaluation Metrics
- Define metrics such as:
  - Click-through rate (CTR)
  - Top-K hit rate
- Use these metrics to evaluate recommendation quality

### Personalization Engine
- Build user profiles based on interaction history
- Adapt recommendations over time
- Transition from stateless to stateful system

> Note: The current system is intentionally stateless for stability, low memory usage, and deployment simplicity under constrained environments.


## Author
- **Name**: Sujoy
- **GitHub**: [https://github.com/Sujoy-004](https://github.com/Sujoy-004)
