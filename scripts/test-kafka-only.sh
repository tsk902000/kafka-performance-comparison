#!/bin/bash

# Kafka-Only Performance Testing Script
# This script tests only Apache Kafka performance

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
TOPIC_NAME="kafka-perf-test-$(date +%s)"
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

# Start Kafka environment only
start_kafka() {
    log "Starting Kafka environment..."
    
    # Stop Redpanda if running to avoid conflicts
    info "Stopping any running Redpanda instances..."
    docker-compose -f docker/redpanda/docker-compose.yml down 2>/dev/null || true
    
    # Start Kafka
    cd docker/kafka
    docker-compose up -d
    cd ../..
    
    # Wait for Kafka to be ready
    info "Waiting for Kafka brokers to be ready..."
    sleep 60
    
    # Check if Kafka is ready
    for i in {1..30}; do
        if docker exec kafka-broker-1 kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; then
            log "Kafka is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Kafka failed to start within timeout"
            exit 1
        fi
        sleep 5
    done
}

# Create Kafka test topic
create_kafka_topic() {
    log "Creating Kafka test topic: ${TOPIC_NAME}"
    
    docker exec kafka-broker-1 kafka-topics \
        --create \
        --topic "${TOPIC_NAME}" \
        --partitions ${PARTITIONS} \
        --replication-factor ${REPLICATION_FACTOR} \
        --bootstrap-server localhost:9092 \
        --config min.insync.replicas=2 \
        --config retention.ms=3600000
    
    # Verify topic creation
    docker exec kafka-broker-1 kafka-topics \
        --describe \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092
}

# Run Kafka producer performance test
test_kafka_producer() {
    log "Running Kafka producer performance test..."
    
    local results_dir="results/kafka-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Producer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Records: ${NUM_RECORDS}"
    echo "  - Record size: ${MESSAGE_SIZE} bytes"
    echo "  - Target throughput: ${TARGET_THROUGHPUT} records/sec"
    echo "  - Test duration: ${TEST_DURATION}"
    
    # Run producer performance test
    docker exec kafka-broker-1 kafka-producer-perf-test \
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
    
    log "Kafka producer test completed. Results saved to: ${results_dir}/producer-results.txt"
}

# Run Kafka consumer performance test
test_kafka_consumer() {
    log "Running Kafka consumer performance test..."
    
    local results_dir="results/kafka-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Consumer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Messages: ${NUM_RECORDS}"
    echo "  - Consumer group: kafka-perf-test-group"
    
    # Run consumer performance test
    timeout ${TEST_DURATION} docker exec kafka-broker-1 kafka-consumer-perf-test \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --messages ${NUM_RECORDS} \
        --group "kafka-perf-test-group" \
        --consumer-props \
            fetch.min.bytes=1 \
            fetch.max.wait.ms=500 \
            max.poll.records=500 \
        | tee "${results_dir}/consumer-results.txt" || true
    
    log "Kafka consumer test completed. Results saved to: ${results_dir}/consumer-results.txt"
}

# Run concurrent producer/consumer test
test_kafka_concurrent() {
    log "Running Kafka concurrent producer/consumer test..."
    
    local results_dir="results/kafka-concurrent-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Starting concurrent producer and consumer..."
    
    # Start consumer in background
    timeout ${TEST_DURATION} docker exec kafka-broker-1 kafka-consumer-perf-test \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server localhost:9092 \
        --messages ${NUM_RECORDS} \
        --group "kafka-concurrent-group" \
        > "${results_dir}/concurrent-consumer-results.txt" &
    
    local consumer_pid=$!
    sleep 5
    
    # Start producer
    docker exec kafka-broker-1 kafka-producer-perf-test \
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
    
    log "Kafka concurrent test completed. Results saved to: ${results_dir}/"
}

# Get Kafka cluster information
get_kafka_info() {
    log "Gathering Kafka cluster information..."
    
    local results_dir="results/kafka-info-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Broker information
    docker exec kafka-broker-1 kafka-broker-api-versions --bootstrap-server localhost:9092 \
        > "${results_dir}/broker-info.txt" 2>&1
    
    # Topic information
    docker exec kafka-broker-1 kafka-topics --list --bootstrap-server localhost:9092 \
        > "${results_dir}/topics-list.txt" 2>&1
    
    # Consumer groups
    docker exec kafka-broker-1 kafka-consumer-groups --list --bootstrap-server localhost:9092 \
        > "${results_dir}/consumer-groups.txt" 2>&1
    
    # Log directories
    docker exec kafka-broker-1 kafka-log-dirs --bootstrap-server localhost:9092 --describe \
        > "${results_dir}/log-dirs.txt" 2>&1
    
    log "Kafka cluster information saved to: ${results_dir}/"
}

# Generate Kafka performance report
generate_kafka_report() {
    log "Generating Kafka performance report..."
    
    local report_file="results/kafka-performance-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "${report_file}" <<EOF
# Kafka Performance Test Report

**Test Date:** $(date)
**Test Duration:** ${TEST_DURATION}
**Message Size:** ${MESSAGE_SIZE} bytes
**Target Throughput:** ${TARGET_THROUGHPUT} messages/sec
**Topic:** ${TOPIC_NAME}
**Partitions:** ${PARTITIONS}
**Replication Factor:** ${REPLICATION_FACTOR}

## Test Configuration

- **Kafka Version:** confluentinc/cp-kafka:7.4.0
- **Cluster Size:** 3 brokers
- **Zookeeper:** Single instance
- **JVM Heap:** 4GB per broker

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
$(find results -name "*kafka*" -path "*/producer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No producer results found")
\`\`\`

### Consumer Performance
\`\`\`
$(find results -name "*kafka*" -path "*/consumer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No consumer results found")
\`\`\`

## Monitoring Access

- **Grafana Dashboard:** http://localhost:3000
- **Prometheus Metrics:** http://localhost:9090
- **Kafka UI:** http://localhost:8081

## Resource Utilization

Check Grafana dashboards for detailed resource utilization:
- CPU usage per broker
- Memory consumption
- Disk I/O patterns
- Network throughput

## Next Steps

1. Compare with Redpanda results using \`./scripts/test-redpanda-only.sh\`
2. Analyze detailed metrics in Grafana
3. Optimize configuration based on results
4. Run extended tests with different message sizes

---
*Generated by test-kafka-only.sh*
EOF

    log "Kafka performance report generated: ${report_file}"
}

# Cleanup function
cleanup() {
    log "Cleaning up Kafka test resources..."
    
    # Delete test topic
    docker exec kafka-broker-1 kafka-topics --delete --topic "${TOPIC_NAME}" --bootstrap-server localhost:9092 2>/dev/null || true
    
    log "Cleanup completed."
}

# Display access information
display_kafka_info() {
    log "Kafka performance test completed!"
    echo
    info "Access your Kafka environment:"
    echo "- Kafka UI: http://localhost:8081"
    echo "- Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    echo "- Prometheus Metrics: http://localhost:9090"
    echo "- Results Directory: results/"
    echo
    info "Kafka cluster endpoints:"
    echo "- Broker 1: localhost:9092"
    echo "- Broker 2: localhost:9093" 
    echo "- Broker 3: localhost:9094"
    echo
    info "To test Redpanda separately:"
    echo "- Run: ./scripts/test-redpanda-only.sh"
    echo
    info "To stop Kafka:"
    echo "- Run: docker-compose -f docker/kafka/docker-compose.yml down"
}

# Main execution
main() {
    log "Starting Kafka-only performance testing..."
    
    # Create results directory
    mkdir -p results
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    check_monitoring
    start_kafka
    create_kafka_topic
    get_kafka_info
    
    # Run performance tests
    test_kafka_producer
    sleep 10
    test_kafka_consumer
    sleep 10
    test_kafka_concurrent
    
    generate_kafka_report
    display_kafka_info
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