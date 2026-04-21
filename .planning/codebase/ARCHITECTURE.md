# System Architecture: Scentrix

## Overview
Scentrix is a decoupled multi-service application designed for scalable olfactory discovery. It uses a hybrid graph-neural approach to power its recommendation engine.

## Core Services
1. **API (Backend)**: Single point of entry for the frontend and external clients. Handles auth, user profile management, and serves recommendation results.
2. **Celery Worker**: Offloads heavy tasks (Neural inference, re-ranking, taste-vector generation) to prevent blocking the API.
3. **Frontend**: A cinematic Next.js interface for user onboarding and discovery.
4. **ML Component**: Dedicated logic for graph ingestion (Neo4j) and text DNA encoding.

## Data Flow
- **Onboarding**: Quiz Responses → API → Redis (Session) → User Conversion → PostgreSQL (Profile).
- **Recommendation**: User Ratings → Celery → Hybrid Recommender (Neo4j + Pinecone) → API Result.
- **Security**: All PII (Name, Email) is encrypted via the **DataVault** service before SQL storage.
