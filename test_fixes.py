#!/usr/bin/env python3

"""
Test script to verify the fixes for the two reported errors:
1. Error parsing container stats: 'percpu_usage'
2. Comparison test failed: Object of type datetime is not JSON serializable
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from performance_monitor import PerformanceMonitor, DateTimeEncoder


def test_datetime_json_serialization():
    """Test that datetime objects can be serialized to JSON."""
    print("Testing datetime JSON serialization...")
    
    test_data = {
        'start_time': datetime.now(),
        'end_time': datetime.now(),
        'metrics': [
            {
                'timestamp': datetime.now(),
                'cpu_percent': 50.0,
                'memory_percent': 30.0
            }
        ]
    }
    
    try:
        # This should work with our custom encoder
        json_str = json.dumps(test_data, cls=DateTimeEncoder, indent=2)
        print("✅ Datetime JSON serialization works!")
        
        # Verify we can load it back
        loaded_data = json.loads(json_str)
        print("✅ JSON can be loaded back successfully!")
        
        return True
    except Exception as e:
        print(f"❌ Datetime JSON serialization failed: {e}")
        return False


def test_container_stats_parsing():
    """Test container stats parsing with missing percpu_usage field."""
    print("\nTesting container stats parsing...")
    
    monitor = PerformanceMonitor()
    
    # Test with missing percpu_usage field (this was causing the original error)
    stats_without_percpu = {
        'cpu_stats': {
            'cpu_usage': {
                'total_usage': 1000000000,
                # 'percpu_usage' field is missing - this was the problem
            },
            'system_cpu_usage': 2000000000
        },
        'precpu_stats': {
            'cpu_usage': {
                'total_usage': 500000000,
            },
            'system_cpu_usage': 1000000000
        },
        'memory_stats': {
            'usage': 1024 * 1024 * 100,  # 100MB
            'limit': 1024 * 1024 * 1024  # 1GB
        },
        'networks': {
            'eth0': {
                'rx_bytes': 1024,
                'tx_bytes': 2048
            }
        },
        'blkio_stats': {
            'io_service_bytes_recursive': [
                {'op': 'Read', 'value': 1024},
                {'op': 'Write', 'value': 2048}
            ]
        }
    }
    
    try:
        result = monitor._parse_container_stats(stats_without_percpu)
        print("✅ Container stats parsing with missing percpu_usage works!")
        print(f"   CPU percent: {result.get('cpu_percent', 'N/A')}")
        print(f"   Memory percent: {result.get('memory_percent', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Container stats parsing failed: {e}")
        return False


def test_container_stats_with_percpu():
    """Test container stats parsing with percpu_usage field present."""
    print("\nTesting container stats parsing with percpu_usage...")
    
    monitor = PerformanceMonitor()
    
    # Test with percpu_usage field present
    stats_with_percpu = {
        'cpu_stats': {
            'cpu_usage': {
                'total_usage': 1000000000,
                'percpu_usage': [250000000, 250000000, 250000000, 250000000]  # 4 CPUs
            },
            'system_cpu_usage': 2000000000
        },
        'precpu_stats': {
            'cpu_usage': {
                'total_usage': 500000000,
            },
            'system_cpu_usage': 1000000000
        },
        'memory_stats': {
            'usage': 1024 * 1024 * 100,  # 100MB
            'limit': 1024 * 1024 * 1024  # 1GB
        },
        'networks': {
            'eth0': {
                'rx_bytes': 1024,
                'tx_bytes': 2048
            }
        },
        'blkio_stats': {
            'io_service_bytes_recursive': [
                {'op': 'Read', 'value': 1024},
                {'op': 'Write', 'value': 2048}
            ]
        }
    }
    
    try:
        result = monitor._parse_container_stats(stats_with_percpu)
        print("✅ Container stats parsing with percpu_usage works!")
        print(f"   CPU percent: {result.get('cpu_percent', 'N/A')}")
        print(f"   Memory percent: {result.get('memory_percent', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Container stats parsing with percpu_usage failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Running tests for the reported fixes...\n")
    
    tests = [
        test_datetime_json_serialization,
        test_container_stats_parsing,
        test_container_stats_with_percpu
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n{'='*50}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All fixes are working correctly!")
        return True
    else:
        print("❌ Some tests failed. Please check the fixes.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
