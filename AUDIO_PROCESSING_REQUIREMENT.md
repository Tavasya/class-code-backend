# Audio Processing Requirement for Pronunciation Practice

## Important Note

For the pronunciation practice flow to work correctly, **all audio URLs must be processed through the AudioService before pronunciation analysis**.

### Why This is Required

The AudioService handles:
- Audio format conversion (WebM to WAV)
- Audio normalization 
- Proper encoding for Azure Speech Services
- File format validation

### Implementation Requirement

**Before any pronunciation analysis for practice sessions:**

1. Audio URL must be downloaded via `AudioService.download_audio()`
2. Audio must be converted to WAV format via `AudioService.convert_webm_to_wav()` 
3. Only then can the processed audio file be passed to pronunciation analysis

### Current Implementation Status

✅ **Already Implemented**: The current practice endpoint (`improve_session_transcript`) handles transcript improvement only and does NOT do pronunciation analysis.

⚠️ **Future Requirement**: If/when pronunciation analysis is added to the practice flow, the audio processing step will be mandatory.

### Code Pattern for Future Pronunciation Practice

```python
# Required pattern for any pronunciation practice feature:

# 1. Download audio from URL
temp_audio_file = await AudioService.download_audio(audio_url)

# 2. Convert to WAV if needed  
if not temp_audio_file.endswith('.wav'):
    wav_file = await AudioService.convert_webm_to_wav(temp_audio_file)
    temp_audio_file = wav_file

# 3. NOW pronunciation analysis can proceed
result = await PronunciationService.analyze_pronunciation(temp_audio_file, transcript)

# 4. Clean up temp files
os.unlink(temp_audio_file)
```

### Notes

- This requirement applies to **pronunciation analysis only**
- The current transcript improvement feature does not need this (it only transcribes and improves text)
- If pronunciation scoring is added later, this audio processing step is mandatory