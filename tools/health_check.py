# tools/health_check.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class HealthCheck:
    """
    Performs a post-run health check on the audiobook pipeline.
    """

    def __init__(self, pipeline_json_path: str, file_id: str):
        self.pipeline_json_path = Path(pipeline_json_path)
        self.file_id = file_id
        self.pipeline_data: Dict[str, Any] = {}
        self.issues: List[str] = []
        self.report: Dict[str, Any] = {}

    def _load_data(self) -> bool:
        """Loads the pipeline.json file."""
        try:
            if self.pipeline_json_path.exists():
                with self.pipeline_json_path.open("r", encoding="utf-8") as f:
                    self.pipeline_data = json.load(f)
                return True
            else:
                self.issues.append("pipeline.json not found. Cannot perform health check.")
                return False
        except Exception as e:
            self.issues.append(f"Error loading pipeline.json: {e}")
            return False

    def verify_audiobook_integrity(self):
        """Placeholder for verifying the final audiobook file."""
        logger.info("Verifying audiobook integrity...")
        # In a real implementation, we would use ffprobe or similar
        # to check if the file is a valid media file.
        phase5_data = self.pipeline_data.get("phase5", {})
        files = phase5_data.get("files", {})
        file_entry = files.get(self.file_id, {})
        output_file = file_entry.get("output_file")
        
        if not output_file:
            self.issues.append("Final audiobook file is not listed in pipeline.json.")
        elif not Path(output_file).exists():
            self.issues.append(f"Final audiobook file not found at path: {output_file}")

    def check_for_missing_artifacts(self):
        """Placeholder for checking for missing artifacts."""
        logger.info("Checking for missing artifacts...")
        # In a real implementation, we would iterate through all phases
        # and check if the files listed in `artifacts` exist.
        pass

    def analyze_pipeline_state(self):
        """Placeholder for analyzing the pipeline state for anomalies."""
        logger.info("Analyzing pipeline state...")
        # In a real implementation, we would look for inconsistencies,
        # e.g., a phase marked as "success" with no output files.
        pass

    def generate_health_report(self) -> Dict[str, Any]:
        """Generates a health report."""
        self.report = {
            "file_id": self.file_id,
            "pipeline_json_path": str(self.pipeline_json_path),
            "status": "healthy" if not self.issues else "unhealthy",
            "issues_found": len(self.issues),
            "issues": self.issues,
        }
        return self.report

    def run(self) -> Dict[str, Any]:
        """Runs all health checks."""
        logger.info(f"Starting health check for '{self.file_id}'...")
        if not self._load_data():
            return self.generate_health_report()

        self.verify_audiobook_integrity()
        self.check_for_missing_artifacts()
        self.analyze_pipeline_state()
        
        report = self.generate_health_report()
        logger.info(f"Health check complete. Status: {report['status']}")
        return report

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline Health Check Tool")
    parser.add_argument("--pipeline_json", required=True, help="Path to pipeline.json")
    parser.add_argument("--file_id", required=True, help="File ID of the book to check")
    args = parser.parse_args()

    health_checker = HealthCheck(args.pipeline_json, args.file_id)
    report = health_checker.run()

    print("\n--- Health Check Report ---")
    print(json.dumps(report, indent=2))
    print("---------------------------")
