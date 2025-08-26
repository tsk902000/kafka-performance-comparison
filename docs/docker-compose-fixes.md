# Docker Compose Configuration Fixes

## Issues Identified

The setup script is failing due to two main issues in the monitoring stack:

### 1. cAdvisor `/dev/kmsg` Device Error
**Error:** `Cannot start service cadvisor: error gathering device information while adding custom device "/dev/kmsg": no such file or directory`

**Root Cause:** The `/dev/kmsg` device may not be available on all systems, particularly in containerized environments or certain Linux distributions.

### 2. Elasticsearch Memory Lock Error
**Error:** `Cannot start service elasticsearch: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: error setting rlimits for ready process: error setting rlimit type 8: operation not permitted`

**Root Cause:** Elasticsearch is trying to set memory lock limits that require privileged access or specific system configuration.

## Recommended Fixes

### Fix 1: Update cAdvisor Configuration

**Current Configuration (docker/monitoring/docker-compose.yml lines 122-123):**
```yaml
devices:
  - /dev/kmsg
```

**Recommended Fix:**
```yaml
devices:
  - /dev/kmsg:/dev/kmsg:r
privileged: false
# Alternative: Remove devices section entirely for basic monitoring
```

**Or for broader compatibility, make the device optional:**
```yaml
# Remove the devices section entirely and add:
security_opt:
  - no-new-privileges:true
```

### Fix 2: Update Elasticsearch Configuration

**Current Configuration (docker/monitoring/docker-compose.yml lines 164-168):**
```yaml
environment:
  - discovery.type=single-node
  - xpack.security.enabled=false
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
  - bootstrap.memory_lock=true
ulimits:
  memlock:
    soft: -1
    hard: -1
```

**Recommended Fix:**
```yaml
environment:
  - discovery.type=single-node
  - xpack.security.enabled=false
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
  - bootstrap.memory_lock=false  # Changed from true
# Remove ulimits section entirely
```

### Fix 3: Alternative Minimal Monitoring Stack

For immediate testing, consider a minimal monitoring configuration that focuses on Node Exporter:

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
      - '--storage.tsdb.retention.time=90d'  # Enhanced for long-term testing
      - '--storage.tsdb.retention.size=50GB'  # Enhanced for long-term testing
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./configs/alert-rules.yml:/etc/prometheus/alert-rules.yml
      - prometheus-data:/prometheus
    networks:
      - monitoring-network
    restart: unless-stopped

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
    volumes:
      - grafana-data:/var/lib/grafana
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
          memory: 256M
          cpus: '0.25'

volumes:
  prometheus-data:
    driver: local
  grafana-data:
    driver: local

networks:
  monitoring-network:
    driver: bridge
    external: false
```

## Implementation Steps

### Option 1: Quick Fix (Recommended)
1. **Update cAdvisor configuration:**
   ```yaml
   # Comment out or remove the devices section in cAdvisor service
   # devices:
   #   - /dev/kmsg
   ```

2. **Update Elasticsearch configuration:**
   ```yaml
   environment:
     - bootstrap.memory_lock=false  # Change from true
   # Remove ulimits section
   ```

### Option 2: Minimal Stack for Node Exporter Testing
1. Create a separate `docker-compose-minimal.yml` file with just Prometheus, Grafana, and Node Exporter
2. Use this for initial Node Exporter performance testing
3. Add other services incrementally after resolving issues

### Option 3: System-Level Fixes
1. **For cAdvisor:** Ensure `/dev/kmsg` exists or run with privileged mode
2. **For Elasticsearch:** Configure system memory limits or run with `--privileged` flag

## Updated Prometheus Configuration for Long-term Testing

```yaml
# Enhanced retention for Node Exporter long-term testing
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--storage.tsdb.retention.time=90d'  # Increased from 30d
  - '--storage.tsdb.retention.size=50GB'  # Increased from 10GB
  - '--web.enable-lifecycle'
  - '--web.enable-admin-api'

# Enhanced Node Exporter scraping
- job_name: 'node-exporter-detailed'
  static_configs:
    - targets: ['node-exporter:9100']
  scrape_interval: 1s  # High frequency for degradation detection
  scrape_timeout: 5s
```

## Testing the Fixes

After implementing the fixes:

1. **Test minimal stack:**
   ```bash
   cd docker/monitoring
   docker-compose down
   docker-compose up -d prometheus grafana node-exporter
   ```

2. **Verify Node Exporter metrics:**
   ```bash
   curl http://localhost:9100/metrics | grep node_cpu
   ```

3. **Check Prometheus targets:**
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

4. **Access Grafana:**
   - URL: http://localhost:3000
   - Credentials: admin/admin123

## Next Steps for Node Exporter Focus

Once the monitoring stack is running:

1. Implement the baseline measurement script
2. Configure enhanced Prometheus retention
3. Create Node Exporter-specific Grafana dashboards
4. Set up long-term performance test scenarios
5. Monitor CPU/IO degradation patterns over 6-24 hour periods