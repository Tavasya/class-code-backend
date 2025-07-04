#!/usr/bin/env python3
"""
View vocabulary debug logs in real-time
"""
import sys
import time
import os

def tail_vocab_log(follow=False):
    log_file = "/tmp/vocabulary_debug.log"
    
    if not os.path.exists(log_file):
        print("❌ No vocabulary debug log found at /tmp/vocabulary_debug.log")
        print("Run a submission test first to generate vocabulary logs.")
        return
    
    try:
        with open(log_file, 'r') as f:
            # Read all existing content
            content = f.read()
            if content:
                print(content)
            
            if follow:
                print("\n📊 Following vocabulary log (Ctrl+C to stop)...")
                # Follow mode - watch for new content
                while True:
                    line = f.readline()
                    if line:
                        print(line.rstrip())
                    else:
                        time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n✅ Stopped following log")
    except Exception as e:
        print(f"❌ Error reading log: {e}")

if __name__ == "__main__":
    follow = len(sys.argv) > 1 and sys.argv[1] == "-f"
    tail_vocab_log(follow)