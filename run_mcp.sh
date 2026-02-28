
#!/bin/bash

# Kill any existing processes on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:5173 | xargs kill -9 2>/dev/null

echo "🚀 Starting Governor-MCP Backend (Dashboard API)..."
/opt/anaconda3/envs/deepseek-ocr/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &

echo "📊 Starting Governor-MCP Frontend..."
cd frontend-react
npm run dev &
cd ..

echo "✅ Governor Dashboard is running!"
echo "   - View Dashboard: http://localhost:5173"
echo "   - Connect MCP Client: python $(pwd)/backend/mcp_server.py"
echo ""
echo "Press Ctrl+C to stop the dashboard."

# Wait indefinitely
wait
