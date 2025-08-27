

import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
import uuid

# Try confluent-kafka first, fallback to kafka-python
try:
    from confluent_kafka import Producer as ConfluentProducer
    from confluent_kafka import KafkaError as ConfluentKafkaError
    CONFLUENT_KAFKA_AVAILABLE = False
except ImportError:
    CONFLUENT_KAFKA_AVAILABLE = False

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_PYTHON_AVAILABLE = True
except ImportError:
    KAFKA_PYTHON_AVAILABLE = False


class KafkaPerformanceProducer:
    """High-performance Kafka producer for testing."""
    
    def __init__(self, bootstrap_servers: str, topic: str, mode: str = "v1", **producer_config):
        """
        Initialize the Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            topic: Topic to produce messages to
            mode: "v1" for synchronous (original) mode, "v2" for asynchronous (high-throughput) mode
            **producer_config: Additional producer configuration
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.mode = mode
        
        # Determine which Kafka client to use
        if CONFLUENT_KAFKA_AVAILABLE:
            self.client_type = 'confluent'
            self.producer_config = {
                'bootstrap.servers': bootstrap_servers,
                'acks': 'all',
                'retries': 3,
                'batch.size': 16384,
                'linger.ms': 10,
                **producer_config
            }
        elif KAFKA_PYTHON_AVAILABLE:
            self.client_type = 'kafka-python'
            self.producer_config = {
                'bootstrap_servers': bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                'key_serializer': lambda k: str(k).encode('utf-8') if k else None,
                'acks': 'all',
                'retries': 3,
                'batch_size': 16384,
                'linger_ms': 10,
                'buffer_memory': 33554432,
                **producer_config
            }
        else:
            raise ImportError("Neither confluent-kafka nor kafka-python is available")
        
        self.producer = None
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'bytes_sent': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
        self.running = False
        
    def connect(self):
        """Connect to Kafka cluster."""
        try:
            if self.client_type == 'confluent':
                self.producer = ConfluentProducer(self.producer_config)
                # Verify connection by requesting metadata
                metadata = self.producer.list_topics(timeout=5)
                if not metadata.brokers:
                    raise Exception("No brokers available")
            else:  # kafka-python
                self.producer = KafkaProducer(**self.producer_config)
                # For kafka-python, the connection is established lazily
                # Force a metadata refresh to verify connectivity
                _ = self.producer.bootstrap_connected()
            return True
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Kafka cluster."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            self.producer = None
    
    def send_message(self, message: Dict, key: Optional[str] = None) -> bool:
        """Send a single message."""
        if not self.producer:
            return False
        
        try:
            # Add metadata to message
            enriched_message = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'data': message
            }
            
            if self.client_type == 'confluent':
                # Confluent Kafka producer
                message_json = json.dumps(enriched_message)
                message_bytes = message_json.encode('utf-8')
                key_bytes = key.encode('utf-8') if key else None
                
                # Produce the message
                self.producer.produce(
                    self.topic,
                    value=message_bytes,
                    key=key_bytes,
                    callback=self._delivery_callback if self.mode == "v2" else None
                )
                
                # In v1 mode, flush after each message (synchronous)
                # In v2 mode, don't flush (asynchronous)
                if self.mode == "v1":
                    self.producer.flush()
                    self.stats['messages_sent'] += 1
                    self.stats['bytes_sent'] += len(message_bytes)
                else:
                    # In v2 mode, we'll count messages in the callback
                    # But we still track bytes here for accurate bandwidth calculation
                    self.stats['bytes_sent'] += len(message_bytes)
                
            else:  # kafka-python
                future = self.producer.send(
                    self.topic,
                    value=enriched_message,
                    key=key
                )
                
                # In v1 mode, wait for send to complete (synchronous)
                # In v2 mode, don't wait (asynchronous)
                if self.mode == "v1":
                    record_metadata = future.get(timeout=10)
                    self.stats['messages_sent'] += 1
                    self.stats['bytes_sent'] += len(json.dumps(enriched_message).encode('utf-8'))
                else:
                    # For v2 mode with kafka-python, we add a callback
                    message_bytes = json.dumps(enriched_message).encode('utf-8')
                    self.stats['bytes_sent'] += len(message_bytes)
                    
                    # Add callback for asynchronous tracking
                    future.add_callback(self._kafka_python_callback)
                    future.add_errback(self._kafka_python_errback)
            
            return True
            
        except Exception as e:
            self.stats['messages_failed'] += 1
            self.stats['errors'].append(str(e))
            return False
    
    def _delivery_callback(self, err, msg):
        """Callback for confluent-kafka producer in v2 mode."""
        if err:
            self.stats['messages_failed'] += 1
            self.stats['errors'].append(str(err))
        else:
            self.stats['messages_sent'] += 1
    
    def _kafka_python_callback(self, record_metadata):
        """Success callback for kafka-python producer in v2 mode."""
        self.stats['messages_sent'] += 1
    
    def _kafka_python_errback(self, excp):
        """Error callback for kafka-python producer in v2 mode."""
        self.stats['messages_failed'] += 1
        self.stats['errors'].append(str(excp))
    
    def send_batch(self, messages: List[Dict], keys: Optional[List[str]] = None) -> int:
        """Send a batch of messages."""
        if not self.producer:
            return 0
        
        sent_count = 0
        keys = keys or [None] * len(messages)
        
        for i, message in enumerate(messages):
            key = keys[i] if i < len(keys) else None
            if self.send_message(message, key):
                sent_count += 1
        
        return sent_count
    
    def run_load_test(self,
                     duration_seconds: int,
                     messages_per_second: int,
                     message_size_bytes: int = 1024,
                     num_threads: int = 1,
                     progress_callback: Optional[Callable] = None,
                     mode: Optional[str] = None) -> Dict:
        """Run a load test for specified duration."""
        
        # If mode is provided, temporarily override the instance mode for this test
        original_mode = self.mode
        if mode is not None:
            self.mode = mode
            
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'bytes_sent': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'errors': [],
            'throughput_history': [],
            'mode': self.mode  # Track which mode was used
        }
        
        self.running = True
        threads = []
        
        # Calculate messages per thread
        messages_per_thread_per_second = messages_per_second // num_threads
        
        # Create test message template
        test_data = 'x' * (message_size_bytes - 100)  # Reserve space for metadata
        
        def producer_thread():
            thread_stats = {'sent': 0, 'failed': 0}
            interval = 1.0 / messages_per_thread_per_second if messages_per_thread_per_second > 0 else 0
            
            start_time = time.time()
            while self.running and (time.time() - start_time) < duration_seconds:
                message = {
                    'thread_id': threading.current_thread().ident,
                    'sequence': thread_stats['sent'],
                    'test_data': test_data
                }
                
                if self.send_message(message):
                    thread_stats['sent'] += 1
                else:
                    thread_stats['failed'] += 1
                
                if interval > 0:
                    time.sleep(interval)
        
        # Start producer threads
        for i in range(num_threads):
            thread = threading.Thread(target=producer_thread)
            thread.daemon = True
            threads.append(thread)
            thread.start()
        
        # Monitor progress
        start_time = time.time()
        last_count = 0
        
        while self.running and (time.time() - start_time) < duration_seconds:
            time.sleep(1)
            current_count = self.stats['messages_sent']
            throughput = current_count - last_count
            last_count = current_count
            
            self.stats['throughput_history'].append({
                'timestamp': datetime.now().isoformat(),
                'messages_per_second': throughput,
                'total_messages': current_count
            })
            
            if progress_callback:
                progress_callback(current_count, throughput)
        
        # Stop all threads
        self.running = False
        for thread in threads:
            thread.join(timeout=5)
        
        # For v2 mode, flush any remaining messages before calculating stats
        if self.mode == "v2" and self.producer:
            self.producer.flush()
            
        self.stats['end_time'] = datetime.now()
        
        # Restore original mode if it was temporarily overridden
        if mode is not None:
            self.mode = original_mode
        
        # Calculate final statistics
        total_duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        self.stats['duration_seconds'] = total_duration
        self.stats['average_throughput'] = self.stats['messages_sent'] / total_duration if total_duration > 0 else 0
        self.stats['average_bandwidth_mbps'] = (self.stats['bytes_sent'] / (1024 * 1024)) / total_duration if total_duration > 0 else 0
        
        return self.stats
    
    def get_stats(self) -> Dict:
        """Get current statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'bytes_sent': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }



