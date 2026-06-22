#!/usr/bin/env bash
uvicorn api:app --host 0.0.0.0 --port 8000 &
streamlit run ui.py --server.port $PORT --server.address 0.0.0.0