
import psutil
import time
import threading
import json
from datetime import datetime
from typing import Dict, List, Optional
import docker


class PerformanceMonitor:
    """Monitor system and container performance metrics."""
    
    def __init__(self, container_name: Optional[str] = None):
        self.container_name = container_name
        self.docker_client = None
        self.container = None
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
        
        if container_name:
            try:
                self.docker_client = docker.from_env()
                self.container = self.docker_client.containers.get(container_name)
            except Exception as e:
                print(f"Warning: Could not connect to Docker container {container_name}: {e}")
    
    def start_monitoring(self, interval: float = 1.0):
        """Start monitoring performance metrics."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and return collected metrics."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
        return self.metrics
    
    def _monitor_loop(self, interval: float):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                metric = self._collect_metrics()
                self.metrics.append(metric)
                time.sleep(interval)
            except Exception as e:
                print(f"Error collecting metrics: {e}")
                time.sleep(interval)
    
    def _collect_metrics(self) -> Dict:
        """Collect current performance metrics."""
        timestamp = datetime.now().isoformat()
        
        # System-wide metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        network_io = psutil.net_io_counters()
        
        metric = {
            'timestamp': timestamp,
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_mb': memory.used / (1024 * 1024),
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_read_mb': disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                'disk_write_mb': disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                'network_sent_mb': network_io.bytes_sent / (1024 * 1024) if network_io else 0,
                'network_recv_mb': network_io.bytes_recv / (1024 * 1024) if network_io else 0,
            }
        }
        
        # Container-specific metrics if available
        if self.container:
            try:
                container_stats = self.container.stats(stream=False)
                metric['container'] = self._parse_container_stats(container_stats)
            except Exception as e:
                print(f"Error getting container stats: {e}")
                metric['container'] = {}
        
        return metric
    
    def _parse_container_stats(self, stats: Dict) -> Dict:
        """Parse Docker container statistics."""
        try:
            # CPU usage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            memory_percent = (memory_usage / memory_limit) * 100.0
            
            # Network I/O
            networks = stats.get('networks', {})
            total_rx = sum(net['rx_bytes'] for net in networks.values())
            total_tx = sum(net['tx_bytes'] for net in networks.values())
            
            # Block I/O
            blkio_stats = stats.get('blkio_stats', {})
            io_service_bytes = blkio_stats.get('io_service_bytes_recursive', [])
            read_bytes = sum(item['value'] for item in io_service_bytes if item['op'] == 'Read')
            write_bytes = sum(item['value'] for item in io_service_bytes if item['op'] == 'Write')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_usage_mb': memory_usage / (1024 * 1024),
                'memory_limit_mb': memory_limit / (1024 * 1024),
                'memory_percent': memory_percent,
                'network_rx_mb': total_rx / (1024 * 1024),
                'network_tx_mb': total_tx / (1024 * 1024),
                'disk_read_mb': read_bytes / (1024 * 1024),
                'disk_write_mb': write_bytes / (1024 * 1024),
            }
        except Exception as e:
            print(f"Error parsing container stats: {e}")
            return {}
    
    def get_summary_stats(self) -> Dict:
        """Calculate summary statistics from collected metrics."""
        if not self.metrics:
            return {}
        
        # Extract system metrics
        cpu_values = [m['system']['cpu_percent'] for m in self.metrics]
        memory_values = [m['system']['memory_percent'] for m in self.metrics]
        disk_read_values = [m['system']['disk_read_mb'] for m in self.metrics]
        disk_write_values = [m['system']['disk_write_mb'] for m in self.metrics]
        
        summary = {
            'duration_seconds': len(self.metrics),
            'system': {
                'cpu_avg': sum(cpu_values) / len(cpu_values),
                'cpu_max': max(cpu_values),
                'cpu_min': min(cpu_values),
                'memory_avg': sum(memory_values) / len(memory_values),
                'memory_max': max(memory_values),
                'memory_min': min(memory_values),
                'disk_read_total_mb': max(disk_read_values) - min(disk_read_values),
                'disk_write_total_mb': max(disk_write_values) - min(disk_write_values),
            }
        }
        
        # Container summary if available
        if self.metrics[0].get('container'):
            container_cpu_values = [m['container']['cpu_percent'] for m in self.metrics if m.get('container')]
            container_memory_values = [m['container']['memory_percent'] for m in self.metrics if m.get('container')]
            
            if container_cpu_values:
                summary['container'] = {
                    'cpu_avg': sum(container_cpu_values) / len(container_cpu_values),
                    'cpu_max': max(container_cpu_values),
                    'cpu_min': min(container_cpu_values),
                    'memory_avg': sum(container_memory_values) / len(container_memory_values),
                    'memory_max': max(container_memory_values),
                    'memory_min': min(container_memory_values),
                }
        
        return summary
    
    def save_metrics(self, filename: str):
        """Save collected metrics to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'metrics': self.metrics,
                'summary': self.get_summary_stats()
            }, f, indent=2)


