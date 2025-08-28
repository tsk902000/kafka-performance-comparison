


import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable

# Try confluent-kafka first, fallback to kafka-python
try:
    from confluent_kafka import Consumer as ConfluentConsumer
    from confluent_kafka import KafkaError as ConfluentKafkaError
    CONFLUENT_KAFKA_AVAILABLE = True
except ImportError:
    CONFLUENT_KAFKA_AVAILABLE = False

try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_PYTHON_AVAILABLE = True
except ImportError:
    KAFKA_PYTHON_AVAILABLE = False


class KafkaPerformanceConsumer:
    """High-performance Kafka consumer for testing."""
    
    def __init__(self, bootstrap_servers: str, topic: str, group_id: str, **consumer_config):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        
        # Determine which Kafka client to use
        if CONFLUENT_KAFKA_AVAILABLE:
            self.client_type = 'confluent'
            self.consumer_config = {
                'bootstrap.servers': bootstrap_servers,
                'group.id': group_id,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 1000,
                'session.timeout.ms': 30000,
                'max.poll.interval.ms': 300000,
                **consumer_config
            }
        elif KAFKA_PYTHON_AVAILABLE:
            self.client_type = 'kafka-python'
            self.consumer_config = {
                'bootstrap_servers': bootstrap_servers,
                'group_id': group_id,
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'key_deserializer': lambda m: m.decode('utf-8') if m else None,
                'auto_offset_reset': 'earliest',
                'enable_auto_commit': True,
                'auto_commit_interval_ms': 1000,
                'fetch_min_bytes': 1,
                'fetch_max_wait_ms': 500,
                'max_partition_fetch_bytes': 1048576,
                **consumer_config
            }
        else:
            raise ImportError("Neither confluent-kafka nor kafka-python is available")
        
        self.consumer = None
        self.stats = {
            'messages_consumed': 0,
            'bytes_consumed': 0,
            'start_time': None,
            'end_time': None,
            'errors': [],
            'latency_measurements': []
        }
        self.running = False
        
    def connect(self):
        """Connect to Kafka cluster."""
        try:
            if self.client_type == 'confluent':
                self.consumer = ConfluentConsumer(self.consumer_config)
                self.consumer.subscribe([self.topic])
            else:  # kafka-python
                self.consumer = KafkaConsumer(self.topic, **self.consumer_config)
            return True
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Kafka cluster."""
        if self.consumer:
            self.consumer.close()
            self.consumer = None
    
    def consume_messages(self, 
                        duration_seconds: int,
                        progress_callback: Optional[Callable] = None) -> Dict:
        """Consume messages for specified duration."""
        
        if not self.consumer:
            raise Exception("Consumer not connected")
        
        self.stats = {
            'messages_consumed': 0,
            'bytes_consumed': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'errors': [],
            'latency_measurements': [],
            'throughput_history': []
        }
        
        self.running = True
        start_time = time.time()
        last_count = 0
        
        try:
            while self.running and (time.time() - start_time) < duration_seconds:
                # Poll for messages with timeout
                if self.client_type == 'confluent':
                    msg = self.consumer.poll(timeout=1.0)
                    if msg is not None and not msg.error():
                        self._process_message(msg)
                else:  # kafka-python
                    message_batch = self.consumer.poll(timeout_ms=1000)
                    
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            self._process_message(message)
                
                # Update throughput statistics every second
                current_time = time.time()
                if int(current_time) > int(start_time + len(self.stats['throughput_history'])):
                    current_count = self.stats['messages_consumed']
                    throughput = current_count - last_count
                    last_count = current_count
                    
                    self.stats['throughput_history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'messages_per_second': throughput,
                        'total_messages': current_count
                    })
                    
                    if progress_callback:
                        progress_callback(current_count, throughput)
        
        except Exception as e:
            self.stats['errors'].append(str(e))
        
        finally:
            self.running = False
            self.stats['end_time'] = datetime.now()
        
        # Calculate final statistics
        total_duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.stats['duration_seconds'] = total_duration
        self.stats['average_throughput'] = self.stats['messages_consumed'] / total_duration if total_duration > 0 else 0
        self.stats['average_bandwidth_mbps'] = (self.stats['bytes_consumed'] / (1024 * 1024)) / total_duration if total_duration > 0 else 0
        
        # Calculate latency statistics
        if self.stats['latency_measurements']:
            latencies = self.stats['latency_measurements']
            self.stats['latency_avg_ms'] = sum(latencies) / len(latencies)
            self.stats['latency_min_ms'] = min(latencies)
            self.stats['latency_max_ms'] = max(latencies)
            self.stats['latency_p95_ms'] = self._percentile(latencies, 95)
            self.stats['latency_p99_ms'] = self._percentile(latencies, 99)
        
        return self.stats
    
    def _process_message(self, message):
        """Process a single consumed message."""
        try:
            if self.client_type == 'confluent':
                # Confluent Kafka message
                message_value = json.loads(message.value().decode('utf-8'))
                message_size = len(message.value())
            else:
                # kafka-python message
                message_value = message.value
                message_size = len(message.value.encode('utf-8')) if isinstance(message.value, str) else len(str(message.value).encode('utf-8'))
            
            # Calculate latency if timestamp is available
            if isinstance(message_value, dict) and 'timestamp' in message_value:
                try:
                    sent_time = datetime.fromisoformat(message_value['timestamp'])
                    received_time = datetime.now()
                    latency_ms = (received_time - sent_time).total_seconds() * 1000
                    self.stats['latency_measurements'].append(latency_ms)
                except Exception:
                    pass  # Skip latency calculation if timestamp parsing fails
            
            self.stats['messages_consumed'] += 1
            self.stats['bytes_consumed'] += message_size
            
        except Exception as e:
            self.stats['errors'].append(f"Error processing message: {e}")
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list of values."""
        if not data:
            return 0
        
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        if index >= len(sorted_data):
            index = len(sorted_data) - 1
        return sorted_data[index]
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'messages_consumed': 0,
            'bytes_consumed': 0,
            'start_time': None,
            'end_time': None,
            'errors': [],
            'latency_measurements': []
        }
    
    def stop(self):
        """Stop consuming messages."""
        self.running = False




