#!/bin/bash

# Deploy script for backend services
# Runs services in the correct order

echo "🚀 Starting deployment..."

# Kill any existing processes first
echo "🛑 Killing any existing processes..."

# Kill PubSub emulator
pkill -f "cloud-pubsub-emulator" 2>/dev/null
pkill -f "pubsub.*emulator" 2>/dev/null

# Kill Python processes
pkill -f "python -m app.main" 2>/dev/null
pkill -f "subscriber_service.py" 2>/dev/null
pkill -f "setup_emulator.py" 2>/dev/null

# Kill any processes running on port 8080 (main app) or 8085 (pubsub)
lsof -ti:8080 | xargs kill -9 2>/dev/null
lsof -ti:8085 | xargs kill -9 2>/dev/null

echo "✅ Previous processes killed"
sleep 2

# Step 1: Start PubSub emulator
echo "1️⃣ Starting PubSub emulator..."
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
gcloud beta emulators pubsub start --host-port=127.0.0.1:8085 --project=demo-project &
PUBSUB_PID=$!

# Wait for emulator to start
echo "⏳ Waiting for PubSub emulator to start..."
sleep 5

# Step 2: Setup emulator (topics/subscriptions)
echo "2️⃣ Setting up emulator..."
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
python setup_emulator.py

# Step 3: Start main application
echo "3️⃣ Starting main application..."
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
python -m app.main &
MAIN_PID=$!

# Wait for main app to start
sleep 3

# Step 4: Start subscriber service
echo "4️⃣ Starting subscriber service..."
export PUBSUB_EMULATOR_HOST=127.0.0.1:8085
python subscriber_service.py &
SUBSCRIBER_PID=$!

echo "✅ All services started successfully!"
echo "📝 Process IDs:"
echo "   PubSub Emulator: $PUBSUB_PID"
echo "   Main App: $MAIN_PID"
echo "   Subscriber: $SUBSCRIBER_PID"

# Keep script running and handle cleanup on exit
cleanup() {
    echo "🛑 Stopping services..."
    kill $PUBSUB_PID $MAIN_PID $SUBSCRIBER_PID 2>/dev/null
    echo "✅ Services stopped"
}

trap cleanup EXIT INT TERM

# Wait for any process to exit
wait