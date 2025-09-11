# 🔍 Alleato RAG Agent - Comprehensive Tracing Setup

This guide shows you how to set up complete observability for the Alleato RAG Agent with distributed tracing, metrics, and monitoring.

## 📊 What's Included

### ✅ Distributed Tracing (OpenTelemetry + Jaeger)
- Request/response tracing across all endpoints
- AI agent execution spans
- Database query tracing
- Search operation tracing
- Error tracking and performance monitoring

### ✅ Metrics Collection (Prometheus)
- HTTP request metrics (count, duration, status codes)
- AI agent execution metrics
- Search operation statistics
- Database connection monitoring
- Vector similarity score distributions

### ✅ Real-time Monitoring
- Live terminal dashboard
- Health checks and status monitoring
- Performance metrics visualization
- Activity logging

## 🚀 Quick Start

### 1. Install Tracing Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the RAG Agent with Tracing
```bash
./start_production.sh
```

### 3. View Available Endpoints
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Tracing Status**: http://localhost:8000/tracing/status

### 4. Launch Monitoring Dashboard
```bash
# In a separate terminal
python monitoring/dashboard.py
```

## 🐳 Full Monitoring Stack (Optional)

### Start External Services
```bash
# Start Jaeger, Prometheus, and Grafana
docker-compose -f docker-compose.monitoring.yml up -d
```

### Access Monitoring UIs
- **Jaeger UI**: http://localhost:16686 (Distributed traces)
- **Prometheus**: http://localhost:9091 (Metrics)
- **Grafana**: http://localhost:3001 (Dashboards - admin/admin)

## 📈 Key Metrics Tracked

### HTTP Request Metrics
```
alleato_requests_total - Total API requests by method/endpoint/status
alleato_request_duration_seconds - Request duration distribution
```

### AI Agent Metrics
```
alleato_agent_execution_seconds - AI agent execution time
alleato_search_operations_total - Search operations count by type
alleato_vector_similarity_scores - Vector similarity score distribution
```

### System Metrics
```
alleato_db_connections_active - Active database connections
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Jaeger configuration
export JAEGER_ENDPOINT="http://localhost:14268/api/traces"

# Metrics configuration
export PROMETHEUS_PORT=9090

# Logging level
export LOG_LEVEL=INFO
```

### Tracing in Code

#### Trace Custom Operations
```python
from shared.monitoring.tracing import get_tracer

tracer = get_tracer()

# Manual tracing
with tracer.trace_operation("custom_operation", param1="value1"):
    # Your code here
    pass

# Decorator tracing
@tracer.trace_agent_execution("my_agent")
async def my_agent_function():
    # Agent code
    pass
```

## 📱 Monitoring Commands

### Check System Health
```bash
curl http://localhost:8000/health | jq .
```

### View Metrics
```bash
curl http://localhost:8000/metrics
```

### Real-time Dashboard
```bash
python monitoring/dashboard.py --refresh 3
```

## 🔍 What You Can Monitor

### 1. **Request Performance**
- Response times by endpoint
- Error rates and status codes
- Request volume patterns
- Slow query identification

### 2. **AI Agent Execution**
- Agent execution times
- Success/failure rates
- Tool calling patterns
- Search operation efficiency

### 3. **Search Operations**
- Semantic vs hybrid search usage
- Vector similarity score distributions
- Search result quality metrics
- Database query performance

### 4. **System Health**
- API responsiveness
- Database connectivity
- LLM service status
- Resource utilization

## 🚨 Alerting & Monitoring

### Key Alerts to Set Up
1. **High Response Time**: `alleato_request_duration_seconds > 5`
2. **High Error Rate**: `rate(alleato_requests_total{status=~"5.."}[5m]) > 0.1`
3. **Agent Failures**: `rate(alleato_agent_execution_seconds{success="false"}[5m]) > 0.05`
4. **Database Issues**: `alleato_db_connections_active == 0`

### Sample Prometheus Alerts
```yaml
groups:
  - name: alleato_alerts
    rules:
      - alert: HighResponseTime
        expr: alleato_request_duration_seconds > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
      
      - alert: AgentExecutionFailures
        expr: rate(alleato_agent_execution_seconds{success="false"}[5m]) > 0.05
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "AI agent execution failing"
```

## 📊 Sample Grafana Dashboards

### RAG Agent Overview Dashboard
- Request rate and latency charts
- Error rate monitoring
- Agent execution metrics
- Search operation statistics

### Performance Dashboard
- 95th percentile response times
- Request volume heatmaps
- Database connection pools
- Vector similarity distributions

## 🔧 Troubleshooting

### Common Issues

**1. Jaeger Not Receiving Traces**
```bash
# Check if Jaeger is running
curl http://localhost:16686

# Verify endpoint configuration
echo $JAEGER_ENDPOINT
```

**2. Metrics Not Appearing**
```bash
# Check metrics endpoint
curl http://localhost:8000/metrics

# Verify Prometheus scraping
curl http://localhost:9091/targets
```

**3. Dashboard Connection Issues**
```bash
# Test API connectivity
python monitoring/dashboard.py --api-url http://localhost:8000
```

## 🎯 Production Recommendations

### 1. **Resource Allocation**
- Reserve 10-15% additional CPU for tracing overhead
- Monitor memory usage for trace buffering
- Set appropriate trace sampling rates for high-volume environments

### 2. **Data Retention**
- Jaeger: 7-30 days for traces
- Prometheus: 15-90 days for metrics
- Configure appropriate storage backend for production

### 3. **Security**
- Secure Jaeger and Prometheus endpoints
- Use authentication for Grafana dashboards
- Sanitize sensitive data in traces

### 4. **Scaling**
- Use Jaeger Collector for high-volume tracing
- Configure Prometheus federation for multi-instance setups
- Implement metric aggregation for distributed deployments

## 📚 Additional Resources

- **OpenTelemetry Documentation**: https://opentelemetry.io/docs/
- **Jaeger Documentation**: https://www.jaegertracing.io/docs/
- **Prometheus Best Practices**: https://prometheus.io/docs/practices/
- **Grafana Dashboard Examples**: https://grafana.com/grafana/dashboards/

---

🎉 **Your RAG Agent is now fully observable!** Monitor performance, track issues, and optimize your AI-powered business intelligence system with comprehensive tracing and metrics.