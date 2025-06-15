#!/bin/bash
# Docker build and management script for Annotation Engine

set -e

# Configuration
IMAGE_NAME="annotation-engine"
TAG="${1:-latest}"
BUILD_TYPE="${2:-prod}"

echo "🐳 Building Annotation Engine Docker Image"
echo "==========================================="
echo "Image: ${IMAGE_NAME}:${TAG}"
echo "Build type: ${BUILD_TYPE}"
echo ""

# Choose Dockerfile based on build type
if [ "$BUILD_TYPE" = "dev" ]; then
    DOCKERFILE="Dockerfile.dev"
    echo "📦 Building development image..."
else
    DOCKERFILE="Dockerfile"
    echo "🚀 Building production image..."
fi

# Build the image
docker build -f $DOCKERFILE -t ${IMAGE_NAME}:${TAG} .

echo ""
echo "✅ Build complete!"
echo ""
echo "🔧 Available commands:"
echo "  Run CLI:        docker run --rm ${IMAGE_NAME}:${TAG}"
echo "  Interactive:    docker run --rm -it ${IMAGE_NAME}:${TAG} bash"
echo "  With volumes:   docker run --rm -v \$(pwd)/data:/app/data ${IMAGE_NAME}:${TAG}"
echo "  Compose up:     docker-compose up -d"
echo ""

# Test the image
echo "🧪 Testing image..."
docker run --rm ${IMAGE_NAME}:${TAG} python -c "
import annotation_engine
print('✅ Annotation Engine import successful')
print('🔧 Testing CLI...')
"

echo "🎉 Image ready for use!"