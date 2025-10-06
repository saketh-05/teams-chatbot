# test_framework.py
# Testing framework for Memory Box accuracy evaluation

import os
import json
import logging
import argparse
import subprocess
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Import the config manager
from config_manager import ConfigManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("memory_box_tests.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestFramework")

class MemoryBoxTester:
    """Framework for testing Memory Box accuracy and performance"""
    
    def __init__(self, test_data_dir="./test_data"):
        """Initialize the testing framework"""
        self.test_data_dir = test_data_dir
        self.config_manager = ConfigManager()
        self.results = []
        
        # Create test data directory if it doesn't exist
        os.makedirs(test_data_dir, exist_ok=True)
    
    def load_test_cases(self, test_file):
        """Load test cases from a JSON file
        
        Args:
            test_file: Path to the test cases JSON file
            
        Returns:
            List of test case dictionaries
        """
        try:
            with open(test_file, 'r') as f:
                test_cases = json.load(f)
            logger.info(f"Loaded {len(test_cases)} test cases from {test_file}")
            return test_cases
        except Exception as e:
            logger.error(f"Error loading test cases: {str(e)}")
            return []
    
    def run_query(self, query, sources=None, n_results=3):
        """Run a query against the Memory Box
        
        Args:
            query: The query string
            sources: Optional list of specific sources to query
            n_results: Number of results to fetch per source
            
        Returns:
            Dict containing the query results
        """
        try:
            cmd = ["python", "query_brain.py", "--query", query, "--results", str(n_results)]
            
            if sources:
                cmd.extend(["--sources"] + sources)
            
            logger.info(f"Running query: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Query failed with error: {result.stderr}")
                return {"success": False, "error": result.stderr}
            
            return {"success": True, "output": result.stdout}
        except Exception as e:
            logger.error(f"Error running query: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def evaluate_result(self, test_case, result):
        """Evaluate a query result against expected output
        
        Args:
            test_case: The test case dictionary
            result: The query result dictionary
            
        Returns:
            Dict containing evaluation metrics
        """
        if not result["success"]:
            return {
                "query": test_case["query"],
                "success": False,
                "error": result.get("error", "Unknown error"),
                "expected_sources": test_case.get("expected_sources", []),
                "found_sources": [],
                "source_match_rate": 0.0,
                "expected_keywords": test_case.get("expected_keywords", []),
                "keyword_match_rate": 0.0
            }
        
        output = result["output"]
        
        # Extract sources from output
        found_sources = []
        for line in output.split("\n"):
            if line.startswith("- "):
                found_sources.append(line[2:])  # Remove the "- " prefix
        
        # Calculate source match rate
        expected_sources = test_case.get("expected_sources", [])
        source_matches = sum(1 for source in expected_sources if any(source in found for found in found_sources))
        source_match_rate = source_matches / len(expected_sources) if expected_sources else 1.0
        
        # Calculate keyword match rate
        expected_keywords = test_case.get("expected_keywords", [])
        keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in output.lower())
        keyword_match_rate = keyword_matches / len(expected_keywords) if expected_keywords else 1.0
        
        return {
            "query": test_case["query"],
            "success": True,
            "expected_sources": expected_sources,
            "found_sources": found_sources,
            "source_match_rate": source_match_rate,
            "expected_keywords": expected_keywords,
            "keyword_match_rate": keyword_match_rate,
            "overall_score": (source_match_rate + keyword_match_rate) / 2
        }
    
    def run_test_suite(self, test_file):
        """Run a full test suite
        
        Args:
            test_file: Path to the test cases JSON file
            
        Returns:
            DataFrame with test results
        """
        test_cases = self.load_test_cases(test_file)
        if not test_cases:
            logger.error(f"No test cases found in {test_file}")
            return None
        
        results = []
        for i, test_case in enumerate(test_cases):
            logger.info(f"Running test case {i+1}/{len(test_cases)}: {test_case['query']}")
            
            # Run the query
            result = self.run_query(
                test_case["query"], 
                test_case.get("sources"), 
                test_case.get("n_results", 3)
            )
            
            # Evaluate the result
            evaluation = self.evaluate_result(test_case, result)
            results.append(evaluation)
            
            # Log the result
            if evaluation["success"]:
                logger.info(f"Test {i+1} - Score: {evaluation['overall_score']:.2f}")
            else:
                logger.error(f"Test {i+1} - Failed: {evaluation.get('error', 'Unknown error')}")
        
        # Convert results to DataFrame
        df = pd.DataFrame(results)
        
        # Calculate overall metrics
        success_rate = df["success"].mean()
        avg_source_match = df["source_match_rate"].mean()
        avg_keyword_match = df["keyword_match_rate"].mean()
        avg_overall_score = df["overall_score"].mean() if "overall_score" in df else 0.0
        
        logger.info(f"Test suite complete. Success rate: {success_rate:.2f}")
        logger.info(f"Average source match rate: {avg_source_match:.2f}")
        logger.info(f"Average keyword match rate: {avg_keyword_match:.2f}")
        logger.info(f"Average overall score: {avg_overall_score:.2f}")
        
        return df
    
    def generate_test_cases(self, output_file, num_cases=10):
        """Generate test cases based on available data sources
        
        Args:
            output_file: Path to save the generated test cases
            num_cases: Number of test cases to generate
            
        Returns:
            List of generated test cases
        """
        # This is a simplified version - in a real implementation,
        # you would analyze the actual data to generate meaningful test cases
        
        test_cases = []
        
        # Example test cases for different data sources
        drive_test_cases = [
            {
                "query": "What are the latest project requirements?",
                "sources": ["drive"],
                "expected_sources": ["Drive: Project Requirements"],
                "expected_keywords": ["requirements", "project", "specification"]
            },
            {
                "query": "Who is the project manager for the current sprint?",
                "sources": ["drive"],
                "expected_sources": ["Drive: Team Structure"],
                "expected_keywords": ["manager", "sprint", "team"]
            }
        ]
        
        slack_test_cases = [
            {
                "query": "What was discussed in yesterday's standup?",
                "sources": ["slack"],
                "expected_sources": ["Slack: Channel #daily-standup"],
                "expected_keywords": ["standup", "update", "progress"]
            },
            {
                "query": "What are the current blockers in the project?",
                "sources": ["slack"],
                "expected_sources": ["Slack: Channel #project-status"],
                "expected_keywords": ["blocker", "issue", "problem"]
            }
        ]
        
        teams_test_cases = [
            {
                "query": "What was the outcome of the last architecture meeting?",
                "sources": ["teams"],
                "expected_sources": ["Teams: Channel #architecture"],
                "expected_keywords": ["architecture", "decision", "design"]
            },
            {
                "query": "What are the current deployment issues?",
                "sources": ["teams"],
                "expected_sources": ["Teams: Channel #devops"],
                "expected_keywords": ["deployment", "issue", "pipeline"]
            }
        ]
        
        jira_test_cases = [
            {
                "query": "What are the high priority bugs?",
                "sources": ["jira"],
                "expected_sources": ["Jira: BUG-"],
                "expected_keywords": ["bug", "high", "priority"]
            },
            {
                "query": "What features are planned for the next release?",
                "sources": ["jira"],
                "expected_sources": ["Jira: FEAT-"],
                "expected_keywords": ["feature", "release", "roadmap"]
            }
        ]
        
        # Multi-source test cases
        multi_source_test_cases = [
            {
                "query": "What is the current status of the authentication feature?",
                "sources": ["jira", "slack"],
                "expected_sources": ["Jira: AUTH-", "Slack: Channel #auth-team"],
                "expected_keywords": ["authentication", "status", "feature"]
            },
            {
                "query": "What are the technical specifications for the new API?",
                "sources": ["drive", "teams"],
                "expected_sources": ["Drive: API Specification", "Teams: Channel #api-team"],
                "expected_keywords": ["API", "specification", "technical"]
            }
        ]
        
        # Combine all test cases
        all_test_cases = (
            drive_test_cases + 
            slack_test_cases + 
            teams_test_cases + 
            jira_test_cases + 
            multi_source_test_cases
        )
        
        # Select a subset of test cases if needed
        test_cases = all_test_cases[:num_cases] if num_cases < len(all_test_cases) else all_test_cases
        
        # Save test cases to file
        try:
            with open(output_file, 'w') as f:
                json.dump(test_cases, f, indent=2)
            logger.info(f"Generated {len(test_cases)} test cases and saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving test cases: {str(e)}")
        
        return test_cases
    
    def save_results(self, results_df, output_file):
        """Save test results to a CSV file
        
        Args:
            results_df: DataFrame with test results
            output_file: Path to save the results
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            results_df.to_csv(output_file, index=False)
            logger.info(f"Results saved to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            return False

def main():
    """Main function to run the testing framework"""
    parser = argparse.ArgumentParser(description="Memory Box Testing Framework")
    parser.add_argument("--generate", action="store_true", help="Generate test cases")
    parser.add_argument("--run", action="store_true", help="Run test cases")
    parser.add_argument("--test-file", default="./test_data/test_cases.json", help="Path to test cases file")
    parser.add_argument("--results-file", default="./test_data/test_results.csv", help="Path to save test results")
    parser.add_argument("--num-cases", type=int, default=10, help="Number of test cases to generate")
    args = parser.parse_args()
    
    tester = MemoryBoxTester()
    
    if args.generate:
        tester.generate_test_cases(args.test_file, args.num_cases)
    
    if args.run:
        results = tester.run_test_suite(args.test_file)
        if results is not None:
            tester.save_results(results, args.results_file)

if __name__ == "__main__":
    main()