
import json
import time
import random
from datetime import datetime

# Cyberpunk / Security Phrases
ATTACKS = [
    ("BLOCK", "SQL Injection blocked by Qdrant pattern match", "SELECT * FROM users WHERE '1'='1'"),
    ("DECEIVE", "Redirected to Siren Honeypot (Port 2222)", "ssh root@10.0.0.5"),
    ("ALLOW", "Authorized API Request", "GET /api/v1/status"),
    ("PATCH", "Auto-Patch deployed to src/auth.py", "Vulnerability: CWE-89"),
    ("BLOCK", "XSS Payload neutralized", "<script>alert(1)</script>"),
    ("DECEIVE", "Sandbox Session Created #9921", "curl -X POST /admin/login"),
    ("BLOCK", "RCE Attempt stopped by Gemini", "os.system('rm -rf /')"),
]

def generate_traffic():
    print("🔥 JIRACHI TRAFFIC GENERATOR ACTIVE 🔥")
    print("Injecting synthetic logs into 'mission_log.jsonl'...")
    
    while True:
        try:
            decision, reason, trace = random.choice(ATTACKS)
            
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "decision": decision,
                "reasoning": reason,
                "trace": trace,
                "confidence": round(random.uniform(0.85, 0.99), 2)
            }
            
            with open("mission_log.jsonl", "a") as f:
                f.write(json.dumps(entry) + "\n")
            
            print(f"[{entry['timestamp']}] {decision}: {reason[:40]}...")
            
            # Random burst delay
            time.sleep(random.uniform(0.5, 2.0))
            
        except KeyboardInterrupt:
            print("\nGenerator Stopped.")
            break

if __name__ == "__main__":
    generate_traffic()
