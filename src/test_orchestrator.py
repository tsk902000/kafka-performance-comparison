


import os
import time
import json
import subprocess
import threading
from datetime import datetime
from typing import Dict, List, Optional
import yaml
from pathlib import Path

from performance_monitor import PerformanceMonitor
from kafka_producer import KafkaPerformanceProducer
from kafka_consumer import KafkaPerformanceConsumer


class TestOrchestrator:
    """Orchestrates performance tests for Kafka and Redpanda."""
    
    def __init__(self, project_dir: str = "."):
        self.project_dir = Path(project_dir)
        self.results_dir = self.project_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.kafka_config = {
            'bootstrap_servers': 'localhost:9092',
            'container_name': 'kafka-broker',
            'compose_file': 'docker-compose.kafka.yml'
        }
        
        self.redpanda_config = {
            'bootstrap_servers': 'localhost:19092',
            'container_name': 'redpanda-broker',
            'compose_file': 'docker-compose.redpanda.yml'
        }
        
        self.test_configs = {
            'light_load': {
                'duration_seconds': 60,
                'messages_per_second': 100,
                'message_size_bytes': 1024,
                'num_producer_threads': 1,
                'num_consumers': 1
            },
            'medium_load': {
                'duration_seconds': 120,
                'messages_per_second': 1000,
                'message_size_bytes': 2048,
                'num_producer_threads': 2,
                'num_consumers': 2
            },
            'heavy_load': {
                'duration_seconds': 180,
                'messages_per_second': 5000,
                'message_size_bytes': 4096,
                'num_producer_threads': 4,
                'num_consumers': 4
            }
        }
    
    def start_platform(self, platform: str) -> bool:
        """Start Kafka or Redpanda platform."""
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        compose_file = self.project_dir / config['compose_file']
        
        print(f"Starting {platform}...")
        try:
            # Stop any existing containers
            subprocess.run([
                'docker-compose', '-f', str(compose_file), 'down'
            ], capture_output=True, check=False)
            
            # Start the platform
            result = subprocess.run([
                'docker-compose', '-f', str(compose_file), 'up', '-d'
            ], capture_output=True, check=True)
            
            # Wait for platform to be ready
            self._wait_for_platform(platform)
            
            print(f"{platform} started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to start {platform}: {e}")
            print(f"stdout: {e.stdout.decode()}")
            print(f"stderr: {e.stderr.decode()}")
            return False
    
    def stop_platform(self, platform: str) -> bool:
        """Stop Kafka or Redpanda platform."""
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        compose_file = self.project_dir / config['compose_file']
        
        print(f"Stopping {platform}...")
        try:
            subprocess.run([
                'docker-compose', '-f', str(compose_file), 'down'
            ], capture_output=True, check=True)
            
            print(f"{platform} stopped successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop {platform}: {e}")
            return False
    
    def _wait_for_platform(self, platform: str, max_wait: int = 60):
        """Wait for platform to be ready."""
        if platform == 'kafka':
            bootstrap_servers = self.kafka_config['bootstrap_servers']
        else:
            bootstrap_servers = self.redpanda_config['bootstrap_servers']
        
        print(f"Waiting for {platform} to be ready...")
        
        for i in range(max_wait):
            try:
                # Try to create a test producer to check connectivity
                producer = KafkaPerformanceProducer(
                    bootstrap_servers=bootstrap_servers,
                    topic='test-connectivity'
                )
                if producer.connect():
                    producer.disconnect()
                    print(f"{platform} is ready!")
                    return True
            except Exception:
                pass
            
            time.sleep(1)
        
        raise Exception(f"{platform} failed to start within {max_wait} seconds")
    
    def run_single_test(self, 
                       platform: str, 
                       test_name: str, 
                       custom_config: Optional[Dict] = None) -> Dict:
        """Run a single performance test."""
        
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        test_config = self.test_configs.get(test_name, {})
        if custom_config:
            test_config.update(custom_config)
        
        print(f"\nRunning {test_name} test on {platform}")
        print(f"Configuration: {test_config}")
        
        # Create unique topic for this test
        topic = f"perf-test-{platform}-{test_name}-{int(time.time())}"
        
        # Start performance monitoring
        monitor = PerformanceMonitor(config['container_name'])
        monitor.start_monitoring(interval=1.0)
        
        # Initialize results
        test_results = {
            'platform': platform,
            'test_name': test_name,
            'config': test_config,
            'topic': topic,
            'start_time': datetime.now().isoformat(),
            'producer_stats': {},
            'consumer_stats': [],
            'system_metrics': {},
            'errors': []
        }
        
        try:
            # Start consumers first
            consumers = []
            consumer_threads = []
            
            for i in range(test_config.get('num_consumers', 1)):
                consumer = KafkaPerformanceConsumer(
                    bootstrap_servers=config['bootstrap_servers'],
                    topic=topic,
                    group_id=f"test-group-{i}"
                )
                
                if consumer.connect():
                    consumers.append(consumer)
                    
                    # Start consumer in separate thread
                    def run_consumer(cons):
                        return cons.consume_messages(
                            duration_seconds=test_config['duration_seconds'] + 10,  # Extra time for cleanup
                            progress_callback=lambda count, tps: print(f"Consumer consumed: {count} messages ({tps} msg/s)")
                        )
                    
                    thread = threading.Thread(target=lambda c=consumer: run_consumer(c))
                    thread.daemon = True
                    consumer_threads.append((thread, consumer))
                    thread.start()
                else:
                    test_results['errors'].append(f"Failed to connect consumer {i}")
            
            # Wait a moment for consumers to be ready
            time.sleep(2)
            
            # Start producer
            producer = KafkaPerformanceProducer(
                bootstrap_servers=config['bootstrap_servers'],
                topic=topic
            )
            
            if producer.connect():
                # Run producer load test
                producer_stats = producer.run_load_test(
                    duration_seconds=test_config['duration_seconds'],
                    messages_per_second=test_config['messages_per_second'],
                    message_size_bytes=test_config['message_size_bytes'],
                    num_threads=test_config['num_producer_threads'],
                    progress_callback=lambda count, tps: print(f"Producer sent: {count} messages ({tps} msg/s)")
                )
                
                test_results['producer_stats'] = producer_stats
                producer.disconnect()
            else:
                test_results['errors'].append("Failed to connect producer")
            
            # Wait for consumers to finish
            time.sleep(5)  # Allow consumers to catch up
            
            for thread, consumer in consumer_threads:
                consumer.stop()
                thread.join(timeout=10)
                consumer_stats = consumer.get_stats()
                test_results['consumer_stats'].append(consumer_stats)
                consumer.disconnect()
        
        except Exception as e:
            test_results['errors'].append(str(e))
        
        finally:
            # Stop monitoring and collect metrics
            system_metrics = monitor.stop_monitoring()
            test_results['system_metrics'] = monitor.get_summary_stats()
            test_results['end_time'] = datetime.now().isoformat()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"{platform}_{test_name}_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        # Save raw metrics
        metrics_file = self.results_dir / f"{platform}_{test_name}_{timestamp}_metrics.json"
        monitor.save_metrics(str(metrics_file))
        
        print(f"Test completed. Results saved to {results_file}")
        return test_results
    
    def run_comparison_test(self, test_name: str, custom_config: Optional[Dict] = None) -> Dict:
        """Run the same test on both Kafka and Redpanda for comparison."""
        
        print(f"\n{'='*60}")
        print(f"RUNNING COMPARISON TEST: {test_name}")
        print(f"{'='*60}")
        
        comparison_results = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'kafka_results': {},
            'redpanda_results': {},
            'comparison': {}
        }
        
        # Test Kafka
        print(f"\n{'-'*30} KAFKA TEST {'-'*30}")
        try:
            if self.start_platform('kafka'):
                kafka_results = self.run_single_test('kafka', test_name, custom_config)
                comparison_results['kafka_results'] = kafka_results
            else:
                comparison_results['kafka_results'] = {'error': 'Failed to start Kafka'}
        finally:
            self.stop_platform('kafka')
            time.sleep(5)  # Wait between tests
        
        # Test Redpanda
        print(f"\n{'-'*30} REDPANDA TEST {'-'*30}")
        try:
            if self.start_platform('redpanda'):
                redpanda_results = self.run_single_test('redpanda', test_name, custom_config)
                comparison_results['redpanda_results'] = redpanda_results
            else:
                comparison_results['redpanda_results'] = {'error': 'Failed to start Redpanda'}
        finally:
            self.stop_platform('redpanda')
        
        # Generate comparison
        comparison_results['comparison'] = self._generate_comparison(
            comparison_results['kafka_results'],
            comparison_results['redpanda_results']
        )
        
        comparison_results['end_time'] = datetime.now().isoformat()
        
        # Save comparison results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = self.results_dir / f"comparison_{test_name}_{timestamp}.json"
        
        with open(comparison_file, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        print(f"\nComparison test completed. Results saved to {comparison_file}")
        return comparison_results
    
    def _generate_comparison(self, kafka_results: Dict, redpanda_results: Dict) -> Dict:
        """Generate comparison metrics between Kafka and Redpanda results."""
        comparison = {}
        
        try:
            # Producer comparison
            if 'producer_stats' in kafka_results and 'producer_stats' in redpanda_results:
                kafka_producer = kafka_results['producer_stats']
                redpanda_producer = redpanda_results['producer_stats']
                
                comparison['producer'] = {
                    'throughput': {
                        'kafka_msg_per_sec': kafka_producer.get('average_throughput', 0),
                        'redpanda_msg_per_sec': redpanda_producer.get('average_throughput', 0),
                        'winner': 'redpanda' if redpanda_producer.get('average_throughput', 0) > kafka_producer.get('average_throughput', 0) else 'kafka'
                    },
                    'bandwidth': {
                        'kafka_mbps': kafka_producer.get('average_bandwidth_mbps', 0),
                        'redpanda_mbps': redpanda_producer.get('average_bandwidth_mbps', 0),
                        'winner': 'redpanda' if redpanda_producer.get('average_bandwidth_mbps', 0) > kafka_producer.get('average_bandwidth_mbps', 0) else 'kafka'
                    }
                }
            
            # Consumer comparison
            if kafka_results.get('consumer_stats') and redpanda_results.get('consumer_stats'):
                kafka_consumer = kafka_results['consumer_stats'][0] if kafka_results['consumer_stats'] else {}
                redpanda_consumer = redpanda_results['consumer_stats'][0] if redpanda_results['consumer_stats'] else {}
                
                comparison['consumer'] = {
                    'throughput': {
                        'kafka_msg_per_sec': kafka_consumer.get('average_throughput', 0),
                        'redpanda_msg_per_sec': redpanda_consumer.get('average_throughput', 0),
                        'winner': 'redpanda' if redpanda_consumer.get('average_throughput', 0) > kafka_consumer.get('average_throughput', 0) else 'kafka'
                    },
                    'latency': {
                        'kafka_avg_ms': kafka_consumer.get('latency_avg_ms', 0),
                        'redpanda_avg_ms': redpanda_consumer.get('latency_avg_ms', 0),
                        'winner': 'redpanda' if redpanda_consumer.get('latency_avg_ms', float('inf')) < kafka_consumer.get('latency_avg_ms', float('inf')) else 'kafka'
                    }
                }
            
            # System resource comparison
            if 'system_metrics' in kafka_results and 'system_metrics' in redpanda_results:
                kafka_system = kafka_results['system_metrics']
                redpanda_system = redpanda_results['system_metrics']
                
                comparison['resources'] = {
                    'cpu_usage': {
                        'kafka_avg_percent': kafka_system.get('system', {}).get('cpu_avg', 0),
                        'redpanda_avg_percent': redpanda_system.get('system', {}).get('cpu_avg', 0),
                        'winner': 'redpanda' if redpanda_system.get('system', {}).get('cpu_avg', float('inf')) < kafka_system.get('system', {}).get('cpu_avg', float('inf')) else 'kafka'
                    },
                    'memory_usage': {
                        'kafka_avg_percent': kafka_system.get('system', {}).get('memory_avg', 0),
                        'redpanda_avg_percent': redpanda_system.get('system', {}).get('memory_avg', 0),
                        'winner': 'redpanda' if redpanda_system.get('system', {}).get('memory_avg', float('inf')) < kafka_system.get('system', {}).get('memory_avg', float('inf')) else 'kafka'
                    }
                }
        
        except Exception as e:
            comparison['error'] = f"Failed to generate comparison: {e}"
        
        return comparison
    
    def run_all_tests(self) -> List[Dict]:
        """Run all predefined tests for comparison."""
        results = []
        
        for test_name in self.test_configs.keys():
            try:
                result = self.run_comparison_test(test_name)
                results.append(result)
            except Exception as e:
                print(f"Failed to run test {test_name}: {e}")
                results.append({
                    'test_name': test_name,
                    'error': str(e)
                })
        
        return results




