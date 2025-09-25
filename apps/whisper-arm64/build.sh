#!/bin/bash
# Build script for Whisper Jetson image

set -e

echo "Building Whisper image for Jetson (ARM64)..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build the Docker image
echo "Building Docker image..."
docker build -f "${SCRIPT_DIR}/Dockerfile.jetson" -t whisper-jetson:latest "${SCRIPT_DIR}"

echo "Build complete!"
echo ""
echo "To deploy this image to your Jetson node, you can either:"
echo "1. Save and load the image:"
echo "   docker save whisper-jetson:latest | gzip > whisper-jetson.tar.gz"
echo "   # Transfer to Jetson node"
echo "   docker load < whisper-jetson.tar.gz"
echo ""
echo "2. Or push to a registry:"
echo "   docker tag whisper-jetson:latest your-registry/whisper-jetson:latest"
echo "   docker push your-registry/whisper-jetson:latest"
echo "   # Update deployment to use your-registry/whisper-jetson:latest"
echo ""
echo "3. For local development on Jetson, build directly on the Jetson node:"
echo "   cd ${SCRIPT_DIR}"
echo "   docker build -f Dockerfile.jetson -t whisper-jetson:latest ."
