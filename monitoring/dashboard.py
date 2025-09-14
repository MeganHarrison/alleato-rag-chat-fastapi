#!/usr/bin/env python3
"""
Real-time monitoring dashboard for Alleato RAG Agent.

This script provides a live terminal dashboard showing:
- Request metrics and performance
- AI agent execution statistics
- Search operation metrics
- System health status
"""

import time
import json
from datetime import datetime
import argparse

try:
    import requests
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Monitoring dashboard dependencies not available: {e}")
    print("Install with: pip install requests rich")
    MONITORING_AVAILABLE = False


class RAGMonitoringDashboard:
    """Real-time monitoring dashboard for the RAG system."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url
        self.console = Console()
        self.metrics_history = []
        
    def fetch_metrics(self):
        """Fetch current metrics from the API."""
        try:
            # Get health status
            health_response = requests.get(f"{self.api_url}/health", timeout=5)
            health_data = health_response.json()
            
            # Get tracing status
            tracing_response = requests.get(f"{self.api_url}/tracing/status", timeout=5)
            tracing_data = tracing_response.json()
            
            # Get Prometheus metrics
            metrics_response = requests.get(f"{self.api_url}/metrics", timeout=5)
            metrics_text = metrics_response.text
            
            return {
                "timestamp": datetime.now(),
                "health": health_data,
                "tracing": tracing_data,
                "metrics_raw": metrics_text,
                "api_responsive": True
            }
        except Exception as e:
            return {
                "timestamp": datetime.now(),
                "error": str(e),
                "api_responsive": False
            }
    
    def parse_prometheus_metrics(self, metrics_text: str):
        """Parse Prometheus metrics text into structured data."""
        metrics = {}
        
        for line in metrics_text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            try:
                if '{' in line:
                    # Metric with labels
                    metric_name = line.split('{')[0]
                    value = float(line.split(' ')[-1])
                else:
                    # Simple metric
                    parts = line.split(' ')
                    metric_name = parts[0]
                    value = float(parts[1])
                
                if metric_name.startswith('alleato_'):
                    metrics[metric_name] = value
            except (ValueError, IndexError):
                continue
        
        return metrics
    
    def create_system_status_panel(self, data):
        """Create system status panel."""
        if not data.get("api_responsive", False):
            return Panel(
                Text("❌ API Unreachable", style="bold red"),
                title="System Status",
                border_style="red"
            )
        
        health = data.get("health", {})
        status = health.get("status", "unknown")
        checks = health.get("checks", {})
        
        status_text = Text()
        
        # Overall status
        if status == "healthy":
            status_text.append("✅ ", style="green")
            status_text.append("System Healthy", style="bold green")
        else:
            status_text.append("⚠️ ", style="yellow")
            status_text.append("System Degraded", style="bold yellow")
        
        status_text.append(f"\nLast Updated: {data['timestamp'].strftime('%H:%M:%S')}")
        
        # Individual checks
        status_text.append("\n\nComponent Status:")
        for component, status in checks.items():
            if status:
                status_text.append(f"\n✅ {component.replace('_', ' ').title()}")
            else:
                status_text.append(f"\n❌ {component.replace('_', ' ').title()}", style="red")
        
        return Panel(
            status_text,
            title="System Status",
            border_style="green" if status == "healthy" else "yellow"
        )
    
    def create_metrics_table(self, metrics):
        """Create metrics table."""
        table = Table(title="Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Description", style="white")
        
        metric_descriptions = {
            "alleato_requests_total": "Total API requests",
            "alleato_request_duration_seconds": "Average request duration",
            "alleato_agent_execution_seconds": "AI agent execution time",
            "alleato_search_operations_total": "Search operations count",
            "alleato_db_connections_active": "Active DB connections",
            "alleato_vector_similarity_scores": "Vector similarity scores"
        }
        
        for metric_name, value in metrics.items():
            description = metric_descriptions.get(metric_name, "Custom metric")
            if isinstance(value, float):
                if "duration" in metric_name or "seconds" in metric_name:
                    formatted_value = f"{value:.3f}s"
                elif "similarity" in metric_name:
                    formatted_value = f"{value:.2f}"
                else:
                    formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)
            
            table.add_row(
                metric_name.replace("alleato_", ""),
                formatted_value,
                description
            )
        
        return table
    
    def create_activity_log(self):
        """Create activity log panel."""
        log_text = Text()
        
        if len(self.metrics_history) > 0:
            recent_metrics = self.metrics_history[-5:]  # Last 5 entries
            
            for entry in recent_metrics:
                timestamp = entry["timestamp"].strftime("%H:%M:%S")
                if entry.get("api_responsive", False):
                    log_text.append(f"{timestamp} - ", style="dim")
                    log_text.append("API healthy", style="green")
                    
                    # Add any specific events
                    if "health" in entry:
                        status = entry["health"].get("status", "unknown")
                        if status != "healthy":
                            log_text.append(f" (Status: {status})", style="yellow")
                else:
                    log_text.append(f"{timestamp} - ", style="dim")
                    log_text.append("API unreachable", style="red")
                    if "error" in entry:
                        log_text.append(f" ({entry['error']})", style="dim")
                
                log_text.append("\n")
        else:
            log_text.append("No activity logged yet...", style="dim")
        
        return Panel(
            log_text,
            title="Activity Log",
            border_style="blue"
        )
    
    def create_dashboard_layout(self, data):
        """Create the complete dashboard layout."""
        layout = Layout()
        
        # Parse metrics if available
        metrics = {}
        if data.get("api_responsive") and "metrics_raw" in data:
            metrics = self.parse_prometheus_metrics(data["metrics_raw"])
        
        # Create panels
        status_panel = self.create_system_status_panel(data)
        
        if metrics:
            metrics_table = self.create_metrics_table(metrics)
        else:
            metrics_table = Panel(
                Text("No metrics available", style="dim"),
                title="Performance Metrics"
            )
        
        activity_log = self.create_activity_log()
        
        # Layout structure
        layout.split_column(
            Layout(status_panel, size=10),
            Layout(metrics_table, size=15),
            Layout(activity_log)
        )
        
        return layout
    
    def run_dashboard(self, refresh_interval: int = 5):
        """Run the live dashboard."""
        self.console.print("[bold green]🚀 Alleato RAG Agent - Monitoring Dashboard[/bold green]")
        self.console.print(f"[dim]Monitoring API at: {self.api_url}[/dim]")
        self.console.print(f"[dim]Refresh interval: {refresh_interval} seconds[/dim]")
        self.console.print(f"[dim]Press Ctrl+C to exit[/dim]\n")
        
        def update_dashboard():
            # Fetch current data
            data = self.fetch_metrics()
            self.metrics_history.append(data)
            
            # Keep only last 20 entries
            if len(self.metrics_history) > 20:
                self.metrics_history = self.metrics_history[-20:]
            
            return self.create_dashboard_layout(data)
        
        try:
            with Live(update_dashboard(), refresh_per_second=1/refresh_interval) as live:
                while True:
                    time.sleep(refresh_interval)
                    live.update(update_dashboard())
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")


def main():
    """Main function to run the monitoring dashboard."""
    if not MONITORING_AVAILABLE:
        print("❌ Cannot start monitoring dashboard - missing dependencies")
        print("Install with: pip install requests rich")
        return 1
    
    parser = argparse.ArgumentParser(description="Alleato RAG Agent Monitoring Dashboard")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API URL to monitor (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=5,
        help="Refresh interval in seconds (default: 5)"
    )
    
    args = parser.parse_args()
    
    dashboard = RAGMonitoringDashboard(args.api_url)
    dashboard.run_dashboard(args.refresh)
    return 0


if __name__ == "__main__":
    exit(main())