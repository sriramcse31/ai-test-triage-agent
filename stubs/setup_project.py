#!/usr/bin/env python3
"""
Run this script to create the complete project structure
Usage: python setup_project.py
"""

import os
from pathlib import Path

def create_project_structure():
    """Creates the complete project directory structure"""
    
    structure = {
        "ai-test-triage-agent": {
            "agent": ["__init__.py", "planner.py", "tools.py", "memory.py"],
            "ingestion": ["__init__.py", "log_parser.py", "artifact_processor.py"],
            "evals": ["__init__.py", "golden_cases.json", "eval_runner.py"],
            "demo": {
                "sample_ci_failures": ["test_login_timeout.log", "test_selector_changed.log", 
                                       "test_flaky_network.log", "test_data_issue.log"]
            },
            "data": ["failures.db"],  # For storing historical failures
            "": ["requirements.txt", "README.md", ".gitignore", "config.py"]
        }
    }
    
    def create_structure(base_path, structure_dict):
        for key, value in structure_dict.items():
            current_path = Path(base_path) / key if key else Path(base_path)
            current_path.mkdir(parents=True, exist_ok=True)
            
            if isinstance(value, dict):
                create_structure(current_path, value)
            elif isinstance(value, list):
                for file in value:
                    file_path = current_path / file
                    if not file_path.exists():
                        file_path.touch()
                        print(f"✓ Created: {file_path}")
    
    create_structure(".", structure)
    print("\n✅ Project structure created successfully!")

if __name__ == "__main__":
    create_project_structure()