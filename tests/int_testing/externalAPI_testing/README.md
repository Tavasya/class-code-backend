# Simple External API Integration Tests

Basic tests to verify that our external API integrations work with the data we send them.

## What We Test

- **AssemblyAI** - Can it transcribe our audio URLs?
- **Azure Speech** - Can it analyze pronunciation of our audio files?
- **OpenAI** - Can it analyze grammar and vocabulary of our text?

## Running Tests

### Set API Keys

Create a `.env` file in your project root:
```bash
ASSEMBLYAI_API_KEY=your_assemblyai_key
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus
OPENAI_API_KEY=your_openai_key
```

Or set them as environment variables:
```bash
export ASSEMBLYAI_API_KEY="your_key"
export AZURE_SPEECH_KEY="your_key"
export AZURE_SPEECH_REGION="eastus"
export OPENAI_API_KEY="your_key"
```

### Run Tests
```bash
# Run all API tests
pytest tests/int_testing/externalAPI_testing/ -v -s

# Run specific service
pytest tests/int_testing/externalAPI_testing/test_assemblyai.py -v -s
pytest tests/int_testing/externalAPI_testing/test_azure_speech.py -v -s
pytest tests/int_testing/externalAPI_testing/test_openai.py -v -s
```

## What Each Test Does

### AssemblyAI Tests
- Sends a public audio URL to AssemblyAI
- Checks if we get transcribed text back
- Tests the main transcription methods

### Azure Speech Tests  
- Sends an audio file to Azure Speech
- Checks if we get a pronunciation grade back
- Tests with and without session IDs

### OpenAI Tests
- Sends text to OpenAI for grammar analysis
- Sends text to OpenAI for lexical analysis
- Checks if we get grades and feedback back
- Tests that good text gets good scores

That's it! Simple tests to make sure the APIs work with our data. 