
#!/usr/bin/env python3

"""
Test script to verify that the main components can be imported and initialized
without the JSON serialization errors.
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all main components can be imported."""
    print("Testing imports...")
    
    try:
        from test_orchestrator import TestOrchestrator
        from performance_monitor import PerformanceMonitor, DateTimeEncoder
        from report_generator import ReportGenerator
        print("✅ All imports successful!")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_orchestrator_initialization():
    """Test that TestOrchestrator can be initialized."""
    print("\nTesting TestOrchestrator initialization...")
    
    try:
        from test_orchestrator import TestOrchestrator
        orchestrator = TestOrchestrator()
        print("✅ TestOrchestrator initialized successfully!")
        print(f"   Available test configs: {list(orchestrator.test_configs.keys())}")
        return True
    except Exception as e:
        print(f"❌ TestOrchestrator initialization failed: {e}")
        return False


def test_performance_monitor_initialization():
    """Test that PerformanceMonitor can be initialized."""
    print("\nTesting PerformanceMonitor initialization...")
    
    try:
        from performance_monitor import PerformanceMonitor
        # Initialize without container name to avoid Docker dependency
        monitor = PerformanceMonitor()
        print("✅ PerformanceMonitor initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ PerformanceMonitor initialization failed: {e}")
        return False


def test_report_generator_initialization():
    """Test that ReportGenerator can be initialized."""
    print("\nTesting ReportGenerator initialization...")
    
    try:
        from report_generator import ReportGenerator
        report_gen = ReportGenerator()
        print("✅ ReportGenerator initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ ReportGenerator initialization failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing main component initialization...\n")
    
    tests = [
        test_imports,
        test_orchestrator_initialization,
        test_performance_monitor_initialization,
        test_report_generator_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All main components can be initialized correctly!")
        return True
    else:
        print("❌ Some component initialization failed.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

