import cmudict
import os
import logging
import azure.cognitiveservices.speech as speechsdk
# Import configuration from your config module (same as original)
from app.core.config import OPENAI_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, OPENAI_API_URL
import json

#What it recieves from webhoook

wav_path = "/var/folders/8j/7q9j9_8j78v7py905kp0c3ch0000gn/T/tmp9sxfn969.wav"
transcript = "I bought a ticket to Costa Rica. Costa Rica is something me and my friends have planning a place of planning to visit. It is a country that is beautiful, exciting and very fun for our, for us. We are a group of 20 year olds just entering our senior year of college. I think this is a good celebratory trip to experience a new country and, and grow a better bond between friends. I think it'll be really fun. Our first itinerary is um, uh, La Fortuna, which is a, ah, jungle resort in Costa Rica. I bought it two months ago around um, May. And my next itinerary is after La Fortuna we go to Monteverde, which is labeled as Cloud City. The reason it's called Cloud City is because there's a lot of clouds going through the city. Then after that we go to a beach city. Not sure what the name is, but it's a very beautiful beach city and we will spend a lot of time on the beach, surfing, swimming, hanging out with the locals, stuff like that. After that we go back to San Jose. San Jose is the capital of Costa Rica and is it is the city. Then from San Jose we will fly back to Los Angeles. In Los Angeles we will have our parents probably pick us up and we're only in Costa rica for about 15 days. But throughout those 15 days me and my friends will still be doing work because we work remotely. I'm very excited about this trip because this is something that's really fun. I'm not sure what I can talk about next because I've been talking about this for some time now. I'm really excited to go on this trip. It is next Tuesday, that is July 1st. We're going to leave for the airport at 12:00pm."
session_id = "sdfsdfnsdf"


#this gives the correct pronuncaiton of the word and the stress marks but we only get the stress marks




class PronunciationService:
    
    def __init__(self):
        self.cmu = cmudict.dict()

        # Configuration from environment variables (same as original)
        self.speech_key = AZURE_SPEECH_KEY
        self.region = AZURE_SPEECH_REGION
        self.openai_api_key = OPENAI_API_KEY
        self.openai_url = OPENAI_API_URL

        #there could be variants, this gets the first pronunciaton of the word
        # print(f"'hello': {cmu.get('hello')[0]}")
        #'hello': ['HH', 'AH0', 'L', 'OW1']

        #Now we set up mapping between azure and cmu
        #Azure is what the user said and cmu is what they actually said
        #we are mapping them bc azure is lowercase and cmu is uppercase and numbers
        #we later combine the stresss marks to what they actually said
        self.azure_to_cmu = {
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

        #Stress marks symbols
        #There is a 0 stress but that means weak or no stress for that phoneme, no visual for that too
        # Stress mark symbols
        self.stress_marks = {
            "1": "ˈ",  # Primary stress
            "2": "ˌ"   # Secondary stress
        }

        #Azure to IPA Mapping:
        # Azure phoneme to IPA mapping
        self.azure_to_ipa = {
            # Vowels
            "ax": "ə",  # schwa
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
            "er": "ɜr",  # NURSE vowel
            # Consonants
            "dh": "ð",   # voiced th
            "th": "θ",   # voiceless th
            "sh": "ʃ",   # SHIP consonant
            "zh": "ʒ",   # MEASURE consonant
            "ch": "tʃ",  # CHIP consonant
            "jh": "dʒ",  # JUDGE consonant
            "ng": "ŋ",   # SING consonant
            # Keep single letters as is
            "p": "p", "b": "b", "t": "t", "d": "d", "k": "k", "g": "g",
            "f": "f", "v": "v", "s": "s", "z": "z", "h": "h",
            "m": "m", "n": "n", "l": "l", "r": "r", "w": "w", "y": "j"
        }
        
    def azure_analysis(self, audio_file: str, reference_text: str):
        try:
            # Check if audio file exists
            if not os.path.exists(audio_file):
                print(f"Audio file not found for Pronunciation: {audio_file}")
                logging.warning(f"Audio file not found for Pronunciation: {audio_file}")
                return None
            
            # Get audio file duration and transcript stats
            word_count = len(reference_text.split())
            char_count = len(reference_text)
            
            # Choose analysis method based on transcript length
            if word_count > 60:  # Long transcript - use chunking
                return self._azure_chunked_analysis(audio_file, reference_text)
            elif word_count > 15:  # Medium transcript - use extended timeout
                return self._azure_streaming_analysis(audio_file, reference_text)
            else:
                result = self._azure_standard_analysis(audio_file, reference_text)
                
                # If standard fails, try extended as backup
                if result is None:
                    return self._azure_streaming_analysis(audio_file, reference_text)
                
                return result
                
        except Exception as e:
            print(f"❌ Error in azure_analysis: {str(e)}")
            return None
    
    def _azure_standard_analysis(self, audio_file: str, reference_text: str):
        """Original recognize_once implementation for short transcripts"""
        try:
            # Set up Azure Speech config using instance variables
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, 
                region=self.region
            )
            
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            
            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            pron_config.apply_to(recognizer)
            result = recognizer.recognize_once()
            
            #Handle results
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                
                if json_result:
                    raw_analysis = json.loads(json_result)
                    print("✅ Standard analysis completed")
                    return raw_analysis
                else:
                    print("❌ No pronunciation data returned")
                    return None
            
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("❌ No speech recognized")
                return None
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                print(f"❌ Recognition canceled: {result.cancellation_details.reason}")
                return None
            
        except Exception as e:
            print(f"❌ Error in standard analysis: {str(e)}")
            return None
    
    def _azure_streaming_analysis(self, audio_file: str, reference_text: str):
        """Extended recognition implementation for long transcripts using recognize_once with extended timeout"""
        try:
            # Set up Azure Speech config
            speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key, 
                region=self.region
            )
            
            # Configure for longer audio processing
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "30000")  # 30 seconds
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "30000")    # 30 seconds
            speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "2000")             # 2 seconds between words
            
            # Enable detailed results for better analysis
            speech_config.request_word_level_timestamps()
            
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            
            # Configure pronunciation assessment
            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config
            )
            
            pron_config.apply_to(recognizer)
            
            print(f"🎤 Starting extended pronunciation assessment...")
            print(f"📝 Reference text length: {len(reference_text)} characters")
            print(f"🔤 Reference word count: {len(reference_text.split())} words")
            print(f"⚙️ Using recognize_once with extended timeouts for long audio")
            
            # Use recognize_once (not continuous recognition) for pronunciation assessment
            result = recognizer.recognize_once()
            
            # Handle results
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                
                if json_result:
                    raw_analysis = json.loads(json_result)
                    print("✅ Extended pronunciation analysis completed")
                    print(f"📊 Recognized text: {result.text[:100]}...")
                    return raw_analysis
                else:
                    print("❌ No pronunciation data returned")
                    return None
            
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print(f"❌ No speech recognized: {result.no_match_details.reason}")
                return None
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                print(f"❌ Recognition canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    print(f"❌ Error details: {cancellation.error_details}")
                return None
                
        except Exception as e:
            print(f"❌ Error in streaming analysis: {str(e)}")
            return None
    
    def _azure_chunked_analysis(self, audio_file: str, reference_text: str):
        """Chunked pronunciation analysis for long transcripts"""
        try:
            import subprocess
            import tempfile
            import os
            
            print(f"🔀 Starting chunked pronunciation analysis...")
            print(f"📝 Reference text length: {len(reference_text)} characters")
            print(f"🔤 Reference word count: {len(reference_text.split())} words")
            
            # Split reference text into chunks (roughly 30-50 words each)
            words = reference_text.split()
            chunk_size = 40  # words per chunk
            text_chunks = []
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                text_chunks.append({
                    "text": chunk_text,
                    "start_word": i,
                    "end_word": min(i + chunk_size, len(words)),
                    "word_count": len(chunk_words)
                })
            
            print(f"📊 Split into {len(text_chunks)} chunks")
            
            # Get audio duration to calculate chunk timings
            try:
                # Use ffprobe to get audio duration
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                       '-of', 'csv=p=0', audio_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                total_duration = float(result.stdout.strip())
                print(f"🕒 Total audio duration: {total_duration:.1f} seconds")
            except Exception as e:
                print(f"⚠️ Could not get audio duration: {e}, using estimated timing")
                total_duration = len(words) * 0.6  # Estimate ~0.6 seconds per word
            
            # Calculate time per chunk
            chunk_duration = total_duration / len(text_chunks)
            
            # Process each chunk
            all_results = []
            combined_words = []
            cumulative_offset = 0
            
            for i, chunk in enumerate(text_chunks):
                print(f"\n🔄 Processing chunk {i+1}/{len(text_chunks)}: {chunk['word_count']} words")
                print(f"   Text preview: {chunk['text'][:60]}...")
                
                # Calculate time range for this chunk
                start_time = i * chunk_duration
                
                # Create temporary audio chunk
                temp_chunk_file = None
                try:
                    # Extract audio chunk using ffmpeg
                    temp_chunk_file = tempfile.mktemp(suffix='.wav')
                    cmd = [
                        'ffmpeg', '-y', '-i', audio_file,
                        '-ss', str(start_time), '-t', str(chunk_duration),
                        '-c', 'copy', temp_chunk_file
                    ]
                    
                    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if result.returncode != 0:
                        print(f"   ⚠️ Failed to extract audio chunk {i+1}")
                        continue
                    
                    # Process this chunk with pronunciation assessment
                    chunk_result = self._azure_standard_analysis(temp_chunk_file, chunk['text'])
                    
                    if chunk_result:
                        print(f"   ✅ Chunk {i+1} processed successfully")
                        
                        # Extract words and adjust their timestamps
                        if "NBest" in chunk_result and chunk_result["NBest"]:
                            chunk_words = chunk_result["NBest"][0].get("Words", [])
                            
                            for word_data in chunk_words:
                                # Adjust timestamps to account for chunk offset
                                word_data["Offset"] = word_data.get("Offset", 0) + int(start_time * 10000000)
                                combined_words.append(word_data)
                        
                        all_results.append(chunk_result)
                        cumulative_offset += int(chunk_duration * 10000000)  # Convert to 100-nanosecond units
                    else:
                        print(f"   ❌ Chunk {i+1} failed to process")
                
                finally:
                    # Clean up temporary file
                    if temp_chunk_file and os.path.exists(temp_chunk_file):
                        try:
                            os.unlink(temp_chunk_file)
                        except:
                            pass
            
            # Combine results
            if all_results:
                print(f"\n🔗 Combining {len(all_results)} chunk results...")
                
                # Calculate overall scores (average of chunk scores)
                total_pron_score = 0
                total_accuracy_score = 0
                total_fluency_score = 0
                valid_chunks = 0
                
                for chunk_result in all_results:
                    if "NBest" in chunk_result and chunk_result["NBest"]:
                        assessment = chunk_result["NBest"][0].get("PronunciationAssessment", {})
                        total_pron_score += assessment.get("PronScore", 0)
                        total_accuracy_score += assessment.get("AccuracyScore", 0)
                        total_fluency_score += assessment.get("FluencyScore", 0)
                        valid_chunks += 1
                
                if valid_chunks > 0:
                    avg_pron_score = total_pron_score / valid_chunks
                    avg_accuracy_score = total_accuracy_score / valid_chunks
                    avg_fluency_score = total_fluency_score / valid_chunks
                else:
                    avg_pron_score = avg_accuracy_score = avg_fluency_score = 0
                
                # Create combined result
                combined_result = {
                    "Duration": int(total_duration * 10000000),  # Convert to 100-nanosecond units
                    "DisplayText": " ".join([chunk["text"] for chunk in text_chunks]),
                    "NBest": [{
                        "PronunciationAssessment": {
                            "PronScore": avg_pron_score,
                            "AccuracyScore": avg_accuracy_score,
                            "FluencyScore": avg_fluency_score,
                            "CompletenessScore": 100  # Assume complete
                        },
                        "Words": combined_words
                    }]
                }
                
                print(f"✅ Chunked analysis completed!")
                print(f"📊 Combined scores - Pronunciation: {avg_pron_score:.1f}, Accuracy: {avg_accuracy_score:.1f}, Fluency: {avg_fluency_score:.1f}")
                print(f"📝 Total words processed: {len(combined_words)}")
                
                return combined_result
            else:
                print("❌ No chunks processed successfully")
                return None
                
        except Exception as e:
            print(f"❌ Error in chunked analysis: {str(e)}")
            return None
                
    
    def process_azure_data(self, raw_data):
        
        #Extract overall scores
        nbest = raw_data.get("NBest", [])
        if not nbest:
            return None
        
        best_result = nbest[0]
        
        # Overall pronunciation assessment scores
        pron_assessment = best_result.get("PronunciationAssessment", {})
        overall_score = pron_assessment.get("PronScore", 0)
        accuracy_score = pron_assessment.get("AccuracyScore", 0)
        fluency_score = pron_assessment.get("FluencyScore", 0)
        
        print(f"📊 Overall Pronunciation Score: {overall_score}/100")
        
        
        
        #Extract word level data - Fixed: "Words" should be capitalized
        words = best_result.get("Words", [])
        words_result = []
        
        for word in words:
            word_text = word.get("Word", "")
            word_assessment = word.get("PronunciationAssessment", {})
            word_score = word_assessment.get("AccuracyScore", 0)
            error_type = word_assessment.get("ErrorType", "None")
            
            #Extract phoneme-level data - Fixed: moved inside the word loop
            phonemes = word.get("Phonemes", [])
            phoneme_results = []
            
            for phoneme in phonemes:
                phoneme_text = phoneme.get("Phoneme", "")
                phoneme_assessment = phoneme.get("PronunciationAssessment", {})
                phoneme_score = phoneme_assessment.get("AccuracyScore", 0)
                
                ipa_phoneme = self.convert_to_ipa(phoneme_text)
                
                phoneme_results.append({
                    "azure_phoneme": phoneme_text,
                    "ipa_phoneme": ipa_phoneme,
                    "score": phoneme_score
                })
            
            stress_pattern = self.get_stress(word_text)
            
            words_result.append({
                "word": word_text,
                "score": word_score,
                "error_type": error_type,
                "phonemes": phoneme_results,
                "stress_pattern": stress_pattern
            })
        
        return {
            "overall_score": overall_score,
            "accuracy_score": accuracy_score,
            "fluency_score": fluency_score,
            "words": words_result
        }
                
    
    def get_stress(self, word: str):
        word = word.lower()
        if word in self.cmu:
            return self.cmu[word][0]
        return []
    
    def convert_to_ipa(self, phoneme: str):
        #fallback is original phoneme with no ipa
        return self.azure_to_ipa.get(phoneme, phoneme)


if __name__ == "__main__":
    import datetime
    
    # Initialize output capture
    final_output = {
        "test_session": {
            "timestamp": datetime.datetime.now().isoformat(),
            "session_id": session_id,
            "test_results": []
        },
        "webhook_data": {},
        "azure_analysis": {},
        "processing_results": {},
        "word_analysis": [],
        "summary": {}
    }
    
    def add_output(section, message, data=None):
        """Helper function to add output to final JSON"""
        entry = {
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if data is not None:
            entry["data"] = data
        
        final_output["test_session"]["test_results"].append({
            "section": section,
            "entry": entry
        })
        print(message)  # Still print to console
    
    add_output("header", "🎯 Testing Pronunciation Service")
    add_output("header", "-" * 40)
    
    # Initialize the service
    service = PronunciationService()
    add_output("initialization", "✅ PronunciationService initialized successfully")
    
    # Capture webhook data
    final_output["webhook_data"] = {
        "wav_path": wav_path,
        "transcript": transcript,
        "session_id": session_id,
        "file_exists": os.path.exists(wav_path) if wav_path != "d" else False,
        "file_size_bytes": os.path.getsize(wav_path) if wav_path != "d" and os.path.exists(wav_path) else 0
    }
    
    add_output("webhook_data", f"\n📡 Your webhook data:")
    add_output("webhook_data", f"  wav_path: {wav_path}")
    add_output("webhook_data", f"  transcript: {transcript}")
    add_output("webhook_data", f"  session_id: {session_id}")
    
    # Test with YOUR data
    add_output("azure_analysis", f"\n🎤 Testing Azure analysis with your data:")
    
    if wav_path != "d" and os.path.exists(wav_path):
        add_output("azure_analysis", f"  Analyzing audio: {wav_path}")
        add_output("azure_analysis", f"  Expected transcript: '{transcript}'")
        
        try:
            raw_result = service.azure_analysis(wav_path, transcript)
            
            if raw_result:
                final_output["azure_analysis"] = {
                    "status": "success",
                    "raw_data": raw_result
                }
                add_output("azure_analysis", "✅ Azure analysis successful!")
                
                processed = service.process_azure_data(raw_result)
                if processed:
                    final_output["processing_results"] = {
                        "status": "success",
                        "overall_score": processed['overall_score'],
                        "accuracy_score": processed['accuracy_score'],
                        "fluency_score": processed['fluency_score'],
                        "total_words": len(processed['words'])
                    }
                    
                    add_output("processing", "✅ Data processing successful!")
                    add_output("processing", f"  Overall score: {processed['overall_score']}")
                    add_output("processing", f"  Accuracy score: {processed['accuracy_score']}")
                    add_output("processing", f"  Fluency score: {processed['fluency_score']}")
                    add_output("processing", f"  Words analyzed: {len(processed['words'])}")
                    
                    # Capture word analysis
                    word_analysis_output = []
                    add_output("word_analysis", f"\n📝 Word-by-word analysis:")
                    
                    for i, word_data in enumerate(processed['words']):
                        word_entry = {
                            "word_number": i + 1,
                            "word": word_data['word'],
                            "score": word_data['score'],
                            "stress_pattern": word_data['stress_pattern'],
                            "error_type": word_data['error_type'],
                            "phonemes": []
                        }
                        
                        word_message = f"    Word {i+1}: '{word_data['word']}' - Score: {word_data['score']} - Stress: {word_data['stress_pattern']}"
                        add_output("word_analysis", word_message)
                        
                        # Capture phoneme details
                        for phoneme_data in word_data['phonemes']:
                            phoneme_entry = {
                                "azure_phoneme": phoneme_data['azure_phoneme'],
                                "ipa_phoneme": phoneme_data['ipa_phoneme'],
                                "score": phoneme_data['score']
                            }
                            word_entry["phonemes"].append(phoneme_entry)
                            
                            phoneme_message = f"      Phoneme: {phoneme_data['azure_phoneme']} -> {phoneme_data['ipa_phoneme']} (Score: {phoneme_data['score']})"
                            add_output("word_analysis", phoneme_message)
                        
                        word_analysis_output.append(word_entry)
                    
                    final_output["word_analysis"] = word_analysis_output
                    
                    # Calculate summary statistics
                    word_scores = [w['score'] for w in processed['words']]
                    phoneme_scores = []
                    for w in processed['words']:
                        for p in w['phonemes']:
                            phoneme_scores.append(p['score'])
                    
                    final_output["summary"] = {
                        "total_words": len(processed['words']),
                        "total_phonemes": len(phoneme_scores),
                        "average_word_score": sum(word_scores) / len(word_scores) if word_scores else 0,
                        "average_phoneme_score": sum(phoneme_scores) / len(phoneme_scores) if phoneme_scores else 0,
                        "words_below_70": len([s for s in word_scores if s < 70]),
                        "words_below_50": len([s for s in word_scores if s < 50]),
                        "phonemes_below_70": len([s for s in phoneme_scores if s < 70]),
                        "lowest_word_score": min(word_scores) if word_scores else 0,
                        "highest_word_score": max(word_scores) if word_scores else 0
                    }
                    
                else:
                    final_output["processing_results"] = {"status": "failed", "error": "Data processing failed"}
                    add_output("processing", "❌ Data processing failed")
            else:
                final_output["azure_analysis"] = {"status": "failed", "error": "Azure analysis returned no results"}
                add_output("azure_analysis", "❌ Azure analysis failed - check your audio file and Azure credentials")
                
        except Exception as e:
            final_output["azure_analysis"] = {"status": "error", "error": str(e)}
            add_output("azure_analysis", f"❌ Azure analysis error: {str(e)}")
    
    else:
        final_output["azure_analysis"] = {"status": "skipped", "reason": f"Audio file not found: {wav_path}"}
        add_output("azure_analysis", f"  ⚠️  Audio file not found: {wav_path}")
        add_output("azure_analysis", "  Update wav_path to point to a real .wav file")
        
        # Quick test of other functions with your transcript
        add_output("fallback_test", f"\n🔤 Testing functions with sample text:")
        sample_words = ["reliable", "information", "government", "trustworthy"]
        test_results = {}
        
        for word in sample_words:
            stress = service.get_stress(word)
            test_results[word] = {
                "stress_pattern": stress,
                "cmu_found": word.lower() in service.cmu
            }
            add_output("fallback_test", f"  Stress pattern for '{word}': {stress}")
        
        final_output["fallback_test_results"] = test_results
    
    add_output("completion", "\n✨ Testing complete!")
    
    # Save everything to final JSON
    final_filename = f"pronunciation_final_output_{session_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(final_filename, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        add_output("save_results", f"✅ Complete results saved to {final_filename}")
        
        # Also save a simplified version with just the console output
        console_output = {
            "session_info": {
                "timestamp": final_output["test_session"]["timestamp"],
                "session_id": session_id,
                "wav_path": wav_path,
                "transcript": transcript
            },
            "console_output": [entry["entry"]["message"] for entry in final_output["test_session"]["test_results"]],
            "raw_data": final_output
        }
        
        console_filename = f"pronunciation_console_output_{session_id}.json"
        with open(console_filename, 'w', encoding='utf-8') as f:
            json.dump(console_output, f, indent=2, ensure_ascii=False)
        add_output("save_results", f"✅ Console output saved to {console_filename}")
        
    except Exception as e:
        add_output("save_results", f"❌ Failed to save results: {str(e)}")
    
    print(f"\n📁 Files created:")
    print(f"  - Complete analysis: {final_filename}")
    print(f"  - Console output: {console_filename}")