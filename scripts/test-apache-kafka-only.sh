#!/bin/bash

# Apache Kafka-Only Performance Testing Script
# This script tests only pure Apache Kafka performance (not Confluent)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"; }

# Configuration
TEST_DURATION=${TEST_DURATION:-"10m"}
MESSAGE_SIZE=${MESSAGE_SIZE:-1024}
TARGET_THROUGHPUT=${TARGET_THROUGHPUT:-50000}
TOPIC_NAME="apache-kafka-perf-test-$(date +%s)"
PARTITIONS=6
REPLICATION_FACTOR=3
NUM_RECORDS=${NUM_RECORDS:-1000000}

# Check if monitoring is running
check_monitoring() {
    log "Checking monitoring stack..."
    
    if ! curl -s http://localhost:9090/api/v1/status/config > /dev/null; then
        warn "Prometheus is not running. Starting monitoring stack..."
        docker-compose -f docker/monitoring/docker-compose.yml up -d
        sleep 30
    fi
    
    log "Monitoring stack is ready."
}

# Start Apache Kafka environment only
start_apache_kafka() {
    log "Starting Apache Kafka environment..."
    
    # Stop other Kafka instances if running to avoid conflicts
    info "Stopping any running Kafka instances..."
    docker-compose -f docker/kafka/docker-compose.yml down 2>/dev/null || true
    docker-compose -f docker/redpanda/docker-compose.yml down 2>/dev/null || true
    
    # Start Apache Kafka
    cd docker/apache-kafka
    docker-compose up -d
    cd ../..
    
    # Wait for Apache Kafka to be ready
    info "Waiting for Apache Kafka brokers to be ready..."
    sleep 90
    
    # Check if Apache Kafka is ready
    for i in {1..30}; do
        if docker exec apache-kafka-1 bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 &>/dev/null; then
            log "Apache Kafka is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Apache Kafka failed to start within timeout"
            exit 1
        fi
        sleep 5
    done
}

# Create Apache Kafka test topic
create_apache_kafka_topic() {
    log "Creating Apache Kafka test topic: ${TOPIC_NAME}"
    
    docker exec apache-kafka-1 bin/kafka-topics.sh \
        --create \
        --topic "${TOPIC_NAME}" \
        --partitions ${PARTITIONS} \
        --replication-factor ${REPLICATION_FACTOR} \
        --bootstrap-server localhost:9092 \
        --config min.insync.replicas=2 \
        --config retention.ms=3600000
    
    # Verify topic creation
    docker exec apache-kafka-1 bin/kafka-topics.sh \
        --describe \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092
}

# Run Apache Kafka producer performance test
test_apache_kafka_producer() {
    log "Running Apache Kafka producer performance test..."
    
    local results_dir="results/apache-kafka-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Producer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Records: ${NUM_RECORDS}"
    echo "  - Record size: ${MESSAGE_SIZE} bytes"
    echo "  - Target throughput: ${TARGET_THROUGHPUT} records/sec"
    echo "  - Test duration: ${TEST_DURATION}"
    echo "  - Apache Kafka Version: 3.7.0"
    
    # Run producer performance test using native Apache Kafka tools
    docker exec apache-kafka-1 bin/kafka-producer-perf-test.sh \
        --topic "${TOPIC_NAME}" \
        --num-records ${NUM_RECORDS} \
        --record-size ${MESSAGE_SIZE} \
        --throughput ${TARGET_THROUGHPUT} \
        --producer-props \
            bootstrap.servers=localhost:9092 \
            acks=1 \
            batch.size=16384 \
            linger.ms=5 \
            compression.type=lz4 \
            buffer.memory=33554432 \
        | tee "${results_dir}/producer-results.txt"
    
    log "Apache Kafka producer test completed. Results saved to: ${results_dir}/producer-results.txt"
}

# Run Apache Kafka consumer performance test
test_apache_kafka_consumer() {
    log "Running Apache Kafka consumer performance test..."
    
    local results_dir="results/apache-kafka-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Consumer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Messages: ${NUM_RECORDS}"
    echo "  - Consumer group: apache-kafka-perf-test-group"
    
    # Run consumer performance test using native Apache Kafka tools
    timeout ${TEST_DURATION} docker exec apache-kafka-1 bin/kafka-consumer-perf-test.sh \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --messages ${NUM_RECORDS} \
        --group "apache-kafka-perf-test-group" \
        --consumer-props \
            fetch.min.bytes=1 \
            fetch.max.wait.ms=500 \
            max.poll.records=500 \
        | tee "${results_dir}/consumer-results.txt" || true
    
    log "Apache Kafka consumer test completed. Results saved to: ${results_dir}/consumer-results.txt"
}

# Run concurrent producer/consumer test
test_apache_kafka_concurrent() {
    log "Running Apache Kafka concurrent producer/consumer test..."
    
    local results_dir="results/apache-kafka-concurrent-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Starting concurrent producer and consumer..."
    
    # Start consumer in background
    timeout ${TEST_DURATION} docker exec apache-kafka-1 bin/kafka-consumer-perf-test.sh \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --messages ${NUM_RECORDS} \
        --group "apache-kafka-concurrent-group" \
        > "${results_dir}/concurrent-consumer-results.txt" &
    
    local consumer_pid=$!
    sleep 5
    
    # Start producer
    docker exec apache-kafka-1 bin/kafka-producer-perf-test.sh \
        --topic "${TOPIC_NAME}" \
        --num-records ${NUM_RECORDS} \
        --record-size ${MESSAGE_SIZE} \
        --throughput ${TARGET_THROUGHPUT} \
        --producer-props \
            bootstrap.servers=localhost:9092 \
            acks=1 \
            batch.size=16384 \
            linger.ms=5 \
            compression.type=lz4 \
        > "${results_dir}/concurrent-producer-results.txt"
    
    # Wait for consumer to finish
    wait $consumer_pid 2>/dev/null || true
    
    log "Apache Kafka concurrent test completed. Results saved to: ${results_dir}/"
}

# Get Apache Kafka cluster information
get_apache_kafka_info() {
    log "Gathering Apache Kafka cluster information..."
    
    local results_dir="results/apache-kafka-info-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Broker information
    docker exec apache-kafka-1 bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 \
        > "${results_dir}/broker-info.txt" 2>&1
    
    # Topic information
    docker exec apache-kafka-1 bin/kafka-topics.sh --list --bootstrap-server localhost:9092 \
        > "${results_dir}/topics-list.txt" 2>&1
    
    # Consumer groups
    docker exec apache-kafka-1 bin/kafka-consumer-groups.sh --list --bootstrap-server localhost:9092 \
        > "${results_dir}/consumer-groups.txt" 2>&1
    
    # Log directories
    docker exec apache-kafka-1 bin/kafka-log-dirs.sh --bootstrap-server localhost:9092 --describe \
        > "${results_dir}/log-dirs.txt" 2>&1
    
    # Kafka version and configuration
    docker exec apache-kafka-1 bin/kafka-configs.sh --bootstrap-server localhost:9092 --entity-type brokers --describe \
        > "${results_dir}/broker-configs.txt" 2>&1
    
    log "Apache Kafka cluster information saved to: ${results_dir}/"
}

# Test Apache Kafka native tools
test_apache_kafka_native() {
    log "Running Apache Kafka native tools test..."
    
    local results_dir="results/apache-kafka-native-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Test console producer
    info "Testing console producer..."
    echo "Test message from Apache Kafka console producer" | \
    docker exec -i apache-kafka-1 bin/kafka-console-producer.sh \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        > "${results_dir}/console-producer-results.txt" 2>&1
    
    # Test console consumer
    info "Testing console consumer..."
    timeout 10s docker exec apache-kafka-1 bin/kafka-console-consumer.sh \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --from-beginning \
        --max-messages 5 \
        > "${results_dir}/console-consumer-results.txt" 2>&1 || true
    
    # Test metadata
    docker exec apache-kafka-1 bin/kafka-metadata.sh \
        --bootstrap-server localhost:9092 \
        > "${results_dir}/metadata-results.txt" 2>&1 || true
    
    log "Apache Kafka native tools test completed. Results saved to: ${results_dir}/"
}

# Generate Apache Kafka performance report
generate_apache_kafka_report() {
    log "Generating Apache Kafka performance report..."
    
    local report_file="results/apache-kafka-performance-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "${report_file}" <<EOF
# Apache Kafka Performance Test Report

**Test Date:** $(date)
**Test Duration:** ${TEST_DURATION}
**Message Size:** ${MESSAGE_SIZE} bytes
**Target Throughput:** ${TARGET_THROUGHPUT} messages/sec
**Topic:** ${TOPIC_NAME}
**Partitions:** ${PARTITIONS}
**Replication Factor:** ${REPLICATION_FACTOR}

## Test Configuration

- **Apache Kafka Version:** 3.7.0 (Official Apache Image)
- **Cluster Size:** 3 brokers
- **Mode:** KRaft (Kafka Raft) - No Zookeeper
- **JVM Heap:** 4GB per broker

## Apache Kafka Features Tested

- **KRaft Mode:** No Zookeeper dependency (Kafka 2.8+)
- **Native Performance Tools:** kafka-producer-perf-test.sh, kafka-consumer-perf-test.sh
- **Official Apache Distribution:** Pure Apache Kafka without Confluent additions
- **Java-based Implementation:** JVM optimizations and garbage collection tuning

## Producer Configuration
\`\`\`
bootstrap.servers=localhost:9092
acks=1
batch.size=16384
linger.ms=5
compression.type=lz4
buffer.memory=33554432
\`\`\`

## Consumer Configuration
\`\`\`
fetch.min.bytes=1
fetch.max.wait.ms=500
max.poll.records=500
\`\`\`

## Results Summary

### Producer Performance
\`\`\`
$(find results -name "*apache-kafka*" -path "*/producer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No producer results found")
\`\`\`

### Consumer Performance
\`\`\`
$(find results -name "*apache-kafka*" -path "*/consumer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No consumer results found")
\`\`\`

## Apache Kafka vs Confluent Kafka

### Apache Kafka (This Test)
- **Distribution:** Official Apache Foundation
- **License:** Apache 2.0
- **Features:** Core Kafka functionality
- **Tools:** Native Apache Kafka tools
- **Support:** Community support

### Confluent Kafka (Alternative)
- **Distribution:** Confluent Platform
- **License:** Confluent Community License
- **Features:** Additional enterprise features
- **Tools:** Enhanced tooling and management
- **Support:** Commercial support available

## Monitoring Access

- **Apache Kafka UI:** http://localhost:8083
- **Grafana Dashboard:** http://localhost:3000
- **Prometheus Metrics:** http://localhost:9090
- **Kafka Exporter:** http://localhost:9308/metrics

## Resource Utilization

Check Grafana dashboards for detailed resource utilization:
- CPU usage per broker
- Memory consumption and GC patterns
- Disk I/O patterns
- Network throughput

## Next Steps

1. Compare with Redpanda results using \`./scripts/test-redpanda-only.sh\`
2. Compare with Confluent Kafka using \`./scripts/test-kafka-only.sh\`
3. Analyze detailed metrics in Grafana
4. Optimize configuration based on results
5. Run extended tests with different message sizes

---
*Generated by test-apache-kafka-only.sh*
EOF

    log "Apache Kafka performance report generated: ${report_file}"
}

# Cleanup function
cleanup() {
    log "Cleaning up Apache Kafka test resources..."
    
    # Delete test topic
    docker exec apache-kafka-1 bin/kafka-topics.sh --delete --topic "${TOPIC_NAME}" --bootstrap-server localhost:9092 2>/dev/null || true
    
    log "Cleanup completed."
}

# Display access information
display_apache_kafka_info() {
    log "Apache Kafka performance test completed!"
    echo
    info "Access your Apache Kafka environment:"
    echo "- Apache Kafka UI: http://localhost:8083"
    echo "- Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    echo "- Prometheus Metrics: http://localhost:9090"
    echo "- Kafka Exporter: http://localhost:9308/metrics"
    echo "- Results Directory: results/"
    echo
    info "Apache Kafka cluster endpoints:"
    echo "- Broker 1: localhost:9092"
    echo "- Broker 2: localhost:9093" 
    echo "- Broker 3: localhost:9094"
    echo
    info "To test other platforms:"
    echo "- Confluent Kafka: ./scripts/test-kafka-only.sh"
    echo "- Redpanda: ./scripts/test-redpanda-only.sh"
    echo
    info "To stop Apache Kafka:"
    echo "- Run: docker-compose -f docker/apache-kafka/docker-compose.yml down"
}

# Main execution
main() {
    log "Starting Apache Kafka-only performance testing..."
    
    # Create results directory
    mkdir -p results
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    check_monitoring
    start_apache_kafka
    create_apache_kafka_topic
    get_apache_kafka_info
    
    # Run performance tests
    test_apache_kafka_producer
    sleep 10
    test_apache_kafka_consumer
    sleep 10
    test_apache_kafka_concurrent
    test_apache_kafka_native
    
    generate_apache_kafka_report
    display_apache_kafka_info
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [options]"
        echo "Options:"
        echo "  --help, -h              Show this help message"
        echo "  --duration DURATION     Set test duration (default: 10m)"
        echo "  --throughput NUM        Set target throughput (default: 50000)"
        echo "  --message-size SIZE     Set message size in bytes (default: 1024)"
        echo "  --records NUM           Set number of records (default: 1000000)"
        echo
        echo "Environment variables:"
        echo "  TEST_DURATION           Test duration (default: 10m)"
        echo "  MESSAGE_SIZE            Message size in bytes (default: 1024)"
        echo "  TARGET_THROUGHPUT       Target throughput (default: 50000)"
        echo "  NUM_RECORDS             Number of records (default: 1000000)"
        echo
        echo "This script tests pure Apache Kafka (not Confluent Kafka)"
        exit 0
        ;;
    --duration)
        TEST_DURATION="$2"
        shift 2
        ;;
    --throughput)
        TARGET_THROUGHPUT="$2"
        shift 2
        ;;
    --message-size)
        MESSAGE_SIZE="$2"
        shift 2
        ;;
    --records)
        NUM_RECORDS="$2"
        shift 2
        ;;
esac

# Run main function
main "$@"