# Kafka vs Redpanda Performance Comparison

A comprehensive Docker-based performance testing framework for comparing Apache Kafka and Redpanda messaging platforms with real-time monitoring, automated optimization, and detailed reporting.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd kafka-performance-comparison

# Run the setup script
chmod +x scripts/setup.sh
./scripts/setup.sh

# Start a quick comparison test
chmod +x scripts/quick-comparison.sh
./scripts/quick-comparison.sh
```

## 📊 Features

- **🐳 Docker-based Deployment**: Consistent, isolated environments for fair comparison
- **📈 Real-time Monitoring**: Prometheus + Grafana stack with custom dashboards
- **⚡ Automated Testing**: Comprehensive performance test suites and scenarios
- **🔧 Configuration Optimization**: Automated parameter tuning with genetic algorithms
- **📋 Detailed Reporting**: Executive summaries to technical deep-dives
- **🔄 CI/CD Integration**: GitHub Actions workflows for continuous testing
- **🎯 Multiple Workloads**: Throughput, latency, mixed, and failure recovery scenarios

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Kafka Cluster │    │ Redpanda Cluster│    │ Monitoring Stack│
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Broker 1  │ │    │ │   Node 1    │ │    │ │ Prometheus  │ │
│ │   Broker 2  │ │    │ │   Node 2    │ │    │ │ Grafana     │ │
│ │   Broker 3  │ │    │ │   Node 3    │ │    │ │ Alertmanager│ │
│ │ Zookeeper   │ │    │ │             │ │    │ │ Jaeger      │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Testing Framework│
                    │                 │
                    │ ┌─────────────┐ │
                    │ │ Producers   │ │
                    │ │ Consumers   │ │
                    │ │ Benchmarks  │ │
                    │ │ Scenarios   │ │
                    │ └─────────────┘ │
                    └─────────────────┘
```

## 📋 System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS (10.15+), Windows 10+ with WSL2
- **CPU**: 8+ cores
- **RAM**: 16GB
- **Storage**: 100GB+ SSD
- **Network**: 1Gbps+

### Recommended Requirements
- **CPU**: 16+ cores
- **RAM**: 32GB+
- **Storage**: 500GB+ NVMe SSD
- **Network**: 10Gbps+

## 🛠️ Installation

### Prerequisites

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Setup

```bash
# Run the automated setup
./scripts/setup.sh

# Or manual setup
docker network create kafka-network
docker network create redpanda-network
docker network create monitoring-network

# Start monitoring stack
docker-compose -f docker/monitoring/docker-compose.yml up -d

# Start Kafka environment
docker-compose -f docker/kafka/docker-compose.yml up -d

# Start Redpanda environment
docker-compose -f docker/redpanda/docker-compose.yml up -d
```

## 🧪 Running Tests

### Individual Platform Testing (Recommended)
```bash
# Test only Apache Kafka performance (pure Apache distribution)
chmod +x scripts/test-apache-kafka-only.sh
./scripts/test-apache-kafka-only.sh

# Test only Confluent Kafka performance
chmod +x scripts/test-kafka-only.sh
./scripts/test-kafka-only.sh

# Test only Redpanda performance
chmod +x scripts/test-redpanda-only.sh
./scripts/test-redpanda-only.sh

# Compare results from individual tests
chmod +x scripts/compare-results.sh
./scripts/compare-results.sh
```

### Automated Testing Options
```bash
# Run both tests sequentially and compare
./scripts/compare-results.sh run

# Run specific platform only
./scripts/compare-results.sh apache-kafka  # Apache Kafka only
./scripts/compare-results.sh kafka         # Confluent Kafka only
./scripts/compare-results.sh redpanda      # Redpanda only

# Compare latest available results
./scripts/compare-results.sh auto          # Default mode
```

### Quick Comparison (Both Platforms Simultaneously)
```bash
# Run a 5-minute comparison test (both platforms at once)
./scripts/quick-comparison.sh

# Custom test duration and parameters
TEST_DURATION=30m MESSAGE_SIZE=2048 TARGET_THROUGHPUT=50000 ./scripts/quick-comparison.sh
```

### Configuration Optimization
```bash
# Run optimization for maximum throughput
./scripts/run-optimization.sh --platform kafka --target throughput

# Run optimization for minimum latency
./scripts/run-optimization.sh --platform redpanda --target latency

# Run balanced optimization
./scripts/run-optimization.sh --platform both --target balanced
```

## 📊 Monitoring & Dashboards

### Access Points
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Apache Kafka UI**: http://localhost:8083
- **Confluent Kafka UI**: http://localhost:8081
- **Redpanda Console**: http://localhost:8082
- **Jaeger Tracing**: http://localhost:16686
- **Kibana**: http://localhost:5601

### Key Metrics
- **Throughput**: Messages/sec, Bytes/sec
- **Latency**: p50, p95, p99 percentiles
- **Resource Usage**: CPU, Memory, Disk I/O, Network
- **Reliability**: Error rates, Availability, Recovery time

## 🔍 Platform Comparison

### Apache Kafka vs Confluent Kafka vs Redpanda

| Feature | Apache Kafka | Confluent Kafka | Redpanda |
|---------|--------------|-----------------|----------|
| **Distribution** | Apache Foundation | Confluent Platform | Redpanda Data |
| **License** | Apache 2.0 | Confluent Community License | Business Source License |
| **Language** | Java/Scala | Java/Scala | C++ |
| **Dependencies** | KRaft (no Zookeeper in 3.7+) | Zookeeper/KRaft | None (Raft consensus) |
| **Performance** | High | High + Enterprise features | Very High (C++ optimized) |
| **Ecosystem** | Extensive | Most Extensive | Growing |
| **Management** | Basic tools | Advanced tooling | Simple management |
| **Support** | Community | Commercial available | Commercial |

## 📈 Test Scenarios

### Built-in Scenarios
1. **Baseline Performance**: Default configuration comparison
2. **High Throughput**: Maximum sustainable throughput
3. **Low Latency**: Sub-millisecond latency requirements
4. **Mixed Workloads**: Concurrent high-throughput and low-latency
5. **Scalability**: Partition and consumer scaling behavior
6. **Failure Recovery**: Broker failures and network partitions
7. **Resource Efficiency**: Performance per CPU/memory unit

### Custom Scenarios
```yaml
# Example: testing/scenarios/custom-scenario.yml
test_scenario:
  name: "Custom High Volume Test"
  duration: "60m"
  platforms: ["kafka", "redpanda"]
  
  producer_config:
    message_size: 4096
    batch_size: 32768
    compression: "zstd"
    target_throughput: 200000
    
  consumer_config:
    consumer_groups: 5
    max_poll_records: 2000
    
  metrics:
    - throughput
    - latency_p99
    - cpu_usage
    - memory_usage
    - disk_io
```

## 🔧 Configuration

### Environment Variables
```bash
# Resource allocation
KAFKA_HEAP_SIZE=8G
REDPANDA_MEMORY=8G

# Test parameters
TEST_DURATION=30m
MESSAGE_SIZE=1024
TARGET_THROUGHPUT=100000

# Monitoring
METRICS_SCRAPE_INTERVAL=15s
ALERT_EVALUATION_INTERVAL=15s
```

### Platform-Specific Configurations
- **Kafka**: `configs/kafka-*.yml`
- **Redpanda**: `configs/redpanda-*.yml`
- **Monitoring**: `docker/monitoring/configs/`

## 📊 Results & Reports

### Automated Reports
- **Daily**: Performance monitoring and trend analysis
- **Weekly**: Comprehensive comparison and optimization progress
- **Monthly**: Strategic analysis and recommendations

### Export Formats
- PDF reports with charts and analysis
- CSV data for custom analysis
- JSON/XML for API integration
- PowerBI/Tableau connectors

## 🚨 Alerting

### Alert Categories
- **Critical**: Broker failures, data loss, severe performance degradation
- **Warning**: High resource usage, performance deviation, consumer lag
- **Info**: Configuration changes, test completion, optimization results

### Notification Channels
- Email notifications
- Slack/Teams integration
- Webhook endpoints
- Dashboard alerts

## 🔄 CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/performance-testing.yml
name: Performance Testing Pipeline
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  performance-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run performance comparison
        run: ./scripts/quick-comparison.sh
```

## 🛠️ Development

### Project Structure
```
kafka-performance-comparison/
├── docker/                 # Docker configurations
│   ├── kafka/             # Kafka cluster setup
│   ├── redpanda/          # Redpanda cluster setup
│   └── monitoring/        # Monitoring stack
├── scripts/               # Automation scripts
├── configs/               # Configuration files
├── testing/               # Test scenarios and clients
├── results/               # Test results and reports
├── docs/                  # Documentation
└── memory-bank/           # Project context and decisions
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📚 Documentation

- [Setup Guide](docs/setup-guide.md)
- [Testing Guide](docs/testing-guide.md)
- [Configuration Guide](docs/configuration-guide.md)
- [Troubleshooting](docs/troubleshooting.md)
- [API Reference](docs/api-reference.md)

## 🐛 Troubleshooting

### Common Issues
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs [service-name]

# Restart services
docker-compose restart [service-name]

# Clean restart
docker-compose down && docker-compose up -d
```

### Health Checks
```bash
# Run system health check
./scripts/health-check.sh

# Validate configurations
./scripts/validate-configs.sh

# Generate diagnostic report
./scripts/generate-diagnostics.sh
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: [docs/](docs/)
- **Examples**: [examples/](examples/)

## 🙏 Acknowledgments

- Apache Kafka community
- Redpanda team
- Prometheus and Grafana projects
- Docker and containerization ecosystem

---

**Made with ❤️ for performance engineering**
