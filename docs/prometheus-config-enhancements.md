# Prometheus Configuration Enhancements for Long-term Node Exporter Testing

## Current Issues and Recommended Fixes

Based on the Docker Compose errors and the need for long-term CPU/IO degradation testing, here are the specific configuration changes needed:

## 1. Enhanced Prometheus Configuration

### Update docker/monitoring/docker-compose.yml

**Current Prometheus Configuration (lines 8-16):**
```yaml
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--web.console.libraries=/etc/prometheus/console_libraries'
  - '--web.console.templates=/etc/prometheus/consoles'
  - '--storage.tsdb.retention.time=30d'
  - '--storage.tsdb.retention.size=10GB'
  - '--web.enable-lifecycle'
  - '--web.enable-admin-api'
```

**Enhanced Configuration for Long-term Testing:**
```yaml
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--web.console.libraries=/etc/prometheus/console_libraries'
  - '--web.console.templates=/etc/prometheus/consoles'
  - '--storage.tsdb.retention.time=90d'        # Increased from 30d
  - '--storage.tsdb.retention.size=50GB'       # Increased from 10GB
  - '--web.enable-lifecycle'
  - '--web.enable-admin-api'
  - '--storage.tsdb.wal-compression'           # Enable WAL compression
  - '--query.max-samples=50000000'             # Increase query sample limit
```

## 2. Enhanced Node Exporter Scraping Configuration

### Update docker/monitoring/configs/prometheus.yml

**Current Node Exporter Job (lines 24-28):**
```yaml
- job_name: 'node-exporter'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 5s
  metrics_path: /metrics
```

**Enhanced Configuration for Degradation Detection:**
```yaml
- job_name: 'node-exporter'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 1s                    # Increased frequency from 5s
  scrape_timeout: 5s
  metrics_path: /metrics
  metric_relabel_configs:
    # Keep only essential metrics for long-term storage efficiency
    - source_labels: [__name__]
      regex: 'node_(cpu_seconds_total|memory_.*|disk_.*|network_.*|load.*|filesystem_.*)'
      action: keep

- job_name: 'node-exporter-detailed'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 5s                    # Standard interval for all metrics
  scrape_timeout: 10s
  metrics_path: /metrics
  # No metric filtering - collect everything for comprehensive analysis
```

## 3. Fix Docker Compose Issues

### cAdvisor Fix (lines 122-123)
**Remove problematic device mapping:**
```yaml
# Comment out or remove:
# devices:
#   - /dev/kmsg

# Add instead:
security_opt:
  - no-new-privileges:true
```

### Elasticsearch Fix (lines 164-168)
**Disable memory locking:**
```yaml
environment:
  - discovery.type=single-node
  - xpack.security.enabled=false
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
  - bootstrap.memory_lock=false          # Changed from true

# Remove ulimits section entirely:
# ulimits:
#   memlock:
#     soft: -1
#     hard: -1
```

## 4. Minimal Monitoring Stack for Node Exporter Testing

Create `docker/monitoring/docker-compose-minimal.yml` for immediate testing:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.47.0
    hostname: prometheus
    container_name: prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=90d'
      - '--storage.tsdb.retention.size=50GB'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
      - '--storage.tsdb.wal-compression'
      - '--query.max-samples=50000000'
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus-minimal.yml:/etc/prometheus/prometheus.yml
      - ./configs/alert-rules.yml:/etc/prometheus/alert-rules.yml
      - prometheus-data:/prometheus
    networks:
      - monitoring-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G                     # Increased for long-term data
          cpus: '4'                      # Increased for query performance
        reservations:
          memory: 4G
          cpus: '2'

  grafana:
    image: grafana/grafana:10.1.0
    hostname: grafana
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-piechart-panel,grafana-worldmap-panel,grafana-clock-panel
      - GF_FEATURE_TOGGLES_ENABLE=publicDashboards
    volumes:
      - grafana-data:/var/lib/grafana
      - ./configs/grafana/provisioning:/etc/grafana/provisioning
      - ./configs/grafana/dashboards:/var/lib/grafana/dashboards
    networks:
      - monitoring-network
    depends_on:
      - prometheus
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:v1.6.1
    hostname: node-exporter
    container_name: node-exporter
    command:
      - '--path.rootfs=/host'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
      - '--collector.systemd'
      - '--collector.processes'
      - '--collector.interrupts'          # Additional collector for detailed CPU analysis
      - '--collector.softirqs'            # Additional collector for system analysis
      - '--collector.vmstat'              # Additional collector for memory analysis
    ports:
      - "9100:9100"
    volumes:
      - /:/host:ro,rslave
    networks:
      - monitoring-network
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 512M                   # Increased for additional collectors
          cpus: '0.5'                    # Increased for additional collectors

  alertmanager:
    image: prom/alertmanager:v0.26.0
    hostname: alertmanager
    container_name: alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
      - '--cluster.advertise-address=0.0.0.0:9093'
    ports:
      - "9093:9093"
    volumes:
      - ./configs/alertmanager.yml:/etc/alertmanager/config.yml
      - alertmanager-data:/alertmanager
    networks:
      - monitoring-network
    restart: unless-stopped

volumes:
  prometheus-data:
    driver: local
  grafana-data:
    driver: local
  alertmanager-data:
    driver: local

networks:
  monitoring-network:
    driver: bridge
    external: false
```

## 5. Minimal Prometheus Configuration

Create `docker/monitoring/configs/prometheus-minimal.yml`:

```yaml
global:
  scrape_interval: 1s                    # High frequency for degradation detection
  evaluation_interval: 15s
  external_labels:
    cluster: 'kafka-redpanda-comparison'
    environment: 'performance-testing'

rule_files:
  - "alert-rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
    scrape_interval: 15s

  # Node Exporter - High frequency for CPU/IO degradation detection
  - job_name: 'node-exporter-degradation'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 1s
    scrape_timeout: 5s
    metrics_path: /metrics
    metric_relabel_configs:
      # Keep only essential metrics for degradation analysis
      - source_labels: [__name__]
        regex: 'node_(cpu_seconds_total|memory_MemTotal_bytes|memory_MemFree_bytes|memory_MemAvailable_bytes|memory_Cached_bytes|memory_Buffers_bytes|memory_SwapTotal_bytes|memory_SwapFree_bytes|load1|load5|load15|disk_reads_completed_total|disk_writes_completed_total|disk_read_bytes_total|disk_written_bytes_total|disk_io_time_seconds_total|disk_read_time_seconds_total|disk_write_time_seconds_total|network_receive_bytes_total|network_transmit_bytes_total|network_receive_packets_total|network_transmit_packets_total|network_receive_errs_total|network_transmit_errs_total|filesystem_size_bytes|filesystem_free_bytes|filesystem_avail_bytes)'
        action: keep

  # Node Exporter - Standard frequency for comprehensive monitoring
  - job_name: 'node-exporter-comprehensive'
    static_configs:
      - targets: ['node-exporter:9100']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    # No filtering - collect all metrics
```

## 6. Implementation Steps

### Step 1: Quick Fix for Immediate Testing
```bash
# Stop current monitoring stack
cd docker/monitoring
docker-compose down

# Apply fixes to docker-compose.yml
# 1. Comment out cAdvisor devices section
# 2. Set elasticsearch bootstrap.memory_lock=false
# 3. Remove elasticsearch ulimits section

# Start minimal stack
docker-compose up -d prometheus grafana node-exporter alertmanager
```

### Step 2: Verify Node Exporter Functionality
```bash
# Test Node Exporter metrics
curl http://localhost:9100/metrics | grep node_cpu

# Test Prometheus targets
curl http://localhost:9090/api/v1/targets

# Access Grafana
# URL: http://localhost:3000
# Credentials: admin/admin123
```

### Step 3: Implement Enhanced Configuration
```bash
# Copy enhanced configurations
cp docker/monitoring/configs/prometheus.yml docker/monitoring/configs/prometheus-backup.yml
# Apply enhanced prometheus configuration

# Restart with enhanced settings
docker-compose restart prometheus
```

## 7. Validation Commands

```bash
# Check Prometheus configuration
curl http://localhost:9090/api/v1/status/config

# Verify high-frequency scraping
curl "http://localhost:9090/api/v1/query?query=up{job='node-exporter-degradation'}"

# Check storage metrics
curl "http://localhost:9090/api/v1/query?query=prometheus_tsdb_symbol_table_size_bytes"

# Verify Node Exporter metrics availability
curl "http://localhost:9090/api/v1/query?query=node_cpu_seconds_total"
```

This configuration provides the foundation for long-term Node Exporter monitoring with enhanced data retention and high-frequency sampling needed for CPU/IO degradation detection over 6-24 hour periods.