#!/bin/bash

# Kafka vs Redpanda Performance Comparison Setup Script
# This script sets up the entire environment for performance testing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if Docker is installed and running
check_docker() {
    log "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    log "Docker and Docker Compose are installed and running."
}

# Check system requirements
check_system_requirements() {
    log "Checking system requirements..."
    
    # Check available memory
    TOTAL_MEM=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$TOTAL_MEM" -lt 16 ]; then
        warn "System has ${TOTAL_MEM}GB RAM. Recommended: 16GB+ for optimal performance."
    else
        log "Memory check passed: ${TOTAL_MEM}GB available."
    fi
    
    # Check available disk space
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 100 ]; then
        warn "Available disk space: ${AVAILABLE_SPACE}GB. Recommended: 100GB+ for testing data."
    else
        log "Disk space check passed: ${AVAILABLE_SPACE}GB available."
    fi
    
    # Check CPU cores
    CPU_CORES=$(nproc)
    if [ "$CPU_CORES" -lt 8 ]; then
        warn "System has ${CPU_CORES} CPU cores. Recommended: 8+ cores for optimal performance."
    else
        log "CPU check passed: ${CPU_CORES} cores available."
    fi
}

# Create necessary directories
create_directories() {
    log "Creating project directories..."
    
    mkdir -p {configs,results,logs,scripts,testing,docs}
    mkdir -p {configs/kafka,configs/redpanda,configs/monitoring}
    mkdir -p {results/reports,results/raw-data,results/charts}
    mkdir -p {testing/scenarios,testing/clients,testing/benchmarks}
    mkdir -p {logs/kafka,logs/redpanda,logs/monitoring}
    
    log "Project directories created successfully."
}

# Set up Docker networks
setup_networks() {
    log "Setting up Docker networks..."
    
    # Create networks if they don't exist
    docker network create kafka-network 2>/dev/null || true
    docker network create redpanda-network 2>/dev/null || true
    docker network create monitoring-network 2>/dev/null || true
    
    log "Docker networks configured successfully."
}

# Configure system settings for optimal performance
configure_system() {
    log "Configuring system settings for optimal performance..."
    
    # Increase vm.max_map_count for Elasticsearch
    if [ "$(sysctl -n vm.max_map_count)" -lt 262144 ]; then
        info "Increasing vm.max_map_count for Elasticsearch..."
        echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
        sudo sysctl -p
    fi
    
    # Increase file descriptor limits
    if [ ! -f /etc/security/limits.d/kafka-performance.conf ]; then
        info "Setting file descriptor limits..."
        sudo tee /etc/security/limits.d/kafka-performance.conf > /dev/null <<EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 32768
* hard nproc 32768
EOF
    fi
    
    log "System configuration completed."
}

# Create environment file
create_env_file() {
    log "Creating environment configuration file..."
    
    if [ ! -f .env ]; then
        cat > .env <<EOF
# Kafka vs Redpanda Performance Comparison Environment Configuration

# System Configuration
COMPOSE_PROJECT_NAME=kafka-redpanda-comparison
COMPOSE_FILE_SEPARATOR=:

# Resource Allocation
KAFKA_HEAP_SIZE=4G
REDPANDA_MEMORY=4G
PROMETHEUS_RETENTION=30d
GRAFANA_ADMIN_PASSWORD=admin123

# Network Configuration
KAFKA_EXTERNAL_PORT_START=9092
REDPANDA_EXTERNAL_PORT_START=19092
MONITORING_PORT_START=3000

# Testing Configuration
TEST_DURATION=30m
CONCURRENT_PRODUCERS=10
CONCURRENT_CONSUMERS=10
MESSAGE_SIZE=1024
BATCH_SIZE=16384

# Monitoring Configuration
METRICS_SCRAPE_INTERVAL=15s
ALERT_EVALUATION_INTERVAL=15s
LOG_RETENTION_DAYS=7

# Performance Testing
BASELINE_THROUGHPUT_TARGET=50000
LATENCY_SLA_P99_MS=100
ERROR_RATE_THRESHOLD=0.1

# Database Configuration
POSTGRES_DB=performance_db
POSTGRES_USER=perf_user
POSTGRES_PASSWORD=perf_password

# Security (Change in production)
GRAFANA_ADMIN_USER=admin
ALERT_WEBHOOK_SECRET=change-me-in-production
EOF
        log "Environment file created: .env"
    else
        info "Environment file already exists: .env"
    fi
}

# Pull Docker images
pull_images() {
    log "Pulling required Docker images..."
    
    # Kafka images
    docker pull confluentinc/cp-zookeeper:7.4.0
    docker pull confluentinc/cp-kafka:7.4.0
    docker pull provectuslabs/kafka-ui:latest
    
    # Redpanda images
    docker pull redpandadata/redpanda:v23.2.15
    docker pull redpandadata/console:v2.3.1
    
    # Monitoring images
    docker pull prom/prometheus:v2.47.0
    docker pull grafana/grafana:10.1.0
    docker pull prom/alertmanager:v0.26.0
    docker pull prom/node-exporter:v1.6.1
    docker pull gcr.io/cadvisor/cadvisor:v0.47.2
    docker pull jaegertracing/all-in-one:1.49
    
    # ELK Stack
    docker pull docker.elastic.co/elasticsearch/elasticsearch:8.9.0
    docker pull docker.elastic.co/kibana/kibana:8.9.0
    docker pull docker.elastic.co/logstash/logstash:8.9.0
    
    # Database and cache
    docker pull postgres:15-alpine
    docker pull redis:7.2-alpine
    
    # Exporters
    docker pull bitnami/jmx-exporter:1.4.0
    docker pull danielqsj/kafka-exporter:latest
    
    # Apache Kafka images
    docker pull apache/kafka:3.7.0
    
    log "Docker images pulled successfully."
}

# Start monitoring stack
start_monitoring() {
    log "Starting monitoring stack..."
    
    cd docker/monitoring
    docker-compose up -d
    cd ../..
    
    # Wait for services to be ready
    info "Waiting for monitoring services to start..."
    sleep 30
    
    # Check if services are running
    if curl -s http://localhost:9090/api/v1/status/config > /dev/null; then
        log "Prometheus is running at http://localhost:9090"
    else
        warn "Prometheus may not be ready yet. Check logs: docker-compose -f docker/monitoring/docker-compose.yml logs prometheus"
    fi
    
    if curl -s http://localhost:3000/api/health > /dev/null; then
        log "Grafana is running at http://localhost:3000 (admin/admin123)"
    else
        warn "Grafana may not be ready yet. Check logs: docker-compose -f docker/monitoring/docker-compose.yml logs grafana"
    fi
}

# Create sample configuration files
create_sample_configs() {
    log "Creating sample configuration files..."
    
    # Kafka baseline configuration
    cat > configs/kafka-baseline.yml <<EOF
# Kafka Baseline Configuration
producer:
  bootstrap.servers: "localhost:9092,localhost:9093,localhost:9094"
  key.serializer: "org.apache.kafka.common.serialization.StringSerializer"
  value.serializer: "org.apache.kafka.common.serialization.StringSerializer"
  acks: "1"
  retries: 3
  batch.size: 16384
  linger.ms: 5
  buffer.memory: 33554432
  compression.type: "lz4"

consumer:
  bootstrap.servers: "localhost:9092,localhost:9093,localhost:9094"
  key.deserializer: "org.apache.kafka.common.serialization.StringDeserializer"
  value.deserializer: "org.apache.kafka.common.serialization.StringDeserializer"
  group.id: "performance-test-group"
  auto.offset.reset: "earliest"
  enable.auto.commit: true
  auto.commit.interval.ms: 1000
  session.timeout.ms: 30000
  fetch.min.bytes: 1
  fetch.max.wait.ms: 500
  max.poll.records: 500
EOF

    # Redpanda baseline configuration
    cat > configs/redpanda-baseline.yml <<EOF
# Redpanda Baseline Configuration
producer:
  bootstrap.servers: "localhost:19092,localhost:19093,localhost:19094"
  key.serializer: "org.apache.kafka.common.serialization.StringSerializer"
  value.serializer: "org.apache.kafka.common.serialization.StringSerializer"
  acks: "1"
  retries: 3
  batch.size: 16384
  linger.ms: 5
  buffer.memory: 33554432
  compression.type: "lz4"

consumer:
  bootstrap.servers: "localhost:19092,localhost:19093,localhost:19094"
  key.deserializer: "org.apache.kafka.common.serialization.StringDeserializer"
  value.deserializer: "org.apache.kafka.common.serialization.StringDeserializer"
  group.id: "performance-test-group"
  auto.offset.reset: "earliest"
  enable.auto.commit: true
  auto.commit.interval.ms: 1000
  session.timeout.ms: 30000
  fetch.min.bytes: 1
  fetch.max.wait.ms: 500
  max.poll.records: 500
EOF

    log "Sample configuration files created."
}

# Display setup completion message
display_completion() {
    log "Setup completed successfully!"
    echo
    info "Next steps:"
    echo "1. Start Kafka environment: docker-compose -f docker/kafka/docker-compose.yml up -d"
    echo "2. Start Redpanda environment: docker-compose -f docker/redpanda/docker-compose.yml up -d"
    echo "3. Run performance tests: ./scripts/run-comparison.sh"
    echo
    info "Access points:"
    echo "- Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    echo "- Prometheus: http://localhost:9090"
    echo "- Kafka UI: http://localhost:8081"
    echo "- Redpanda Console: http://localhost:8082"
    echo "- Jaeger Tracing: http://localhost:16686"
    echo "- Kibana: http://localhost:5601"
    echo
    info "For help and documentation, see: docs/README.md"
}

# Main execution
main() {
    log "Starting Kafka vs Redpanda Performance Comparison setup..."
    
    check_docker
    check_system_requirements
    create_directories
    setup_networks
    configure_system
    create_env_file
    pull_images
    start_monitoring
    create_sample_configs
    display_completion
}

# Run main function
main "$@"