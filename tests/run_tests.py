#!/usr/bin/env python3
"""
Comprehensive test runner for LMS backend
"""
import subprocess
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import argparse


class TestRunner:
    """Comprehensive test runner for LMS backend"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "summary": {},
            "details": {},
            "performance": {},
            "security": {},
            "coverage": {}
        }

    def run_command(self, command: List[str], cwd: str = None) -> Dict[str, Any]:
        """Run a command and return results"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd or ".",
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(command)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out after 300 seconds",
                "command": " ".join(command)
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "command": " ".join(command)
            }

    def run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests"""
        print("🧪 Running Unit Tests...")

        command = [
            "python", "-m", "pytest",
            "tests/unit/",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=tests/reports/unit_test_results.json"
        ]

        result = self.run_command(command)

        # Parse results if successful
        if result["success"] and os.path.exists("tests/reports/unit_test_results.json"):
            try:
                with open("tests/reports/unit_test_results.json", "r") as f:
                    test_data = json.load(f)
                    result["parsed_results"] = test_data
            except:
                pass

        return result

    def run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests"""
        print("🔗 Running Integration Tests...")

        command = [
            "python", "-m", "pytest",
            "tests/integration/",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=tests/reports/integration_test_results.json"
        ]

        result = self.run_command(command)

        # Parse results if successful
        if result["success"] and os.path.exists("tests/reports/integration_test_results.json"):
            try:
                with open("tests/reports/integration_test_results.json", "r") as f:
                    test_data = json.load(f)
                    result["parsed_results"] = test_data
            except:
                pass

        return result

    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests"""
        print("⚡ Running Performance Tests...")

        command = [
            "python", "-m", "pytest",
            "tests/performance/",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=tests/reports/performance_test_results.json",
            "--durations=10"
        ]

        result = self.run_command(command)

        # Parse results if successful
        if result["success"] and os.path.exists("tests/reports/performance_test_results.json"):
            try:
                with open("tests/reports/performance_test_results.json", "r") as f:
                    test_data = json.load(f)
                    result["parsed_results"] = test_data
            except:
                pass

        return result

    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests"""
        print("🔒 Running Security Tests...")

        command = [
            "python", "-m", "pytest",
            "tests/security/",
            "-v",
            "--tb=short",
            "--json-report",
            "--json-report-file=tests/reports/security_test_results.json"
        ]

        result = self.run_command(command)

        # Parse results if successful
        if result["success"] and os.path.exists("tests/reports/security_test_results.json"):
            try:
                with open("tests/reports/security_test_results.json", "r") as f:
                    test_data = json.load(f)
                    result["parsed_results"] = test_data
            except:
                pass

        return result

    def run_coverage_analysis(self) -> Dict[str, Any]:
        """Run code coverage analysis"""
        print("📊 Running Coverage Analysis...")

        command = [
            "python", "-m", "pytest",
            "--cov=services",
            "--cov-report=html:tests/reports/coverage_html",
            "--cov-report=json:tests/reports/coverage.json",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ]

        result = self.run_command(command)

        # Parse coverage results
        if os.path.exists("tests/reports/coverage.json"):
            try:
                with open("tests/reports/coverage.json", "r") as f:
                    coverage_data = json.load(f)
                    result["coverage_data"] = coverage_data
            except:
                pass

        return result

    def run_load_tests(self) -> Dict[str, Any]:
        """Run load tests using locust (if available)"""
        print("🔄 Running Load Tests...")

        # Check if locust is available
        locust_check = self.run_command(["python", "-c", "import locust; print('available')"])

        if not locust_check["success"]:
            return {
                "success": False,
                "message": "Locust not available for load testing",
                "skipped": True
            }

        # Run locust load tests
        command = [
            "locust",
            "-f", "tests/load/locustfile.py",
            "--headless",
            "--users", "100",
            "--spawn-rate", "10",
            "--run-time", "1m",
            "--csv=tests/reports/load_test_results"
        ]

        result = self.run_command(command)
        return result

    def check_service_health(self) -> Dict[str, Any]:
        """Check health of all services"""
        print("🏥 Checking Service Health...")

        services = [
            {"name": "api-gateway", "port": 8000},
            {"name": "auth-service", "port": 8001},
            {"name": "course-service", "port": 8002},
            {"name": "user-service", "port": 8003},
            {"name": "ai-service", "port": 8004},
            {"name": "assessment-service", "port": 8005},
            {"name": "analytics-service", "port": 8006},
            {"name": "notification-service", "port": 8007},
            {"name": "file-service", "port": 8008}
        ]

        health_results = {}

        for service in services:
            try:
                import requests
                response = requests.get(f"http://localhost:{service['port']}/health", timeout=5)
                health_results[service["name"]] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds()
                }
            except Exception as e:
                health_results[service["name"]] = {
                    "status": "unreachable",
                    "error": str(e)
                }

        return {
            "success": all(r["status"] == "healthy" for r in health_results.values()),
            "results": health_results
        }

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        print("📋 Generating Test Report...")

        report = f"""
# LMS Backend Test Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

### Test Results Overview
- **Unit Tests**: {'✅ PASSED' if self.results.get('unit', {}).get('success') else '❌ FAILED'}
- **Integration Tests**: {'✅ PASSED' if self.results.get('integration', {}).get('success') else '❌ FAILED'}
- **Performance Tests**: {'✅ PASSED' if self.results.get('performance', {}).get('success') else '❌ FAILED'}
- **Security Tests**: {'✅ PASSED' if self.results.get('security', {}).get('success') else '❌ FAILED'}
- **Coverage Analysis**: {'✅ PASSED' if self.results.get('coverage', {}).get('success') else '❌ FAILED'}

### Service Health Status
"""

        # Add service health details
        if 'health' in self.results:
            for service, status in self.results['health'].get('results', {}).items():
                status_icon = "✅" if status.get('status') == 'healthy' else "❌"
                report += f"- **{service}**: {status_icon} {status.get('status', 'unknown')}\n"

        report += "\n## Detailed Results\n\n"

        # Add detailed results for each test type
        for test_type, result in self.results.items():
            if test_type not in ['timestamp', 'summary'] and isinstance(result, dict):
                report += f"### {test_type.title()} Tests\n"
                report += f"- **Status**: {'✅ PASSED' if result.get('success') else '❌ FAILED'}\n"

                if 'parsed_results' in result:
                    parsed = result['parsed_results']
                    if 'summary' in parsed:
                        summary = parsed['summary']
                        report += f"- **Tests Run**: {summary.get('num_tests', 0)}\n"
                        report += f"- **Passed**: {summary.get('passed', 0)}\n"
                        report += f"- **Failed**: {summary.get('failed', 0)}\n"
                        report += f"- **Errors**: {summary.get('errors', 0)}\n"

                if result.get('stderr'):
                    report += f"- **Errors**: {result['stderr'][:500]}...\n"

                report += "\n"

        # Add coverage information
        if 'coverage' in self.results and self.results['coverage'].get('coverage_data'):
            coverage_data = self.results['coverage']['coverage_data']
            report += "## Code Coverage\n\n"
            report += f"- **Overall Coverage**: {coverage_data.get('totals', {}).get('percent_covered', 0):.1f}%\n"

            for file_path, file_data in coverage_data.get('files', {}).items():
                if file_data.get('summary', {}).get('percent_covered', 100) < 80:
                    report += f"- **{file_path}**: {file_data['summary']['percent_covered']:.1f}%\n"

        report += "\n## Recommendations\n\n"

        # Generate recommendations based on results
        recommendations = []

        if not self.results.get('unit', {}).get('success'):
            recommendations.append("🔧 Fix unit test failures to ensure core functionality works correctly")

        if not self.results.get('integration', {}).get('success'):
            recommendations.append("🔗 Fix integration test failures to ensure services communicate properly")

        if not self.results.get('security', {}).get('success'):
            recommendations.append("🔒 Address security test failures to prevent vulnerabilities")

        if not self.results.get('performance', {}).get('success'):
            recommendations.append("⚡ Optimize performance issues identified in performance tests")

        if self.results.get('coverage', {}).get('coverage_data'):
            coverage_pct = self.results['coverage']['coverage_data'].get('totals', {}).get('percent_covered', 100)
            if coverage_pct < 80:
                recommendations.append(f"📊 Improve code coverage (currently {coverage_pct:.1f}%, target: 80%+)")

        if not self.results.get('health', {}).get('success'):
            recommendations.append("🏥 Fix unhealthy services to ensure system reliability")

        if not recommendations:
            recommendations.append("🎉 All tests passed! System is ready for production.")

        for rec in recommendations:
            report += f"- {rec}\n"

        return report

    def save_report(self, report: str, filename: str = None):
        """Save test report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"tests/reports/test_report_{timestamp}.md"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        with open(filename, 'w') as f:
            f.write(report)

        print(f"📄 Report saved to: {filename}")

    def run_all_tests(self, include_load_tests: bool = False, include_coverage: bool = True) -> Dict[str, Any]:
        """Run all test suites"""
        print("🚀 Starting Comprehensive LMS Backend Testing Suite")
        print("=" * 60)

        # Create reports directory
        os.makedirs("tests/reports", exist_ok=True)

        # Check service health first
        print("\n1. Checking Service Health...")
        self.results["health"] = self.check_service_health()

        # Run test suites
        print("\n2. Running Test Suites...")

        self.results["unit"] = self.run_unit_tests()
        self.results["integration"] = self.run_integration_tests()
        self.results["performance"] = self.run_performance_tests()
        self.results["security"] = self.run_security_tests()

        if include_coverage:
            self.results["coverage"] = self.run_coverage_analysis()

        if include_load_tests:
            self.results["load"] = self.run_load_tests()

        # Generate summary
        self.results["summary"] = {
            "total_suites": len([k for k in self.results.keys() if k not in ['timestamp', 'summary', 'details']]),
            "passed_suites": len([k for k, v in self.results.items()
                                if k not in ['timestamp', 'summary', 'details'] and v.get('success')]),
            "failed_suites": len([k for k, v in self.results.items()
                                if k not in ['timestamp', 'summary', 'details'] and not v.get('success')]),
            "overall_success": all(v.get('success', False) for k, v in self.results.items()
                                 if k not in ['timestamp', 'summary', 'details'])
        }

        # Generate and save report
        report = self.generate_report()
        self.save_report(report)

        print("\n" + "=" * 60)
        print("🏁 Testing Complete!")
        print(f"📊 Overall Status: {'✅ ALL TESTS PASSED' if self.results['summary']['overall_success'] else '❌ SOME TESTS FAILED'}")
        print(f"📈 Test Suites Passed: {self.results['summary']['passed_suites']}/{self.results['summary']['total_suites']}")

        return self.results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="LMS Backend Test Runner")
    parser.add_argument("--load-tests", action="store_true", help="Include load tests")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage analysis")
    parser.add_argument("--report-file", help="Custom report filename")

    args = parser.parse_args()

    runner = TestRunner()
    results = runner.run_all_tests(
        include_load_tests=args.load_tests,
        include_coverage=not args.no_coverage
    )

    if args.report_file:
        report = runner.generate_report()
        runner.save_report(report, args.report_file)

    # Exit with appropriate code
    sys.exit(0 if results['summary']['overall_success'] else 1)


if __name__ == "__main__":
    main()