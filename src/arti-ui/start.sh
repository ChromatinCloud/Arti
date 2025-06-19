#!/bin/bash

# Start script for Arti UI
echo "Starting Arti UI development server..."

# Navigate to the project directory
cd "$(dirname "$0")"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

# Start the development server
echo "Starting Vite development server..."
npm run dev