import os
import json
import time
from typing import List, Dict, Any, Optional

class KnowledgeStore:
    def __init__(self, storage_dir: Optional[str] = None):
        if not storage_dir:
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            backend_dir = os.path.dirname(app_dir)
            storage_dir = os.path.join(backend_dir, "data")
        
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.kb_file = os.path.join(self.storage_dir, "knowledge_base.json")
        self._ensure_kb_file()

    def _ensure_kb_file(self):
        if not os.path.exists(self.kb_file):
            with open(self.kb_file, "w", encoding="utf-8") as f:
                json.dump({"findings": []}, f, indent=2)

    def load_findings(self) -> List[Dict[str, Any]]:
        try:
            with open(self.kb_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("findings", [])
        except Exception:
            return []

    def save_finding(self, finding: Dict[str, Any]) -> bool:
        if not finding or not finding.get("finding"):
            return False
        
        findings = self.load_findings()
        query = finding.get("query", "").strip().lower()
        content = finding.get("finding", "").strip().lower()
        
        # Avoid exact duplicate entries
        for existing in findings:
            if existing.get("query", "").strip().lower() == query or existing.get("finding", "").strip().lower() == content:
                return False

        record = dict(finding)
        record["created_at"] = time.time()
        findings.append(record)

        try:
            with open(self.kb_file, "w", encoding="utf-8") as f:
                json.dump({"findings": findings}, f, indent=2)
            return True
        except Exception:
            return False

    def find_relevant(self, objective: str) -> Optional[Dict[str, Any]]:
        obj_lower = objective.lower()
        findings = self.load_findings()

        for item in reversed(findings):
            query = item.get("query", "").lower()
            finding_text = item.get("finding", "").lower()

            # Direct keyword matching for common technical topics (e.g. csv to json)
            if "csv" in obj_lower and "json" in obj_lower:
                if ("csv" in query or "csv" in finding_text) and ("json" in query or "json" in finding_text):
                    return item

            # Generic topic keyword matching
            query_words = [w for w in query.split() if len(w) > 3 and w not in ["python", "standard", "library", "using", "conversion", "script"]]
            if query_words and all(word in obj_lower for word in query_words):
                return item

        return None

    def clear(self):
        """Clears all persistent findings (for clean testing)."""
        with open(self.kb_file, "w", encoding="utf-8") as f:
            json.dump({"findings": []}, f, indent=2)

_knowledge_store_instance = None

def get_knowledge_store() -> KnowledgeStore:
    global _knowledge_store_instance
    if _knowledge_store_instance is None:
        _knowledge_store_instance = KnowledgeStore()
    return _knowledge_store_instance
