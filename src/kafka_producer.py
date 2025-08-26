

import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Callable
from kafka import KafkaProducer
from kafka.errors import KafkaError
import uuid


class KafkaPerformanceProducer:
    """High-performance Kafka producer for testing."""
    
    def __init__(self, bootstrap_servers: str, topic: str, **producer_config):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
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
            self.producer = KafkaProducer(**self.producer_config)
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
            
            future = self.producer.send(
                self.topic,
                value=enriched_message,
                key=key
            )
            
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            
            self.stats['messages_sent'] += 1
            self.stats['bytes_sent'] += len(json.dumps(enriched_message).encode('utf-8'))
            
            return True
            
        except KafkaError as e:
            self.stats['messages_failed'] += 1
            self.stats['errors'].append(str(e))
            return False
        except Exception as e:
            self.stats['messages_failed'] += 1
            self.stats['errors'].append(str(e))
            return False
    
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
                     progress_callback: Optional[Callable] = None) -> Dict:
        """Run a load test for specified duration."""
        
        self.stats = {
            'messages_sent': 0,
            'messages_failed': 0,
            'bytes_sent': 0,
            'start_time': datetime.now(),
            'end_time': None,
            'errors': [],
            'throughput_history': []
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
        
        self.stats['end_time'] = datetime.now()
        
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



