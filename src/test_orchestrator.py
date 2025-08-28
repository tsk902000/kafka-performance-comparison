


import os
import time
import json
import subprocess
import threading
import socket
from datetime import datetime
from typing import Dict, List, Optional
import yaml
from pathlib import Path

from performance_monitor import PerformanceMonitor, DateTimeEncoder
from kafka_producer import KafkaPerformanceProducer
from kafka_consumer import KafkaPerformanceConsumer


class TestOrchestrator:
    """Orchestrates performance tests for Kafka and Redpanda."""
    
    def __init__(self, project_dir: str = ".", producer_mode: str = "v1"):
        """
        Initialize the test orchestrator.
        
        Args:
            project_dir: Project directory path
            producer_mode: Producer mode - "v1" for synchronous (original) or "v2" for asynchronous (high-throughput)
        """
        self.project_dir = Path(project_dir)
        self.results_dir = self.project_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        self.producer_mode = producer_mode
        
        self.kafka_config = {
            'bootstrap_servers': 'localhost:9092',
            'container_name': 'kafka-broker',
            'compose_file': 'docker-compose.kafka.yml'
        }
        
        self.kafka_kraft_config = {
            'bootstrap_servers': 'localhost:9093',
            'container_name': 'kafka-kraft-broker',
            'compose_file': 'docker-compose.kafka-kraft.yml'
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
                'messages_per_second': 50000,
                'message_size_bytes': 4096,
                'num_producer_threads': 12,
                'num_consumers': 6
            }
        }
    
    def start_platform(self, platform: str) -> bool:
        """Start Kafka, Kafka KRaft, or Redpanda platform."""
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'kafka-kraft':
            config = self.kafka_kraft_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        compose_file = self.project_dir / config['compose_file']
        
        print(f"Starting {platform}...")
        try:
            # Stop any existing containers
            subprocess.run([
                'docker', 'compose', '-f', str(compose_file), 'down'
            ], capture_output=True, check=False)
            
            # Start the platform
            result = subprocess.run([
                'docker', 'compose', '-f', str(compose_file), 'up', '-d'
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
        """Stop Kafka, Kafka KRaft, or Redpanda platform."""
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'kafka-kraft':
            config = self.kafka_kraft_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        compose_file = self.project_dir / config['compose_file']
        
        print(f"Stopping {platform}...")
        try:
            subprocess.run([
                'docker', 'compose', '-f', str(compose_file), 'down'
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
        elif platform == 'kafka-kraft':
            bootstrap_servers = self.kafka_kraft_config['bootstrap_servers']
            # KRaft takes longer to initialize
            max_wait = 120
        else:
            bootstrap_servers = self.redpanda_config['bootstrap_servers']
        
        # Parse host and port from bootstrap_servers
        host, port = bootstrap_servers.split(':')
        port = int(port)
        
        print(f"Waiting for {platform} to be ready on {host}:{port} (max {max_wait} seconds)...")
        
        # First, wait for the port to be open
        port_open = False
        for i in range(max_wait):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                if not port_open:
                    print(f"  Port {port} is now open ({i+1} seconds)")
                    port_open = True
                
                # Once port is open, try to connect with Kafka client
                try:
                    producer = KafkaPerformanceProducer(
                        bootstrap_servers=bootstrap_servers,
                        topic='test-connectivity'
                    )
                    if producer.connect():
                        producer.disconnect()
                        print(f"{platform} is ready! (took {i+1} seconds)")
                        return True
                except Exception as e:
                    # After port is open, show more frequent updates
                    if port_open and i % 5 == 0:
                        print(f"  Port is open but Kafka not ready yet... ({i} seconds elapsed)")
            else:
                # Print progress every 10 seconds while waiting for port
                if i > 0 and i % 10 == 0:
                    print(f"  Still waiting for port {port} to open... ({i} seconds elapsed)")
            
            time.sleep(1)
        
        # Try to get more diagnostic information before failing
        print(f"\nDiagnostic information for {platform}:")
        try:
            # Check if container is running
            container_name = self.kafka_config['container_name'] if platform == 'kafka' else \
                           self.kafka_kraft_config['container_name'] if platform == 'kafka-kraft' else \
                           self.redpanda_config['container_name']
            
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Status}}'],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                print(f"  Container status: {result.stdout.strip()}")
            else:
                print(f"  Container {container_name} is not running")
            
            # Check last few logs
            result = subprocess.run(
                ['docker', 'logs', '--tail', '10', container_name],
                capture_output=True, text=True, timeout=5
            )
            if result.stderr:
                print(f"  Recent logs:\n{result.stderr[:500]}")
        except Exception as diag_err:
            print(f"  Could not get diagnostic info: {diag_err}")
        
        raise Exception(f"{platform} failed to start within {max_wait} seconds")
    
    def run_single_test(self,
                       platform: str,
                       test_name: str,
                       custom_config: Optional[Dict] = None,
                       producer_mode: Optional[str] = None) -> Dict:
        """Run a single performance test."""
        
        if platform == 'kafka':
            config = self.kafka_config
        elif platform == 'kafka-kraft':
            config = self.kafka_kraft_config
        elif platform == 'redpanda':
            config = self.redpanda_config
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        # Use provided producer_mode or fall back to instance default
        mode = producer_mode if producer_mode is not None else self.producer_mode
        
        test_config = self.test_configs.get(test_name, {})
        if custom_config:
            test_config.update(custom_config)
        
        print(f"\nRunning {test_name} test on {platform} with producer mode {mode}")
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
            
            # Start producer with the specified mode
            producer = KafkaPerformanceProducer(
                bootstrap_servers=config['bootstrap_servers'],
                topic=topic,
                mode=mode
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
            json.dump(test_results, f, indent=2, cls=DateTimeEncoder)
        
        # Save raw metrics
        metrics_file = self.results_dir / f"{platform}_{test_name}_{timestamp}_metrics.json"
        monitor.save_metrics(str(metrics_file))
        
        print(f"Test completed. Results saved to {results_file}")
        return test_results
    
    def run_comparison_test(self, test_name: str, custom_config: Optional[Dict] = None, producer_mode: Optional[str] = None) -> Dict:
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
        
        # Use provided producer_mode or fall back to instance default
        mode = producer_mode if producer_mode is not None else self.producer_mode
        
        # Test Kafka
        print(f"\n{'-'*30} KAFKA TEST (Mode: {mode}) {'-'*30}")
        try:
            if self.start_platform('kafka'):
                kafka_results = self.run_single_test('kafka', test_name, custom_config, mode)
                comparison_results['kafka_results'] = kafka_results
            else:
                comparison_results['kafka_results'] = {'error': 'Failed to start Kafka'}
        finally:
            self.stop_platform('kafka')
            time.sleep(5)  # Wait between tests
        
        # Test Redpanda
        print(f"\n{'-'*30} REDPANDA TEST (Mode: {mode}) {'-'*30}")
        try:
            if self.start_platform('redpanda'):
                redpanda_results = self.run_single_test('redpanda', test_name, custom_config, mode)
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
            json.dump(comparison_results, f, indent=2, cls=DateTimeEncoder)
        
        print(f"\nComparison test completed. Results saved to {comparison_file}")
        return comparison_results
    
    def run_three_way_comparison_test(self, test_name: str, custom_config: Optional[Dict] = None, producer_mode: Optional[str] = None) -> Dict:
        """Run the same test on Kafka, Kafka KRaft, and Redpanda for comparison."""
        
        print(f"\n{'='*60}")
        print(f"RUNNING THREE-WAY COMPARISON TEST: {test_name}")
        print(f"{'='*60}")
        
        comparison_results = {
            'test_name': test_name,
            'start_time': datetime.now().isoformat(),
            'kafka_results': {},
            'kafka_kraft_results': {},
            'redpanda_results': {},
            'comparison': {}
        }
        
        # Use provided producer_mode or fall back to instance default
        mode = producer_mode if producer_mode is not None else self.producer_mode
        
        # Test Kafka (with Zookeeper)
        print(f"\n{'-'*30} KAFKA (ZOOKEEPER) TEST (Mode: {mode}) {'-'*30}")
        try:
            if self.start_platform('kafka'):
                kafka_results = self.run_single_test('kafka', test_name, custom_config, mode)
                comparison_results['kafka_results'] = kafka_results
            else:
                comparison_results['kafka_results'] = {'error': 'Failed to start Kafka'}
        finally:
            self.stop_platform('kafka')
            time.sleep(5)  # Wait between tests
        
        # Test Kafka KRaft (without Zookeeper)
        print(f"\n{'-'*30} KAFKA KRAFT TEST (Mode: {mode}) {'-'*30}")
        try:
            if self.start_platform('kafka-kraft'):
                kafka_kraft_results = self.run_single_test('kafka-kraft', test_name, custom_config, mode)
                comparison_results['kafka_kraft_results'] = kafka_kraft_results
            else:
                comparison_results['kafka_kraft_results'] = {'error': 'Failed to start Kafka KRaft'}
        finally:
            self.stop_platform('kafka-kraft')
            time.sleep(5)  # Wait between tests
        
        # Test Redpanda
        print(f"\n{'-'*30} REDPANDA TEST (Mode: {mode}) {'-'*30}")
        try:
            if self.start_platform('redpanda'):
                redpanda_results = self.run_single_test('redpanda', test_name, custom_config, mode)
                comparison_results['redpanda_results'] = redpanda_results
            else:
                comparison_results['redpanda_results'] = {'error': 'Failed to start Redpanda'}
        finally:
            self.stop_platform('redpanda')
        
        # Generate three-way comparison
        comparison_results['comparison'] = self._generate_three_way_comparison(
            comparison_results['kafka_results'],
            comparison_results['kafka_kraft_results'],
            comparison_results['redpanda_results']
        )
        
        comparison_results['end_time'] = datetime.now().isoformat()
        
        # Save comparison results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = self.results_dir / f"three_way_comparison_{test_name}_{timestamp}.json"
        
        with open(comparison_file, 'w') as f:
            json.dump(comparison_results, f, indent=2, cls=DateTimeEncoder)
        
        print(f"\nThree-way comparison test completed. Results saved to {comparison_file}")
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
    
    def _generate_three_way_comparison(self, kafka_results: Dict, kafka_kraft_results: Dict, redpanda_results: Dict) -> Dict:
        """Generate comparison metrics between Kafka, Kafka KRaft, and Redpanda results."""
        comparison = {}
        
        try:
            # Producer comparison
            if ('producer_stats' in kafka_results and 
                'producer_stats' in kafka_kraft_results and 
                'producer_stats' in redpanda_results):
                
                kafka_producer = kafka_results['producer_stats']
                kafka_kraft_producer = kafka_kraft_results['producer_stats']
                redpanda_producer = redpanda_results['producer_stats']
                
                # Throughput comparison
                throughputs = {
                    'kafka': kafka_producer.get('average_throughput', 0),
                    'kafka_kraft': kafka_kraft_producer.get('average_throughput', 0),
                    'redpanda': redpanda_producer.get('average_throughput', 0)
                }
                winner = max(throughputs, key=throughputs.get)
                
                comparison['producer'] = {
                    'throughput': {
                        'kafka_msg_per_sec': throughputs['kafka'],
                        'kafka_kraft_msg_per_sec': throughputs['kafka_kraft'],
                        'redpanda_msg_per_sec': throughputs['redpanda'],
                        'winner': winner,
                        'kraft_vs_zookeeper_improvement': ((throughputs['kafka_kraft'] - throughputs['kafka']) / throughputs['kafka'] * 100) if throughputs['kafka'] > 0 else 0
                    },
                    'bandwidth': {
                        'kafka_mbps': kafka_producer.get('average_bandwidth_mbps', 0),
                        'kafka_kraft_mbps': kafka_kraft_producer.get('average_bandwidth_mbps', 0),
                        'redpanda_mbps': redpanda_producer.get('average_bandwidth_mbps', 0),
                        'winner': max(['kafka', 'kafka_kraft', 'redpanda'], 
                                    key=lambda x: {'kafka': kafka_producer.get('average_bandwidth_mbps', 0),
                                                  'kafka_kraft': kafka_kraft_producer.get('average_bandwidth_mbps', 0),
                                                  'redpanda': redpanda_producer.get('average_bandwidth_mbps', 0)}[x])
                    }
                }
            
            # Consumer comparison
            if (kafka_results.get('consumer_stats') and 
                kafka_kraft_results.get('consumer_stats') and 
                redpanda_results.get('consumer_stats')):
                
                kafka_consumer = kafka_results['consumer_stats'][0] if kafka_results['consumer_stats'] else {}
                kafka_kraft_consumer = kafka_kraft_results['consumer_stats'][0] if kafka_kraft_results['consumer_stats'] else {}
                redpanda_consumer = redpanda_results['consumer_stats'][0] if redpanda_results['consumer_stats'] else {}
                
                # Consumer throughput comparison
                consumer_throughputs = {
                    'kafka': kafka_consumer.get('average_throughput', 0),
                    'kafka_kraft': kafka_kraft_consumer.get('average_throughput', 0),
                    'redpanda': redpanda_consumer.get('average_throughput', 0)
                }
                consumer_winner = max(consumer_throughputs, key=consumer_throughputs.get)
                
                # Latency comparison (lower is better)
                latencies = {
                    'kafka': kafka_consumer.get('latency_avg_ms', float('inf')),
                    'kafka_kraft': kafka_kraft_consumer.get('latency_avg_ms', float('inf')),
                    'redpanda': redpanda_consumer.get('latency_avg_ms', float('inf'))
                }
                latency_winner = min(latencies, key=latencies.get)
                
                comparison['consumer'] = {
                    'throughput': {
                        'kafka_msg_per_sec': consumer_throughputs['kafka'],
                        'kafka_kraft_msg_per_sec': consumer_throughputs['kafka_kraft'],
                        'redpanda_msg_per_sec': consumer_throughputs['redpanda'],
                        'winner': consumer_winner
                    },
                    'latency': {
                        'kafka_avg_ms': latencies['kafka'],
                        'kafka_kraft_avg_ms': latencies['kafka_kraft'],
                        'redpanda_avg_ms': latencies['redpanda'],
                        'winner': latency_winner
                    }
                }
            
            # System resource comparison
            if ('system_metrics' in kafka_results and 
                'system_metrics' in kafka_kraft_results and 
                'system_metrics' in redpanda_results):
                
                kafka_system = kafka_results['system_metrics']
                kafka_kraft_system = kafka_kraft_results['system_metrics']
                redpanda_system = redpanda_results['system_metrics']
                
                # CPU usage comparison (lower is better)
                cpu_usages = {
                    'kafka': kafka_system.get('system', {}).get('cpu_avg', float('inf')),
                    'kafka_kraft': kafka_kraft_system.get('system', {}).get('cpu_avg', float('inf')),
                    'redpanda': redpanda_system.get('system', {}).get('cpu_avg', float('inf'))
                }
                cpu_winner = min(cpu_usages, key=cpu_usages.get)
                
                # Memory usage comparison (lower is better)
                memory_usages = {
                    'kafka': kafka_system.get('system', {}).get('memory_avg', float('inf')),
                    'kafka_kraft': kafka_kraft_system.get('system', {}).get('memory_avg', float('inf')),
                    'redpanda': redpanda_system.get('system', {}).get('memory_avg', float('inf'))
                }
                memory_winner = min(memory_usages, key=memory_usages.get)
                
                comparison['resources'] = {
                    'cpu_usage': {
                        'kafka_avg_percent': cpu_usages['kafka'],
                        'kafka_kraft_avg_percent': cpu_usages['kafka_kraft'],
                        'redpanda_avg_percent': cpu_usages['redpanda'],
                        'winner': cpu_winner
                    },
                    'memory_usage': {
                        'kafka_avg_percent': memory_usages['kafka'],
                        'kafka_kraft_avg_percent': memory_usages['kafka_kraft'],
                        'redpanda_avg_percent': memory_usages['redpanda'],
                        'winner': memory_winner
                    }
                }
        
        except Exception as e:
            comparison['error'] = f"Failed to generate three-way comparison: {e}"
        
        return comparison
    
    def run_all_tests(self, producer_mode: Optional[str] = None) -> List[Dict]:
        """Run all predefined tests for comparison."""
        results = []
        
        for test_name in self.test_configs.keys():
            try:
                result = self.run_comparison_test(test_name, producer_mode=producer_mode)
                results.append(result)
            except Exception as e:
                print(f"Failed to run test {test_name}: {e}")
                results.append({
                    'test_name': test_name,
                    'error': str(e)
                })
        
        return results




