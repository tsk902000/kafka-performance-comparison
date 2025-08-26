


#!/usr/bin/env python3

"""
Local testing script for environments where Docker is not available.
This script demonstrates the testing framework functionality without Docker.
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from performance_monitor import PerformanceMonitor
from report_generator import ReportGenerator


def simulate_test_results():
    """Simulate test results for demonstration purposes."""
    
    # Simulate Kafka results
    kafka_results = {
        'platform': 'kafka',
        'test_name': 'medium_load',
        'config': {
            'duration_seconds': 120,
            'messages_per_second': 1000,
            'message_size_bytes': 2048,
            'num_producer_threads': 2,
            'num_consumers': 2
        },
        'producer_stats': {
            'messages_sent': 120000,
            'messages_failed': 12,
            'average_throughput': 998.5,
            'average_bandwidth_mbps': 1.95,
            'duration_seconds': 120.2
        },
        'consumer_stats': [{
            'messages_consumed': 119988,
            'average_throughput': 995.2,
            'latency_avg_ms': 15.3,
            'latency_min_ms': 2.1,
            'latency_max_ms': 89.4,
            'latency_p95_ms': 28.7,
            'latency_p99_ms': 45.2
        }],
        'system_metrics': {
            'duration_seconds': 120,
            'system': {
                'cpu_avg': 45.2,
                'cpu_max': 78.1,
                'cpu_min': 12.3,
                'memory_avg': 62.8,
                'memory_max': 71.2,
                'memory_min': 58.4
            }
        },
        'errors': []
    }
    
    # Simulate Redpanda results (slightly better performance)
    redpanda_results = {
        'platform': 'redpanda',
        'test_name': 'medium_load',
        'config': {
            'duration_seconds': 120,
            'messages_per_second': 1000,
            'message_size_bytes': 2048,
            'num_producer_threads': 2,
            'num_consumers': 2
        },
        'producer_stats': {
            'messages_sent': 120000,
            'messages_failed': 3,
            'average_throughput': 1024.7,
            'average_bandwidth_mbps': 2.01,
            'duration_seconds': 117.1
        },
        'consumer_stats': [{
            'messages_consumed': 119997,
            'average_throughput': 1021.3,
            'latency_avg_ms': 12.8,
            'latency_min_ms': 1.8,
            'latency_max_ms': 67.2,
            'latency_p95_ms': 24.1,
            'latency_p99_ms': 38.9
        }],
        'system_metrics': {
            'duration_seconds': 117,
            'system': {
                'cpu_avg': 38.7,
                'cpu_max': 65.4,
                'cpu_min': 15.2,
                'memory_avg': 48.3,
                'memory_max': 55.1,
                'memory_min': 42.7
            }
        },
        'errors': []
    }
    
    return kafka_results, redpanda_results


def generate_comparison_results(kafka_results, redpanda_results):
    """Generate comparison results from individual platform results."""
    
    comparison_results = {
        'test_name': 'medium_load',
        'start_time': datetime.now().isoformat(),
        'kafka_results': kafka_results,
        'redpanda_results': redpanda_results,
        'comparison': {}
    }
    
    # Generate comparison metrics
    kafka_producer = kafka_results['producer_stats']
    redpanda_producer = redpanda_results['producer_stats']
    kafka_consumer = kafka_results['consumer_stats'][0]
    redpanda_consumer = redpanda_results['consumer_stats'][0]
    kafka_system = kafka_results['system_metrics']['system']
    redpanda_system = redpanda_results['system_metrics']['system']
    
    comparison_results['comparison'] = {
        'producer': {
            'throughput': {
                'kafka_msg_per_sec': kafka_producer['average_throughput'],
                'redpanda_msg_per_sec': redpanda_producer['average_throughput'],
                'winner': 'redpanda' if redpanda_producer['average_throughput'] > kafka_producer['average_throughput'] else 'kafka'
            },
            'bandwidth': {
                'kafka_mbps': kafka_producer['average_bandwidth_mbps'],
                'redpanda_mbps': redpanda_producer['average_bandwidth_mbps'],
                'winner': 'redpanda' if redpanda_producer['average_bandwidth_mbps'] > kafka_producer['average_bandwidth_mbps'] else 'kafka'
            }
        },
        'consumer': {
            'throughput': {
                'kafka_msg_per_sec': kafka_consumer['average_throughput'],
                'redpanda_msg_per_sec': redpanda_consumer['average_throughput'],
                'winner': 'redpanda' if redpanda_consumer['average_throughput'] > kafka_consumer['average_throughput'] else 'kafka'
            },
            'latency': {
                'kafka_avg_ms': kafka_consumer['latency_avg_ms'],
                'redpanda_avg_ms': redpanda_consumer['latency_avg_ms'],
                'winner': 'redpanda' if redpanda_consumer['latency_avg_ms'] < kafka_consumer['latency_avg_ms'] else 'kafka'
            }
        },
        'resources': {
            'cpu_usage': {
                'kafka_avg_percent': kafka_system['cpu_avg'],
                'redpanda_avg_percent': redpanda_system['cpu_avg'],
                'winner': 'redpanda' if redpanda_system['cpu_avg'] < kafka_system['cpu_avg'] else 'kafka'
            },
            'memory_usage': {
                'kafka_avg_percent': kafka_system['memory_avg'],
                'redpanda_avg_percent': redpanda_system['memory_avg'],
                'winner': 'redpanda' if redpanda_system['memory_avg'] < kafka_system['memory_avg'] else 'kafka'
            }
        }
    }
    
    comparison_results['end_time'] = datetime.now().isoformat()
    return comparison_results


def test_performance_monitor():
    """Test the performance monitoring functionality."""
    print("Testing Performance Monitor...")
    
    # Test without Docker container
    monitor = PerformanceMonitor()
    monitor.start_monitoring(interval=0.5)
    
    print("Monitoring system performance for 5 seconds...")
    time.sleep(5)
    
    metrics = monitor.stop_monitoring()
    summary = monitor.get_summary_stats()
    
    print(f"Collected {len(metrics)} metric samples")
    print(f"Average CPU usage: {summary['system']['cpu_avg']:.2f}%")
    print(f"Average memory usage: {summary['system']['memory_avg']:.2f}%")
    
    # Save metrics to file
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metrics_file = results_dir / f"test_metrics_{timestamp}.json"
    monitor.save_metrics(str(metrics_file))
    
    print(f"Metrics saved to: {metrics_file}")
    return True


def test_report_generation():
    """Test the report generation functionality."""
    print("\nTesting Report Generation...")
    
    # Generate simulated test results
    kafka_results, redpanda_results = simulate_test_results()
    comparison_results = generate_comparison_results(kafka_results, redpanda_results)
    
    # Save comparison results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_file = results_dir / f"test_comparison_{timestamp}.json"
    
    with open(comparison_file, 'w') as f:
        json.dump(comparison_results, f, indent=2)
    
    print(f"Comparison results saved to: {comparison_file}")
    
    # Generate report
    report_gen = ReportGenerator(str(results_dir))
    
    # Print summary table
    print("\nGenerating summary table...")
    report_gen.print_summary_table(comparison_results)
    
    # Generate HTML report
    print("\nGenerating HTML report...")
    report_file = report_gen.generate_comparison_report(comparison_results)
    print(f"HTML report generated: {report_file}")
    
    # Generate charts
    print("\nGenerating performance charts...")
    try:
        chart_files = report_gen.generate_charts(comparison_results)
        if chart_files:
            print("Charts generated:")
            for chart_file in chart_files:
                print(f"  - {chart_file}")
        else:
            print("No charts generated (may require display)")
    except Exception as e:
        print(f"Chart generation failed (expected in headless environment): {e}")
    
    return True


def main():
    """Run local tests to demonstrate functionality."""
    print("="*60)
    print("KAFKA VS REDPANDA PERFORMANCE COMPARISON - LOCAL TEST")
    print("="*60)
    print()
    print("This script demonstrates the testing framework functionality")
    print("without requiring Docker. It uses simulated data to show")
    print("how the performance comparison and reporting works.")
    print()
    
    try:
        # Test performance monitoring
        if test_performance_monitor():
            print("✓ Performance monitoring test passed")
        
        # Test report generation
        if test_report_generation():
            print("✓ Report generation test passed")
        
        print("\n" + "="*60)
        print("LOCAL TESTING COMPLETED SUCCESSFULLY")
        print("="*60)
        print()
        print("To run actual tests with Docker:")
        print("1. Ensure Docker is running")
        print("2. Run: python main.py compare --test medium_load --generate-report")
        print()
        print("Check the 'results/' directory for generated files.")
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())



