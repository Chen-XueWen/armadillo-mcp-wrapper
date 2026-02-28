#!/bin/bash

# Kill any existing processes on port 8000 or streamlit default port 8501
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "🚀 Starting Governor-MCP Backend..."
/opt/anaconda3/envs/deepseek-ocr/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

echo "📊 Starting Governor-MCP Frontend..."
cd frontend-react
npm run dev &
cd ..

echo "Waiting for services to spin up..."
sleep 5

echo "🤖 Starting Simulation..."
/opt/anaconda3/envs/deepseek-ocr/bin/python simulation/agent_mock.py
