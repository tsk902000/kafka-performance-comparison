

# Kafka vs Redpanda Performance Comparison

A comprehensive performance testing framework for comparing Apache Kafka, Kafka KRaft, and Redpanda implementations. This project provides Docker-based deployments, automated testing, and detailed performance analysis with metrics collection for CPU, memory, I/O, and message throughput.

## Features

- **Three Platform Support**: Compare Kafka (Zookeeper), Kafka KRaft (no Zookeeper), and Redpanda
- **Isolated Testing**: Each platform runs in separate Docker containers to ensure fair comparison
- **Comprehensive Metrics**: Tracks CPU usage, memory consumption, disk I/O, network I/O, and message throughput
- **Multiple Test Scenarios**: Light, medium, and heavy load testing configurations
- **Three-Way Comparisons**: NEW! Compare all three platforms in a single test run
- **Automated Orchestration**: Start/stop platforms and run tests with simple commands
- **Rich Reporting**: HTML reports with charts and detailed performance analysis
- **Concurrent Testing**: Multi-threaded producers and consumers for realistic load simulation
- **KRaft Performance Analysis**: Measure the performance impact of removing Zookeeper
- **Dual Producer Modes**: Choose between standard (v1) or high-throughput (v2) producer modes

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- At least 4GB RAM available for containers
- Ubuntu/Linux environment (recommended)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Make the main script executable

```bash
chmod +x main.py
```

### 3. Run a Quick Comparison Test

```bash
# Traditional two-way comparison
python main.py compare --test medium_load --generate-report --generate-charts

# NEW: Three-way comparison including Kafka KRaft
python main.py three-way-compare --test medium_load --generate-report --generate-charts
```

**Two-way comparison** will:
- Start Kafka, run tests, stop Kafka
- Start Redpanda, run tests, stop Redpanda  
- Generate comparison report and charts

**Three-way comparison** will:
- Start Kafka (Zookeeper), run tests, stop Kafka
- Start Kafka KRaft (no Zookeeper), run tests, stop Kafka KRaft
- Start Redpanda, run tests, stop Redpanda
- Generate comprehensive comparison showing KRaft performance improvements

## Usage

### Available Commands

#### List Test Configurations
```bash
python main.py list-tests
```

#### Run Single Platform Test
```bash
# Test only Kafka (traditional with Zookeeper)
python main.py single --platform kafka --test heavy_load

# Test only Kafka KRaft (no Zookeeper)
python main.py single --platform kafka-kraft --test heavy_load

# Test only Redpanda with custom settings
python main.py single --platform redpanda --test light_load --duration 30 --messages-per-second 500
```

#### Run Comparison Tests
```bash
# Basic two-way comparison (Kafka vs Redpanda)
python main.py compare --test medium_load

# NEW: Three-way comparison (Kafka vs Kafka KRaft vs Redpanda)
python main.py three-way-compare --test medium_load

# Comparison with custom configuration
python main.py compare --test heavy_load --duration 300 --messages-per-second 10000 --message-size 4096

# Full three-way comparison with reports
python main.py three-way-compare --test medium_load --generate-report --generate-charts
```

#### Run All Tests
```bash
# Run all predefined test scenarios
python main.py all --generate-report --generate-charts
```

#### Platform Management
```bash
# Start platforms manually
python main.py start kafka          # Kafka with Zookeeper (port 9092)
python main.py start kafka-kraft    # Kafka KRaft mode (port 9093)
python main.py start redpanda       # Redpanda (port 19092)

# Stop platforms
python main.py stop kafka
python main.py stop kafka-kraft
python main.py stop redpanda
```

#### Generate Reports from Existing Results
```bash
python main.py report results/comparison_medium_load_20231201_143022.json --charts
```

## Kafka KRaft Support

This project now includes comprehensive support for Kafka KRaft mode (Kafka without Zookeeper). For detailed information about KRaft testing, performance optimizations, and advanced usage, see:

📖 **[Kafka KRaft Performance Testing Guide](KAFKA_KRAFT_GUIDE.md)**

Key benefits of KRaft mode:
- **No Zookeeper dependency** - Simplified architecture
- **Better performance** - 10-25% throughput improvement
- **Lower latency** - 15-30% reduction in message latency
- **Easier operations** - Fewer moving parts to manage

### Test Configurations

The framework includes three predefined test scenarios:

#### Light Load
- Duration: 60 seconds
- Messages per second: 100
- Message size: 1KB
- Producer threads: 1
- Consumers: 1

#### Medium Load  
- Duration: 120 seconds
- Messages per second: 1,000
- Message size: 2KB
- Producer threads: 2
- Consumers: 2

#### Heavy Load
- Duration: 180 seconds
- Messages per second: 5,000
- Message size: 4KB
- Producer threads: 4
- Consumers: 4

## Producer Modes

The framework supports two different producer modes that can be selected with the `--producer-mode` parameter:

### v1 Mode (Default)

- **Synchronous Operation**: Each message is sent and acknowledged before sending the next
- **Reliable Delivery**: Waits for broker acknowledgment of each message
- **Lower Throughput**: Typically achieves 300-800 messages/second under heavy load
- **Lower Resource Usage**: Less demanding on system resources
- **Predictable Behavior**: Consistent performance characteristics

### v2 Mode (High-Throughput)

- **Asynchronous Operation**: Messages are sent without waiting for acknowledgment
- **Batching Optimized**: Takes full advantage of Kafka's batching capabilities
- **Higher Throughput**: Can achieve 10,000+ messages/second under heavy load
- **Higher Resource Usage**: More demanding on CPU and network
- **Callback-Based**: Uses callbacks to track message delivery status

### When to Use Each Mode

- Use **v1 mode** (default) for:
  - Testing with predictable, controlled message rates
  - Scenarios where reliability is more important than throughput
  - Baseline performance testing
  - Comparing platforms with identical delivery guarantees

- Use **v2 mode** for:
  - Maximum throughput testing
  - Stress testing broker capabilities
  - Simulating high-volume production workloads
  - Benchmarking platform limits

### Example Usage

```bash
# Run with default v1 mode (synchronous)
python main.py compare --test heavy_load

# Run with v2 mode (asynchronous high-throughput)
python main.py compare --test heavy_load --producer-mode v2

# Three-way comparison with v2 mode
python main.py three-way-compare --test medium_load --producer-mode v2
```

### Custom Configuration with Producer Mode

You can override any test parameter:

```bash
python main.py compare \
  --test medium_load \
  --duration 600 \
  --messages-per-second 2000 \
  --message-size 8192 \
  --threads 8 \
  --producer-mode v2 \
  --generate-report
```

## Architecture

### Components

1. **Docker Compose Configurations**
   - `docker-compose.kafka.yml`: Apache Kafka with Zookeeper
   - `docker-compose.redpanda.yml`: Redpanda cluster

2. **Performance Testing Framework**
   - `src/kafka_producer.py`: High-performance message producer
   - `src/kafka_consumer.py`: Message consumer with latency tracking
   - `src/performance_monitor.py`: System and container metrics collection

3. **Test Orchestration**
   - `src/test_orchestrator.py`: Manages platform lifecycle and test execution
   - `main.py`: CLI interface for all operations

4. **Reporting System**
   - `src/report_generator.py`: HTML reports and chart generation

### Metrics Collected

#### Message Performance
- **Throughput**: Messages per second (producer and consumer)
- **Bandwidth**: Megabytes per second
- **Latency**: End-to-end message latency (average, min, max, P95, P99)
- **Success Rate**: Message delivery success percentage

#### System Resources
- **CPU Usage**: System and container CPU utilization
- **Memory Usage**: RAM consumption and utilization percentage
- **Disk I/O**: Read/write operations and bandwidth
- **Network I/O**: Network traffic in/out

#### Container Metrics
- **Container CPU**: CPU usage within Docker containers
- **Container Memory**: Memory usage and limits
- **Container Network**: Network traffic specific to containers
- **Container Disk**: Block I/O operations

## Platform Configurations

### Apache Kafka Configuration

The Kafka setup includes:
- Kafka broker with optimized settings
- Zookeeper for coordination
- Kafka UI for monitoring (port 8080)
- JMX metrics enabled

Key optimizations:
- 8 network and I/O threads
- Optimized buffer sizes
- Batch processing enabled

### Redpanda Configuration

The Redpanda setup includes:
- Single-node Redpanda cluster
- Redpanda Console for monitoring (port 8081)
- Schema Registry enabled
- Admin API enabled

Key features:
- No Zookeeper dependency
- Built-in schema registry
- Optimized for performance

## Results and Reports

### Output Files

Test results are saved in the `results/` directory:

- `{platform}_{test}_{timestamp}.json`: Detailed test results
- `{platform}_{test}_{timestamp}_metrics.json`: Raw performance metrics
- `comparison_{test}_{timestamp}.json`: Side-by-side comparison results
- `comparison_report_{timestamp}.html`: HTML report with charts
- `*.png`: Performance comparison charts

### Report Contents

HTML reports include:
- Executive summary with overall winner
- Producer performance comparison
- Consumer performance and latency analysis
- Resource usage comparison
- Detailed configuration and error information
- Interactive charts and visualizations

## Troubleshooting

### Docker Issues

If Docker daemon is not running:
```bash
sudo systemctl start docker
# or
sudo service docker start
```

### Permission Issues
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Container Startup Issues

Check container logs:
```bash
docker-compose -f docker-compose.kafka.yml logs
docker-compose -f docker-compose.redpanda.yml logs
```

### Port Conflicts

Default ports used:
- Kafka: 9092, 2181, 8080
- Redpanda: 19092, 18081, 18082, 19644

Ensure these ports are available or modify the Docker Compose files.

### Memory Issues

Ensure sufficient memory is available:
- Kafka requires ~2GB RAM
- Redpanda requires ~1GB RAM
- Testing framework requires ~1GB RAM

## Advanced Usage

### Custom Test Scenarios

Create custom test configurations by modifying `src/test_orchestrator.py`:

```python
self.test_configs['custom_test'] = {
    'duration_seconds': 300,
    'messages_per_second': 10000,
    'message_size_bytes': 8192,
    'num_producer_threads': 8,
    'num_consumers': 4
}
```

### Monitoring Integration

The performance monitor can be extended to integrate with external monitoring systems:

```python
from src.performance_monitor import PerformanceMonitor

monitor = PerformanceMonitor('kafka-broker')
monitor.start_monitoring()
# Your test code here
metrics = monitor.stop_monitoring()
```

### Custom Metrics

Add custom metrics by extending the `PerformanceMonitor` class:

```python
def _collect_custom_metrics(self):
    # Add your custom metric collection logic
    return custom_metrics
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review container logs
3. Open an issue with detailed error information

## Performance Tips

1. **Resource Allocation**: Ensure adequate CPU and memory for containers
2. **Network**: Use fast network connections for realistic testing
3. **Storage**: Use SSD storage for better I/O performance
4. **Isolation**: Run tests on dedicated hardware when possible
5. **Monitoring**: Monitor system resources during tests to identify bottlenecks


