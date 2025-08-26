#!/bin/bash

# Redpanda-Only Performance Testing Script
# This script tests only Redpanda performance

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
TOPIC_NAME="redpanda-perf-test-$(date +%s)"
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

# Start Redpanda environment only
start_redpanda() {
    log "Starting Redpanda environment..."
    
    # Stop Kafka if running to avoid conflicts
    info "Stopping any running Kafka instances..."
    docker-compose -f docker/kafka/docker-compose.yml down 2>/dev/null || true
    
    # Start Redpanda
    cd docker/redpanda
    docker-compose up -d
    cd ../..
    
    # Wait for Redpanda to be ready
    info "Waiting for Redpanda brokers to be ready..."
    sleep 60
    
    # Check if Redpanda is ready
    for i in {1..30}; do
        if docker exec redpanda-1 rpk cluster health &>/dev/null; then
            log "Redpanda is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            error "Redpanda failed to start within timeout"
            exit 1
        fi
        sleep 5
    done
}

# Create Redpanda test topic
create_redpanda_topic() {
    log "Creating Redpanda test topic: ${TOPIC_NAME}"
    
    docker exec redpanda-1 rpk topic create "${TOPIC_NAME}" \
        --partitions ${PARTITIONS} \
        --replicas ${REPLICATION_FACTOR} \
        --config retention.ms=3600000
    
    # Verify topic creation
    docker exec redpanda-1 rpk topic describe "${TOPIC_NAME}"
}

# Run Redpanda producer performance test using kafka-producer-perf-test
test_redpanda_producer() {
    log "Running Redpanda producer performance test..."
    
    local results_dir="results/redpanda-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Producer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Records: ${NUM_RECORDS}"
    echo "  - Record size: ${MESSAGE_SIZE} bytes"
    echo "  - Target throughput: ${TARGET_THROUGHPUT} records/sec"
    echo "  - Test duration: ${TEST_DURATION}"
    
    # Use Kafka tools to test Redpanda (Kafka-compatible)
    docker run --rm --network redpanda-network \
        confluentinc/cp-kafka:7.4.0 \
        kafka-producer-perf-test \
        --topic "${TOPIC_NAME}" \
        --num-records ${NUM_RECORDS} \
        --record-size ${MESSAGE_SIZE} \
        --throughput ${TARGET_THROUGHPUT} \
        --producer-props \
            bootstrap.servers=redpanda-1:9092,redpanda-2:9092,redpanda-3:9092 \
            acks=1 \
            batch.size=16384 \
            linger.ms=5 \
            compression.type=lz4 \
            buffer.memory=33554432 \
        | tee "${results_dir}/producer-results.txt"
    
    log "Redpanda producer test completed. Results saved to: ${results_dir}/producer-results.txt"
}

# Run Redpanda consumer performance test using kafka-consumer-perf-test
test_redpanda_consumer() {
    log "Running Redpanda consumer performance test..."
    
    local results_dir="results/redpanda-only-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Consumer test parameters:"
    echo "  - Topic: ${TOPIC_NAME}"
    echo "  - Messages: ${NUM_RECORDS}"
    echo "  - Consumer group: redpanda-perf-test-group"
    
    # Use Kafka tools to test Redpanda (Kafka-compatible)
    timeout ${TEST_DURATION} docker run --rm --network redpanda-network \
        confluentinc/cp-kafka:7.4.0 \
        kafka-consumer-perf-test \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server redpanda-1:9092,redpanda-2:9092,redpanda-3:9092 \
        --messages ${NUM_RECORDS} \
        --group "redpanda-perf-test-group" \
        --consumer-props \
            fetch.min.bytes=1 \
            fetch.max.wait.ms=500 \
            max.poll.records=500 \
        | tee "${results_dir}/consumer-results.txt" || true
    
    log "Redpanda consumer test completed. Results saved to: ${results_dir}/consumer-results.txt"
}

# Run concurrent producer/consumer test
test_redpanda_concurrent() {
    log "Running Redpanda concurrent producer/consumer test..."
    
    local results_dir="results/redpanda-concurrent-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    info "Starting concurrent producer and consumer..."
    
    # Start consumer in background
    timeout ${TEST_DURATION} docker run --rm --network redpanda-network \
        confluentinc/cp-kafka:7.4.0 \
        kafka-consumer-perf-test \
        --topic "${TOPIC_NAME}" \
        --bootstrap-server redpanda-1:9092,redpanda-2:9092,redpanda-3:9092 \
        --messages ${NUM_RECORDS} \
        --group "redpanda-concurrent-group" \
        > "${results_dir}/concurrent-consumer-results.txt" &
    
    local consumer_pid=$!
    sleep 5
    
    # Start producer
    docker run --rm --network redpanda-network \
        confluentinc/cp-kafka:7.4.0 \
        kafka-producer-perf-test \
        --topic "${TOPIC_NAME}" \
        --num-records ${NUM_RECORDS} \
        --record-size ${MESSAGE_SIZE} \
        --throughput ${TARGET_THROUGHPUT} \
        --producer-props \
            bootstrap.servers=redpanda-1:9092,redpanda-2:9092,redpanda-3:9092 \
            acks=1 \
            batch.size=16384 \
            linger.ms=5 \
            compression.type=lz4 \
        > "${results_dir}/concurrent-producer-results.txt"
    
    # Wait for consumer to finish
    wait $consumer_pid 2>/dev/null || true
    
    log "Redpanda concurrent test completed. Results saved to: ${results_dir}/"
}

# Test Redpanda native tools
test_redpanda_native() {
    log "Running Redpanda native tools test..."
    
    local results_dir="results/redpanda-native-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Test rpk produce
    info "Testing rpk produce performance..."
    echo "Testing Redpanda native produce performance" | \
    docker exec redpanda-1 rpk topic produce "${TOPIC_NAME}" \
        --brokers localhost:9092 \
        --partition 0 \
        > "${results_dir}/rpk-produce-results.txt" 2>&1
    
    # Test rpk consume
    info "Testing rpk consume performance..."
    timeout 30s docker exec redpanda-1 rpk topic consume "${TOPIC_NAME}" \
        --brokers localhost:9092 \
        --group "rpk-test-group" \
        --offset start \
        --num 10 \
        > "${results_dir}/rpk-consume-results.txt" 2>&1 || true
    
    log "Redpanda native tools test completed. Results saved to: ${results_dir}/"
}

# Get Redpanda cluster information
get_redpanda_info() {
    log "Gathering Redpanda cluster information..."
    
    local results_dir="results/redpanda-info-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "${results_dir}"
    
    # Cluster health
    docker exec redpanda-1 rpk cluster health \
        > "${results_dir}/cluster-health.txt" 2>&1
    
    # Cluster info
    docker exec redpanda-1 rpk cluster info \
        > "${results_dir}/cluster-info.txt" 2>&1
    
    # Topic information
    docker exec redpanda-1 rpk topic list \
        > "${results_dir}/topics-list.txt" 2>&1
    
    # Redpanda configuration
    docker exec redpanda-1 rpk cluster config status \
        > "${results_dir}/config-status.txt" 2>&1
    
    # Redpanda metrics
    curl -s http://localhost:19644/metrics > "${results_dir}/redpanda-metrics.txt" 2>&1 || true
    
    log "Redpanda cluster information saved to: ${results_dir}/"
}

# Generate Redpanda performance report
generate_redpanda_report() {
    log "Generating Redpanda performance report..."
    
    local report_file="results/redpanda-performance-report-$(date +%Y%m%d-%H%M%S).md"
    
    cat > "${report_file}" <<EOF
# Redpanda Performance Test Report

**Test Date:** $(date)
**Test Duration:** ${TEST_DURATION}
**Message Size:** ${MESSAGE_SIZE} bytes
**Target Throughput:** ${TARGET_THROUGHPUT} messages/sec
**Topic:** ${TOPIC_NAME}
**Partitions:** ${PARTITIONS}
**Replication Factor:** ${REPLICATION_FACTOR}

## Test Configuration

- **Redpanda Version:** redpandadata/redpanda:v23.2.15
- **Cluster Size:** 3 nodes
- **No Zookeeper:** Raft consensus
- **Memory:** 4GB per node

## Producer Configuration
\`\`\`
bootstrap.servers=redpanda-1:9092,redpanda-2:9092,redpanda-3:9092
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
$(find results -name "*redpanda*" -path "*/producer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No producer results found")
\`\`\`

### Consumer Performance
\`\`\`
$(find results -name "*redpanda*" -path "*/consumer-results.txt" -exec tail -1 {} \; 2>/dev/null | head -1 || echo "No consumer results found")
\`\`\`

## Redpanda-Specific Features

- **No Zookeeper dependency** - Uses Raft consensus
- **C++ implementation** - Lower latency and higher throughput
- **Vectorized processing** - SIMD optimizations
- **Automatic tuning** - Self-optimizing configuration

## Monitoring Access

- **Grafana Dashboard:** http://localhost:3000
- **Prometheus Metrics:** http://localhost:9090
- **Redpanda Console:** http://localhost:8082
- **Redpanda Metrics:** http://localhost:19644/metrics

## Resource Utilization

Check Grafana dashboards for detailed resource utilization:
- CPU usage per node
- Memory consumption
- Disk I/O patterns
- Network throughput

## Next Steps

1. Compare with Kafka results using \`./scripts/test-kafka-only.sh\`
2. Analyze detailed metrics in Grafana
3. Test Redpanda-specific optimizations
4. Run extended tests with different configurations

---
*Generated by test-redpanda-only.sh*
EOF

    log "Redpanda performance report generated: ${report_file}"
}

# Cleanup function
cleanup() {
    log "Cleaning up Redpanda test resources..."
    
    # Delete test topic
    docker exec redpanda-1 rpk topic delete "${TOPIC_NAME}" 2>/dev/null || true
    
    log "Cleanup completed."
}

# Display access information
display_redpanda_info() {
    log "Redpanda performance test completed!"
    echo
    info "Access your Redpanda environment:"
    echo "- Redpanda Console: http://localhost:8082"
    echo "- Grafana Dashboard: http://localhost:3000 (admin/admin123)"
    echo "- Prometheus Metrics: http://localhost:9090"
    echo "- Redpanda Metrics: http://localhost:19644/metrics"
    echo "- Results Directory: results/"
    echo
    info "Redpanda cluster endpoints:"
    echo "- Node 1: localhost:19092"
    echo "- Node 2: localhost:19093"
    echo "- Node 3: localhost:19094"
    echo
    info "To test Kafka separately:"
    echo "- Run: ./scripts/test-kafka-only.sh"
    echo
    info "To stop Redpanda:"
    echo "- Run: docker-compose -f docker/redpanda/docker-compose.yml down"
}

# Main execution
main() {
    log "Starting Redpanda-only performance testing..."
    
    # Create results directory
    mkdir -p results
    
    # Setup trap for cleanup
    trap cleanup EXIT
    
    check_monitoring
    start_redpanda
    create_redpanda_topic
    get_redpanda_info
    
    # Run performance tests
    test_redpanda_producer
    sleep 10
    test_redpanda_consumer
    sleep 10
    test_redpanda_concurrent
    test_redpanda_native
    
    generate_redpanda_report
    display_redpanda_info
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