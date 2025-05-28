#!/bin/bash

# Simple CI/CD Pipeline Setup Script

echo "🚀 Setting up CI/CD Pipeline"
echo "============================="

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    echo "❌ Please run this script from the project root directory"
    exit 1
fi

echo "✅ Project structure looks good"

# Install pytest-cov if not in requirements
if ! grep -q "pytest-cov" requirements.txt; then
    echo "📦 Adding pytest-cov to requirements.txt"
    echo "pytest-cov" >> requirements.txt
fi

# Create .env.example if it doesn't exist
if [ ! -f ".env.example" ]; then
    echo "📝 Creating .env.example file"
    cat > .env.example << EOF
# Environment Variables for Testing
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
OPENAI_API_KEY=your-openai-api-key
AZURE_SPEECH_KEY=your-azure-speech-key
AZURE_SPEECH_REGION=your-azure-region
ASSEMBLYAI_API_KEY=your-assemblyai-key
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
EOF
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Add your API keys to GitHub Secrets"
echo "2. Push your code to trigger the workflows"
echo ""
echo "Commands to push:"
echo "  git add ."
echo "  git commit -m 'Add CI/CD pipeline'"
echo "  git push" 