# agents/predictive_failure_agent.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class PredictiveFailureAgent:
    """
    Analyzes the pipeline state before a run to predict potential failures.
    """

    def __init__(self, pipeline_json_path: str, file_id: str):
        self.pipeline_json_path = Path(pipeline_json_path)
        self.file_id = file_id
        self.pipeline_data: Dict[str, Any] = {}
        self.production_bible: Dict[str, Any] = {}
        self.warnings: List[str] = []
        self.recommendations: List[str] = []

    def _load_data(self) -> bool:
        """Loads the pipeline.json and production_bible.json files."""
        try:
            if self.pipeline_json_path.exists():
                with self.pipeline_json_path.open("r", encoding="utf-8") as f:
                    self.pipeline_data = json.load(f)
            else:
                self.warnings.append("pipeline.json not found. Cannot perform analysis.")
                return False

            book_dir = self.pipeline_json_path.parent / ".pipeline" / "books" / self.file_id
            bible_path = book_dir / "production_bible.json"
            if bible_path.exists():
                with bible_path.open("r", encoding="utf-8") as f:
                    self.production_bible = json.load(f)
            else:
                self.warnings.append("production_bible.json not found. Analysis will be limited.")
            
            return True
        except Exception as e:
            self.warnings.append(f"Error loading data: {e}")
            return False

    def _analyze_chunk_length(self):
        """Analyzes chunk lengths for potential issues."""
        phase3_data = self.pipeline_data.get("phase3", {})
        files = phase3_data.get("files", {})
        file_entry = files.get(self.file_id, {})
        chunk_paths = file_entry.get("chunk_paths", [])
        
        # This is a placeholder for a more sophisticated check against engine capabilities
        long_chunk_threshold = 3000 # characters

        for i, chunk_path_str in enumerate(chunk_paths):
            try:
                chunk_path = Path(chunk_path_str)
                if not chunk_path.is_absolute():
                    chunk_path = self.pipeline_json_path.parent / chunk_path
                
                if chunk_path.exists():
                    text = chunk_path.read_text(encoding="utf-8")
                    if len(text) > long_chunk_threshold:
                        self.warnings.append(f"Chunk {i} is very long ({len(text)} chars) and may cause TTS to fail.")
                        self.recommendations.append(f"Consider re-chunking with a smaller max chunk size.")
            except Exception as e:
                self.warnings.append(f"Could not analyze chunk {i} at {chunk_path_str}: {e}")

    def _analyze_casting(self):
        """Analyzes character casting for completeness."""
        if not self.production_bible:
            return

        casting_guide = self.production_bible.get("casting_guide", {})
        characters_in_bible = set(casting_guide.keys())

        # This is a placeholder. In a real scenario, we'd get characters from phase 3 data.
        characters_in_script = set() # e.g., {"narrator", "gandalf", "frodo"} 
        
        uncast_characters = characters_in_script - characters_in_bible
        if uncast_characters:
            self.warnings.append(f"The following characters are in the script but not in the casting guide: {', '.join(uncast_characters)}")
            self.recommendations.append("Update the production_bible.json with voice assignments for these characters.")


    def analyze(self) -> Dict[str, List[str]]:
        """
        Runs all analysis steps and returns a summary of potential issues.
        """
        if not self._load_data():
            return {"warnings": self.warnings, "recommendations": self.recommendations}

        logger.info(f"Running predictive failure analysis for '{self.file_id}'...")
        
        self._analyze_chunk_length()
        self._analyze_casting()

        logger.info(f"Analysis complete. Found {len(self.warnings)} potential issues.")

        return {"warnings": self.warnings, "recommendations": self.recommendations}

if __name__ == '__main__':
    # Example usage:
    # python -m agents.predictive_failure_agent --pipeline_json ../pipeline.json --file_id my_book
    import argparse

    parser = argparse.ArgumentParser(description="Predictive Failure Analysis Agent")
    parser.add_argument("--pipeline_json", required=True, help="Path to pipeline.json")
    parser.add_argument("--file_id", required=True, help="File ID of the book to analyze")
    args = parser.parse_args()

    agent = PredictiveFailureAgent(args.pipeline_json, args.file_id)
    results = agent.analyze()

    print("\n--- Predictive Failure Analysis Results ---")
    if results["warnings"]:
        print("\n[Warnings]")
        for warning in results["warnings"]:
            print(f"- {warning}")
    else:
        print("\nNo warnings.")

    if results["recommendations"]:
        print("\n[Recommendations]")
        for rec in results["recommendations"]:
            print(f"- {rec}")
    else:
        print("\nNo recommendations.")
    print("\n-------------------------------------------")
