# Windows Docker Compatibility Fixes

This document explains the comprehensive fixes applied to resolve Docker container startup issues on Windows systems.

## Issues Identified

### 1. cAdvisor `/dev/kmsg` Device Error
**Error Message:**
```
ERROR: for cadvisor  Cannot start service cadvisor: error gathering device information while adding custom device "/dev/kmsg": no such file or directory
```

**Root Cause:**
- The `/dev/kmsg` device is a Linux-specific kernel message buffer device
- Windows Docker containers don't have access to this device
- cAdvisor was configured to mount this device for kernel message monitoring

### 2. Elasticsearch rlimit Permission Error
**Error Message:**
```
ERROR: for elasticsearch  Cannot start service elasticsearch: failed to create task for container: failed to create shim task: OCI runtime create failed: runc create failed: unable to start container process: error during container init: error setting rlimits for ready process: error setting rlimit type 8: operation not permitted: unknown
```

**Root Cause:**
- The `ulimits.memlock` setting requires privileged container access
- Windows Docker Desktop runs containers in a more restricted environment
- The `bootstrap.memory_lock=true` environment variable was also causing issues

### 3. ContainerConfig Errors
**Error Message:**
```
ERROR: for cadvisor  'ContainerConfig'
ERROR: for elasticsearch  'ContainerConfig'
```

**Root Cause:**
- Windows Docker has different container configuration requirements
- Some Linux-specific configurations cause validation errors
- Security and privilege settings need Windows-specific handling

## Solutions Provided

### Solution 1: Modified Standard Configuration
**Files Modified:** [`docker/monitoring/docker-compose.yml`](docker/monitoring/docker-compose.yml:1)

**cAdvisor Changes:**
- Removed the `devices` section for `/dev/kmsg`
- Added Windows-specific security options
- Added `privileged: false` and `security_opt` configurations

**Elasticsearch Changes:**
- Removed the `ulimits` section entirely
- Commented out `bootstrap.memory_lock=true`
- Added disk threshold configuration for better Windows compatibility

### Solution 2: Windows-Specific Configuration
**File Created:** [`docker/monitoring/docker-compose-windows.yml`](docker/monitoring/docker-compose-windows.yml:1)

**Key Features:**
- Replaces cAdvisor with `docker-exporter` for container monitoring
- Replaces Elasticsearch/Kibana with Grafana Loki for lightweight logging
- Maintains core monitoring functionality (Prometheus, Grafana, Alertmanager)
- Includes Jaeger for distributed tracing
- Optimized for Windows Docker Desktop environment

**Services Included:**
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert management and notifications
- **Docker Exporter**: Windows-compatible container metrics
- **Loki**: Lightweight log aggregation
- **Jaeger**: Distributed tracing
- **Redis**: Caching and session storage
- **PostgreSQL**: Performance data storage

## Automated Setup

The [`scripts/setup.sh`](scripts/setup.sh:1) script now automatically detects Windows and uses the appropriate configuration:

```bash
# Run the setup script - it will auto-detect Windows
./scripts/setup.sh
```

**Windows Detection Logic:**
- Checks for `$OSTYPE` containing "msys" or "cygwin"
- Checks for `$WINDIR` environment variable
- Automatically uses `docker-compose-windows.yml` when available

## Manual Setup Options

### Option 1: Use Modified Standard Configuration
```bash
cd docker/monitoring
docker-compose up -d
```

### Option 2: Use Windows-Specific Configuration (Recommended)
```bash
cd docker/monitoring
docker-compose -f docker-compose-windows.yml up -d
```

### Option 3: Individual Service Testing
```bash
# Start only core monitoring services
cd docker/monitoring
docker-compose -f docker-compose-windows.yml up -d prometheus grafana alertmanager

# Add container monitoring
docker-compose -f docker-compose-windows.yml up -d docker-exporter

# Add logging
docker-compose -f docker-compose-windows.yml up -d loki
```

## Verification Steps

### Standard Configuration Testing
```bash
cd docker/monitoring
docker-compose ps
curl -s http://localhost:9090/api/v1/status/config  # Prometheus
curl -s http://localhost:3000/api/health            # Grafana
```

### Windows-Specific Configuration Testing
```bash
cd docker/monitoring
docker-compose -f docker-compose-windows.yml ps
curl -s http://localhost:9090/api/v1/status/config  # Prometheus
curl -s http://localhost:3000/api/health            # Grafana
curl -s http://localhost:3100/ready                 # Loki
curl -s http://localhost:9417/metrics               # Docker Exporter
```

## Service Access Points

### Core Services (Both Configurations)
- **Grafana Dashboard**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Jaeger Tracing**: http://localhost:16686

### Standard Configuration
- **Elasticsearch**: http://localhost:9200
- **Kibana**: http://localhost:5601
- **cAdvisor**: http://localhost:8080

### Windows-Specific Configuration
- **Loki**: http://localhost:3100
- **Docker Exporter**: http://localhost:9417

## Troubleshooting

### If Containers Still Fail to Start

1. **Check Docker Desktop Settings**
   - Ensure WSL 2 backend is enabled
   - Verify resource allocation (memory, CPU)
   - Check file sharing permissions

2. **Use Windows-Specific Configuration**
   ```bash
   cd docker/monitoring
   docker-compose -f docker-compose-windows.yml down
   docker-compose -f docker-compose-windows.yml up -d
   ```

3. **Start Services Individually**
   ```bash
   # Start core services first
   docker-compose -f docker-compose-windows.yml up -d prometheus grafana
   
   # Add additional services one by one
   docker-compose -f docker-compose-windows.yml up -d alertmanager
   docker-compose -f docker-compose-windows.yml up -d docker-exporter
   ```

4. **Check Logs for Specific Errors**
   ```bash
   docker-compose -f docker-compose-windows.yml logs [service-name]
   ```

### Common Windows Docker Issues

1. **Volume Mount Permissions**
   - Ensure Docker Desktop has access to the project directory
   - Check Windows file sharing settings

2. **Port Conflicts**
   - Verify no other services are using the required ports
   - Check Windows Defender firewall settings

3. **Resource Constraints**
   - Increase Docker Desktop memory allocation
   - Reduce service resource limits if needed

## Performance Considerations

### Windows-Specific Configuration Benefits
- **Lighter Resource Usage**: Loki uses less memory than Elasticsearch
- **Better Compatibility**: Docker Exporter designed for Docker Desktop
- **Faster Startup**: Fewer complex services to initialize
- **Reduced Conflicts**: Eliminates Linux-specific dependencies

### Trade-offs
- **Logging**: Loki has different query syntax than Elasticsearch
- **Monitoring**: Docker Exporter provides different metrics than cAdvisor
- **Features**: Some advanced ELK stack features not available

## Integration with Kafka Performance Testing

Both configurations fully support the Kafka vs Redpanda performance comparison:

1. **Metrics Collection**: All Kafka and Redpanda metrics are collected
2. **Visualization**: Grafana dashboards work with both configurations
3. **Alerting**: Performance alerts function normally
4. **Tracing**: Jaeger provides distributed tracing for both platforms

## Next Steps

1. Choose the appropriate configuration for your Windows environment
2. Run the setup script or manually start the monitoring stack
3. Verify all services are running and accessible
4. Proceed with Kafka and Redpanda performance testing
5. Use Grafana dashboards to monitor and compare performance metrics

For additional help, see the main project documentation and performance testing guides.