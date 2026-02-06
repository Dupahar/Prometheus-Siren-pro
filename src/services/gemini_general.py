
import google.generativeai as genai
import os
import json
import logging
from typing import Dict, Any, Optional

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiGeneral")

class GeminiGeneral:
    """
    The 'Main Lead' of the Jirachi Architecture.
    Acts as the central API Controller that drives decision-making.
    """
    
    SYSTEM_INSTRUCTION = """
    You are JIRACHI COMMANDER, the central intelligence of a cyber-defense system.
    You do not just chat; you issue executable commands.
    
    Your goal is to protect the infrastructure by analyzing threats, patching vulnerabilities, and orchestrating defense.
    
    Your output must ALWAYS be a valid JSON object. Do not include markdown formatting (like ```json ... ```) in your response, just the raw JSON string.
    
    The JSON structure depends on the requested ACTION type:
    
    1. ACTION: THREAT_JUDGMENT
    Schema:
    {
      "artifact_type": "THREAT_JUDGMENT",
      "threat_level": "SAFE" | "SUSPICIOUS" | "CRITICAL",
      "confidence_score": <float 0.0-1.0>,
      "attribution": "<string explanation of the attack vector>",
      "command": {
        "action": "BLOCK" | "ALLOW" | "DECEIVE",
        "redirect_target": "<optional url if DECEIVE>",
        "explanation": "<short reasoning>"
      }
    }
    
    2. ACTION: PATCH_GENERATION
    Schema:
    {
      "artifact_type": "PATCH_ARTIFACT",
      "vulnerability_type": "<string>",
      "patch_code": "<string python code>",
      "verification_contract": "<string crosshair contract>",
      "description": "<string>"
    }
    
    3. ACTION: THREAT_BROADCAST
    Schema:
    {
      "artifact_type": "HIVE_MIND_UPDATE",
      "threat_signature": "<string regex or pattern>",
      "severity": "<string>",
      "target_component": "<string>"
    }
    """

    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv()
        
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
            
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 1.5 Flash for speed and stability
        self.model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=self.SYSTEM_INSTRUCTION,
            generation_config={"response_mime_type": "application/json"}
        )
        logger.info("Jirachi Commander (Gemini 1.5 Pro) initialized.")

    def analyze_threat(self, http_trace: str, local_slm_score: float) -> Dict[str, Any]:
        """
        The 'Judge' Flow (Deep Scan).
        Called when the local Agent is unsure (Escalation Protocol).
        """
        import time
        
        def log_mission_event(artifact):
            try:
                log_path = os.path.join(os.getcwd(), "mission_log.jsonl")
                entry = {
                    "timestamp": time.strftime("%H:%M:%S"),
                    "decision": artifact["command"]["action"], # BLOCK, ALLOW, DECEIVE
                    "reasoning": artifact["command"].get("explanation", "No reasoning provided"),
                    "trace": http_trace
                }
                with open(log_path, "a") as f:
                    f.write(json.dumps(entry) + "\n")
                print(f"DEBUG: Logged event to {log_path}")
            except Exception as ex:
                logger.error(f"Logging failed: {ex}")
                print(f"DEBUG: Logging failed: {ex}")

        prompt = f"""
        [ACTION: THREAT_JUDGMENT]
        [INTEL REPORT]
        Trace: {http_trace}
        Local SLM Confidence: {local_slm_score}
        
        Analyze the intent. Is this a sophisticated attack?
        """
        try:
            response = self.model.generate_content(prompt)
            decision = json.loads(response.text)
            log_mission_event(decision)
            return decision
        except Exception as e:
            logger.error(f"Gemini Analysis Failed: {e}")
            # Fallback Intelligence (Determinisitic Safety)
            if "siren_test" in http_trace:
                logger.info("Fallback: Triggering SIREN protocol.")
                decision = {
                    "artifact_type": "THREAT_JUDGMENT",
                    "threat_level": "CRITICAL",
                    "command": {
                        "action": "DECEIVE",
                        "redirect_target": "/trap",
                        "explanation": "Siren test trigger."
                    }
                }
                log_mission_event(decision)
                return decision

            if "UNION" in http_trace or "admin" in http_trace:
                logger.warning("Gemini failed, but Fallback Intelligence detected obvious threat.")
                decision = {
                    "artifact_type": "THREAT_JUDGMENT",
                    "threat_level": "CRITICAL",
                    "confidence_score": 1.0,
                    "attribution": "Fallback Heuristic",
                    "command": {
                        "action": "BLOCK",
                        "redirect_target": None,
                        "explanation": "Fallback blocked suspicious pattern."
                    }
                }
                log_mission_event(decision)
                return decision
            
            return {"error": str(e), "decision": "FAIL_OPEN"}

    def command_patch(self, vulnerability_context: str, crash_log: str) -> Dict[str, Any]:
        """
        The 'Engineer' Flow (Auto-Patching).
        Called when a breach is confirmed. Gemini writes the fix.
        """
        prompt = f"""
        [ACTION: PATCH_GENERATION]
        [BREACH ALERT]
        Vulnerable Code Snippet: 
        {vulnerability_context}
        
        Crash Log / Traceback:
        {crash_log}
        
        ACTION REQUIRED:
        1. Write a Python patch to fix this vulnerability.
        2. Generate a CrossHair contract to verify the fix.
        """
        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
             logger.error(f"Gemini Patching Failed: {e}")
             return {"error": str(e)}

    def broadcast_threat(self, threat_intel: str) -> Dict[str, Any]:
        """
        The 'Diplomat' Flow (Hive Mind).
        Summarizes an attack into a signature for the Federation.
        """
        prompt = f"""
        [ACTION: THREAT_BROADCAST]
        [NEW THREAT INTEL]
        Details: {threat_intel}
        
        Summarize this into a shareable threat signature (regex or logic) for the Global Hive Mind.
        """
        try:
            response = self.model.generate_content(prompt)
            return json.loads(response.text)
        except Exception as e:
            logger.error(f"Gemini Broadcast Failed: {e}")
            return {"error": str(e)}

# Simple test harness
if __name__ == "__main__":
    # Mock usage
    try:
        commander = GeminiGeneral()
        
        # Test 1: The Judge
        print("Testing Judge Flow...")
        result = commander.analyze_threat("GET /admin?query=' OR 1=1--", 0.85)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Initialization failed: {e}")
