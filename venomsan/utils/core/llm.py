"""Local AI Engine - Analyzes WAF responses and suggests bypass techniques."""
import json, re
from pathlib import Path
from typing import Optional
from ..utils.helpers import status

class LocalLLM:
    """Local AI for WAF bypass analysis."""

    WAF_KNOWLEDGE = {
        "Cloudflare": {
            "signatures": ["cf-ray","cloudflare","__cfduid"],
            "bypass": [
                "Use TLS/JA3 spoofing (Chrome fingerprint)",
                "Rotate IP via proxies",
                "Add realistic browser headers",
                "Solve JavaScript challenge",
            ],
        },
        "ModSecurity": {
            "signatures": ["mod_security","ModSecurity","modsecurity"],
            "bypass": [
                "Use HTTP request smuggling",
                "Polymorphic payload encoding",
                "Null byte injection",
                "Comment obfuscation (/**/)",
                "Parameter pollution",
            ],
        },
        "AWS WAF": {
            "signatures": ["x-amzn-requestid","AWS","awselb"],
            "bypass": [
                "Oversized header values",
                "URL encoding variations",
                "Case manipulation",
            ],
        },
        "Akamai": {
            "signatures": ["akamai","x-akamai"],
            "bypass": [
                "TE.CL smuggling",
                "Header obfuscation",
                "Slow rate attacks",
            ],
        },
    }

    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.enabled = False
        self.llm = None

    async def initialize(self) -> bool:
        """Try to load local LLM."""
        if self.model_path and Path(self.model_path).exists():
            try:
                from llama_cpp import Llama
                self.llm = Llama(model_path=self.model_path, n_ctx=2048, n_threads=4, verbose=False)
                self.enabled = True
                status("Local LLM loaded successfully", "success")
                return True
            except ImportError:
                status("llama-cpp-python not installed", "warning")
            except Exception as e:
                status(f"LLM init failed: {e}", "warning")
        else:
            status("No LLM model found, using rule-based analysis", "info")
        return False

    def analyze_waf_error(self, error_msg: str, headers: dict, attack_type: str) -> dict:
        """Analyze WAF error and suggest bypass."""
        # Rule-based detection first
        waf_name = "unknown"
        bypass_suggestions = []
        error_lower = error_msg.lower()

        for waf, info in self.WAF_KNOWLEDGE.items():
            for sig in info["signatures"]:
                if sig.lower() in error_lower or sig.lower() in str(headers).lower():
                    waf_name = waf
                    bypass_suggestions = info["bypass"]
                    break
            if waf_name != "unknown":
                break

        # Generic analysis
        if "403" in error_msg:
            bypass_suggestions.append("Try IP rotation via proxy")
            bypass_suggestions.append("Add random delays between requests")
        if "406" in error_msg:
            bypass_suggestions.append("Modify Content-Type header")
            bypass_suggestions.append("Change User-Agent")
        if "429" in error_msg:
            bypass_suggestions.append("Reduce request rate significantly")
            bypass_suggestions.append("Use exponential backoff")

        result = {
            "waf_type": waf_name,
            "attack_type": attack_type,
            "error_preview": error_msg[:200],
            "bypass_suggestions": bypass_suggestions or ["Use multi-layer encoding"],
            "confidence": "high" if waf_name != "unknown" else "low",
        }

        # LLM enhancement if available
        if self.enabled and self.llm:
            try:
                prompt = f"Analyze this WAF error for {attack_type} attack. Error: {error_msg[:500]}. Headers: {json.dumps(headers)}. Suggest bypass techniques."
                response = self.llm(prompt, max_tokens=256, temperature=0.1)
                text = response["choices"][0]["text"]
                result["llm_analysis"] = text.strip()
                result["confidence"] = "high"
            except: pass

        return result

    def suggest_payload_modification(self, original_payload: str, waf_type: str) -> str:
        """Suggest payload modifications for specific WAF."""
        if waf_type == "Cloudflare":
            from urllib.parse import quote
            return quote(quote(original_payload))
        elif waf_type == "ModSecurity":
            return original_payload.replace(" ", "/**/")
        elif waf_type == "AWS WAF":
            return original_payload.replace(" ", "\t")
        else:
            # Default: base64 + URL encoding
            import base64
            from urllib.parse import quote
            return quote(base64.b64encode(original_payload.encode()).decode())
