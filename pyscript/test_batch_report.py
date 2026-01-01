#!/usr/bin/env python3
"""Test Batch Report Generation"""

import sys
from pathlib import Path

# Add pyscript to path
sys.path.insert(0, str(Path(__file__).parent))

from report_generator import generate_batch_report


def test_batch_report_with_real_data():
    """Test batch report generation with realistic sample data"""
    print("=" * 80)
    print("BATCH REPORT GENERATION TEST")
    print("=" * 80)
    print()

    # Create realistic sample data based on actual conversion results
    results = [
        {
            "filename": "SID/Stinsens_Last_Night_of_89.sid",
            "driver": "laxity",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 99.93,
            "status": "passed",
            "error_message": "",
            "duration": 0.46,
            "output_files": [
                "output/Stinsens_Last_Night_of_89.sf2",
                "output/Stinsens_Last_Night_of_89_analysis.txt"
            ]
        },
        {
            "filename": "SID/Beast.sid",
            "driver": "laxity",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 99.85,
            "status": "passed",
            "error_message": "",
            "duration": 0.39,
            "output_files": [
                "output/Beast.sf2",
                "output/Beast_analysis.txt"
            ]
        },
        {
            "filename": "SID/Delicate.sid",
            "driver": "laxity",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 99.91,
            "status": "passed",
            "error_message": "",
            "duration": 0.39,
            "output_files": [
                "output/Delicate.sf2"
            ]
        },
        {
            "filename": "G5/examples/Driver 11 Test - Arpeggio.sf2",
            "driver": "driver11",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 100.0,
            "status": "passed",
            "error_message": "",
            "duration": 0.25,
            "output_files": [
                "output/Driver_11_Test_Arpeggio.sf2"
            ]
        },
        {
            "filename": "SID/Unknown_Format.sid",
            "driver": "driver11",
            "steps_completed": 3,
            "total_steps": 5,
            "accuracy": 0,
            "status": "failed",
            "error_message": "Unsupported player format",
            "duration": 0.15,
            "output_files": []
        },
        {
            "filename": "SID/Partial_Success.sid",
            "driver": "np20",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 75.3,
            "status": "warning",
            "error_message": "Low accuracy detected",
            "duration": 0.52,
            "output_files": [
                "output/Partial_Success.sf2"
            ]
        }
    ]

    summary = {
        "total_files": 6,
        "passed": 4,
        "failed": 1,
        "warnings": 1,
        "avg_accuracy": 95.8,
        "duration": 2.16,
        "pass_rate": 66.7
    }

    config = {
        "primary_driver": "auto",
        "enabled_steps": [
            "Analyze SID",
            "Convert to SF2",
            "Validate Output",
            "Generate Report",
            "Archive Original"
        ]
    }

    # Generate report
    output_file = Path("output/batch_report_test.html")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Test Data:")
    print(f"  Total files: {summary['total_files']}")
    print(f"  Passed: {summary['passed']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Warnings: {summary['warnings']}")
    print(f"  Average accuracy: {summary['avg_accuracy']:.1f}%")
    print(f"  Total duration: {summary['duration']:.2f}s")
    print()

    print(f"Generating batch report: {output_file}")
    success = generate_batch_report(results, summary, str(output_file), config)

    if success:
        file_size = output_file.stat().st_size
        print(f"[OK] Batch report generated successfully!")
        print(f"     File: {output_file}")
        print(f"     Size: {file_size:,} bytes")
        print()
        print("=" * 80)
        print("TEST PASSED")
        print("=" * 80)
        print()
        print(f"Open {output_file} in your browser to view the report.")
        return True
    else:
        print("[ERROR] Batch report generation failed!")
        print()
        print("=" * 80)
        print("TEST FAILED")
        print("=" * 80)
        return False


if __name__ == '__main__':
    success = test_batch_report_with_real_data()
    sys.exit(0 if success else 1)
