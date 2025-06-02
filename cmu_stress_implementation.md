# CMU Dictionary Integration for Stress Marks

## Overview
This document outlines the process of integrating CMU dictionary for adding stress marks to phonemes in the pronunciation assessment service.

## 1. Dependencies
```bash
pip install cmudict
```

## 2. System Components

### 2.1 Phoneme Mapping Systems
```python
# Azure phonemes to IPA (existing)
AZURE_TO_IPA = {
    "ax": "ə",   # schwa
    "ay": "aɪ",  # PRICE vowel
    "ow": "oʊ",  # GOAT vowel
    "iy": "i",   # FLEECE vowel
    "ih": "ɪ",   # KIT vowel
    "eh": "ɛ",   # DRESS vowel
    "ae": "æ",   # TRAP vowel
    "aa": "ɑ",   # PALM vowel
    "ao": "ɔ",   # THOUGHT vowel
    "uw": "u",   # GOOSE vowel
    "uh": "ʊ",   # FOOT vowel
    "er": "ɜr"   # NURSE vowel
}

# Azure to CMU mapping (new)
AZURE_TO_CMU = {
    "ax": "AH",  # schwa
    "ay": "AY",  # PRICE vowel
    "ow": "OW",  # GOAT vowel
    "iy": "IY",  # FLEECE vowel
    "ih": "IH",  # KIT vowel
    "eh": "EH",  # DRESS vowel
    "ae": "AE",  # TRAP vowel
    "aa": "AA",  # PALM vowel
    "ao": "AO",  # THOUGHT vowel
    "uw": "UW",  # GOOSE vowel
    "uh": "UH",  # FOOT vowel
    "er": "ER"   # NURSE vowel
}
```

### 2.2 Stress Mark Symbols
```python
STRESS_MARKS = {
    "1": "ˈ",  # Primary stress
    "2": "ˌ"   # Secondary stress
}
```

## 3. Process Flow

### 3.1 Word-Level Processing
1. Get word from Azure response
2. Look up word in CMU dictionary
3. Get first pronunciation (handle multiple pronunciations)
4. Extract stress pattern from CMU pronunciation

Example:
```python
# Word: "beautiful"
azure_phonemes = ["b", "y", "uw", "t", "ax", "f", "ax", "l"]
cmu_pron = ["B", "Y", "UW1", "T", "AH0", "F", "AH0", "L"]
# Expected result: /bjuˈtəfəl/
```

### 3.2 Phoneme Alignment Process

1. **Initialize Alignment**
```python
def align_phonemes(azure_phonemes, cmu_pronunciation):
    aligned = []
    vowel_index = 0
    cmu_vowel_index = 0
    
    for az_phoneme in azure_phonemes:
        alignment = {
            "azure_phoneme": az_phoneme,
            "ipa": AZURE_TO_IPA.get(az_phoneme, az_phoneme),
            "stress": None
        }
        aligned.append(alignment)
```

2. **Identify Vowels**
```python
def is_vowel(phoneme):
    # Azure vowels
    azure_vowels = ["ax", "ay", "ow", "iy", "ih", "eh", "ae", "aa", "ao", "uw", "uh", "er"]
    return phoneme.lower() in azure_vowels
```

3. **Match and Align**
```python
for i, az_phoneme in enumerate(azure_phonemes):
    if is_vowel(az_phoneme):
        # Get corresponding CMU base
        cmu_base = AZURE_TO_CMU.get(az_phoneme)
        if cmu_base:
            # Find matching CMU vowel
            for cmu_phoneme in cmu_pronunciation:
                if cmu_phoneme.startswith(cmu_base):
                    # Extract stress
                    stress = cmu_phoneme[-1]
                    aligned[i]["stress"] = stress
                    break
```

### 3.3 Stress Application Rules

1. **Primary Stress (1)**
   - CMU: Vowel ends with "1" (e.g., "AH1")
   - Action: Add "ˈ" before the IPA vowel
   - Example: "AH1" → "ˈə"

2. **Secondary Stress (2)**
   - CMU: Vowel ends with "2" (e.g., "AH2")
   - Action: Add "ˌ" before the IPA vowel
   - Example: "AH2" → "ˌə"

3. **No Stress (0)**
   - CMU: Vowel ends with "0" (e.g., "AH0")
   - Action: No stress mark added
   - Example: "AH0" → "ə"

### 3.4 Implementation Details

```python
def process_phoneme(azure_phoneme, stress):
    # Get base IPA symbol
    ipa = AZURE_TO_IPA.get(azure_phoneme, azure_phoneme)
    
    # Apply stress if present
    if stress == "1":
        return "ˈ" + ipa
    elif stress == "2":
        return "ˌ" + ipa
    return ipa
```

## 4. Edge Cases and Handling

### 4.1 Word Not in CMU Dictionary
```python
if word not in cmu_dict:
    # Skip stress marks, return basic IPA conversion
    return convert_to_basic_ipa(azure_phonemes)
```

### 4.2 Phoneme Sequence Mismatch
- When Azure and CMU have different number of vowels
- Solution: Only apply stress marks where clear match exists

### 4.3 Multiple Pronunciations
```python
# Always use first pronunciation
cmu_pron = cmu_dict.get(word, [None])[0]
```

### 4.4 Compound Words
- Azure might split: "understand" → ["under", "stand"]
- Solution: Look up full word first, fall back to parts if needed

## 5. Example Transformations

### 5.1 Simple Word
```
Word: "hello"
Azure: ["h", "eh", "l", "ow"]
CMU: ["HH", "AH0", "L", "OW1"]
Result: /həˈloʊ/
```

### 5.2 Complex Word
```
Word: "beautiful"
Azure: ["b", "y", "uw", "t", "ax", "f", "ax", "l"]
CMU: ["B", "Y", "UW1", "T", "AH0", "F", "AH0", "L"]
Result: /bjuˈtəfəl/
```

## 6. Performance Considerations

### 6.1 Caching
```python
# Cache CMU dictionary lookup
_cmu_cache = {}

def get_cmu_pronunciation(word):
    if word not in _cmu_cache:
        _cmu_cache[word] = cmu_dict.get(word, [None])[0]
    return _cmu_cache[word]
```

### 6.2 Error Handling
```python
try:
    cmu_pron = get_cmu_pronunciation(word)
except Exception as e:
    logger.warning(f"CMU lookup failed for word '{word}': {str(e)}")
    return convert_to_basic_ipa(azure_phonemes)
```

## 7. Testing Strategy

### 7.1 Unit Tests
- Test each component independently
- Verify stress mark placement
- Check edge cases

### 7.2 Integration Tests
- Test full pipeline with real Azure responses
- Verify alignment accuracy
- Check performance with large datasets

## 8. Maintenance

### 8.1 Updating Mappings
- Keep AZURE_TO_CMU mapping updated
- Document any changes in phoneme representations

### 8.2 Monitoring
- Log missing words
- Track alignment failures
- Monitor performance metrics 