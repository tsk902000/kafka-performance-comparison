



import json
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import seaborn as sns
from tabulate import tabulate


class ReportGenerator:
    """Generate performance comparison reports and visualizations."""
    
    def __init__(self, results_dir: str = "results"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def load_comparison_results(self, comparison_file: str) -> Dict:
        """Load comparison results from JSON file."""
        with open(comparison_file, 'r') as f:
            return json.load(f)
    
    def generate_comparison_report(self, comparison_results: Dict, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive comparison report."""
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.results_dir / f"comparison_report_{timestamp}.html"
        
        html_content = self._generate_html_report(comparison_results)
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"Comparison report generated: {output_file}")
        return str(output_file)
    
    def _generate_html_report(self, results: Dict) -> str:
        """Generate HTML report content."""
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Kafka vs Redpanda Performance Comparison</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 30px 0; }}
        .metric-table {{ border-collapse: collapse; width: 100%; }}
        .metric-table th, .metric-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .metric-table th {{ background-color: #f2f2f2; }}
        .winner {{ background-color: #d4edda; font-weight: bold; }}
        .loser {{ background-color: #f8d7da; }}
        .chart {{ text-align: center; margin: 20px 0; }}
        .summary {{ background-color: #e7f3ff; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Kafka vs Redpanda Performance Comparison</h1>
        <p><strong>Test:</strong> {results.get('test_name', 'Unknown')}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
"""
        
        # Executive Summary
        html += self._generate_executive_summary(results)
        
        # Producer Performance
        html += self._generate_producer_section(results)
        
        # Consumer Performance
        html += self._generate_consumer_section(results)
        
        # Resource Usage
        html += self._generate_resource_section(results)
        
        # Detailed Results
        html += self._generate_detailed_section(results)
        
        html += """
</body>
</html>
"""
        return html
    
    def _generate_executive_summary(self, results: Dict) -> str:
        """Generate executive summary section."""
        comparison = results.get('comparison', {})
        
        # Count wins for each platform
        kafka_wins = 0
        redpanda_wins = 0
        
        for category in comparison.values():
            if isinstance(category, dict):
                for metric in category.values():
                    if isinstance(metric, dict) and 'winner' in metric:
                        if metric['winner'] == 'kafka':
                            kafka_wins += 1
                        elif metric['winner'] == 'redpanda':
                            redpanda_wins += 1
        
        overall_winner = 'Redpanda' if redpanda_wins > kafka_wins else 'Kafka'
        
        html = f"""
    <div class="section summary">
        <h2>Executive Summary</h2>
        <p><strong>Overall Winner:</strong> {overall_winner}</p>
        <p><strong>Kafka Wins:</strong> {kafka_wins} metrics</p>
        <p><strong>Redpanda Wins:</strong> {redpanda_wins} metrics</p>
    </div>
"""
        return html
    
    def _generate_producer_section(self, results: Dict) -> str:
        """Generate producer performance section."""
        comparison = results.get('comparison', {})
        producer_comp = comparison.get('producer', {})
        
        html = """
    <div class="section">
        <h2>Producer Performance</h2>
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Kafka</th>
                <th>Redpanda</th>
                <th>Winner</th>
            </tr>
"""
        
        # Throughput
        throughput = producer_comp.get('throughput', {})
        kafka_tps = throughput.get('kafka_msg_per_sec', 0)
        redpanda_tps = throughput.get('redpanda_msg_per_sec', 0)
        tps_winner = throughput.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>Throughput (msg/sec)</td>
                <td class="{'winner' if tps_winner == 'kafka' else 'loser'}">{kafka_tps:.2f}</td>
                <td class="{'winner' if tps_winner == 'redpanda' else 'loser'}">{redpanda_tps:.2f}</td>
                <td>{tps_winner.title()}</td>
            </tr>
"""
        
        # Bandwidth
        bandwidth = producer_comp.get('bandwidth', {})
        kafka_bw = bandwidth.get('kafka_mbps', 0)
        redpanda_bw = bandwidth.get('redpanda_mbps', 0)
        bw_winner = bandwidth.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>Bandwidth (MB/sec)</td>
                <td class="{'winner' if bw_winner == 'kafka' else 'loser'}">{kafka_bw:.2f}</td>
                <td class="{'winner' if bw_winner == 'redpanda' else 'loser'}">{redpanda_bw:.2f}</td>
                <td>{bw_winner.title()}</td>
            </tr>
        </table>
    </div>
"""
        return html
    
    def _generate_consumer_section(self, results: Dict) -> str:
        """Generate consumer performance section."""
        comparison = results.get('comparison', {})
        consumer_comp = comparison.get('consumer', {})
        
        html = """
    <div class="section">
        <h2>Consumer Performance</h2>
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Kafka</th>
                <th>Redpanda</th>
                <th>Winner</th>
            </tr>
"""
        
        # Throughput
        throughput = consumer_comp.get('throughput', {})
        kafka_tps = throughput.get('kafka_msg_per_sec', 0)
        redpanda_tps = throughput.get('redpanda_msg_per_sec', 0)
        tps_winner = throughput.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>Throughput (msg/sec)</td>
                <td class="{'winner' if tps_winner == 'kafka' else 'loser'}">{kafka_tps:.2f}</td>
                <td class="{'winner' if tps_winner == 'redpanda' else 'loser'}">{redpanda_tps:.2f}</td>
                <td>{tps_winner.title()}</td>
            </tr>
"""
        
        # Latency
        latency = consumer_comp.get('latency', {})
        kafka_lat = latency.get('kafka_avg_ms', 0)
        redpanda_lat = latency.get('redpanda_avg_ms', 0)
        lat_winner = latency.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>Average Latency (ms)</td>
                <td class="{'winner' if lat_winner == 'kafka' else 'loser'}">{kafka_lat:.2f}</td>
                <td class="{'winner' if lat_winner == 'redpanda' else 'loser'}">{redpanda_lat:.2f}</td>
                <td>{lat_winner.title()}</td>
            </tr>
        </table>
    </div>
"""
        return html
    
    def _generate_resource_section(self, results: Dict) -> str:
        """Generate resource usage section."""
        comparison = results.get('comparison', {})
        resource_comp = comparison.get('resources', {})
        
        html = """
    <div class="section">
        <h2>Resource Usage</h2>
        <table class="metric-table">
            <tr>
                <th>Metric</th>
                <th>Kafka</th>
                <th>Redpanda</th>
                <th>Winner (Lower is Better)</th>
            </tr>
"""
        
        # CPU Usage
        cpu = resource_comp.get('cpu_usage', {})
        kafka_cpu = cpu.get('kafka_avg_percent', 0)
        redpanda_cpu = cpu.get('redpanda_avg_percent', 0)
        cpu_winner = cpu.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>CPU Usage (%)</td>
                <td class="{'winner' if cpu_winner == 'kafka' else 'loser'}">{kafka_cpu:.2f}</td>
                <td class="{'winner' if cpu_winner == 'redpanda' else 'loser'}">{redpanda_cpu:.2f}</td>
                <td>{cpu_winner.title()}</td>
            </tr>
"""
        
        # Memory Usage
        memory = resource_comp.get('memory_usage', {})
        kafka_mem = memory.get('kafka_avg_percent', 0)
        redpanda_mem = memory.get('redpanda_avg_percent', 0)
        mem_winner = memory.get('winner', 'tie')
        
        html += f"""
            <tr>
                <td>Memory Usage (%)</td>
                <td class="{'winner' if mem_winner == 'kafka' else 'loser'}">{kafka_mem:.2f}</td>
                <td class="{'winner' if mem_winner == 'redpanda' else 'loser'}">{redpanda_mem:.2f}</td>
                <td>{mem_winner.title()}</td>
            </tr>
        </table>
    </div>
"""
        return html
    
    def _generate_detailed_section(self, results: Dict) -> str:
        """Generate detailed results section."""
        html = """
    <div class="section">
        <h2>Detailed Results</h2>
        <h3>Test Configuration</h3>
"""
        
        # Get configuration from either platform
        config = {}
        if 'kafka_results' in results and 'config' in results['kafka_results']:
            config = results['kafka_results']['config']
        elif 'redpanda_results' in results and 'config' in results['redpanda_results']:
            config = results['redpanda_results']['config']
        
        if config:
            html += "<ul>"
            for key, value in config.items():
                html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
            html += "</ul>"
        
        # Error information
        kafka_errors = results.get('kafka_results', {}).get('errors', [])
        redpanda_errors = results.get('redpanda_results', {}).get('errors', [])
        
        if kafka_errors or redpanda_errors:
            html += "<h3>Errors and Warnings</h3>"
            
            if kafka_errors:
                html += "<h4>Kafka Errors:</h4><ul>"
                for error in kafka_errors:
                    html += f"<li>{error}</li>"
                html += "</ul>"
            
            if redpanda_errors:
                html += "<h4>Redpanda Errors:</h4><ul>"
                for error in redpanda_errors:
                    html += f"<li>{error}</li>"
                html += "</ul>"
        
        html += "</div>"
        return html
    
    def generate_charts(self, comparison_results: Dict, output_dir: Optional[str] = None) -> List[str]:
        """Generate performance comparison charts."""
        
        if not output_dir:
            output_dir = self.results_dir
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(exist_ok=True)
        
        chart_files = []
        comparison = comparison_results.get('comparison', {})
        
        # Producer throughput chart
        if 'producer' in comparison:
            chart_file = self._create_throughput_chart(comparison['producer'], output_dir, 'producer')
            if chart_file:
                chart_files.append(chart_file)
        
        # Consumer performance chart
        if 'consumer' in comparison:
            chart_file = self._create_consumer_chart(comparison['consumer'], output_dir)
            if chart_file:
                chart_files.append(chart_file)
        
        # Resource usage chart
        if 'resources' in comparison:
            chart_file = self._create_resource_chart(comparison['resources'], output_dir)
            if chart_file:
                chart_files.append(chart_file)
        
        return chart_files
    
    def _create_throughput_chart(self, producer_data: Dict, output_dir: Path, prefix: str) -> Optional[str]:
        """Create throughput comparison chart."""
        try:
            throughput = producer_data.get('throughput', {})
            kafka_tps = throughput.get('kafka_msg_per_sec', 0)
            redpanda_tps = throughput.get('redpanda_msg_per_sec', 0)
            
            if kafka_tps == 0 and redpanda_tps == 0:
                return None
            
            platforms = ['Kafka', 'Redpanda']
            values = [kafka_tps, redpanda_tps]
            
            plt.figure(figsize=(10, 6))
            bars = plt.bar(platforms, values, color=['#ff7f0e', '#2ca02c'])
            plt.title(f'{prefix.title()} Throughput Comparison')
            plt.ylabel('Messages per Second')
            plt.grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(values)*0.01,
                        f'{value:.1f}', ha='center', va='bottom')
            
            chart_file = output_dir / f'{prefix}_throughput_comparison.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_file)
        
        except Exception as e:
            print(f"Error creating throughput chart: {e}")
            return None
    
    def _create_consumer_chart(self, consumer_data: Dict, output_dir: Path) -> Optional[str]:
        """Create consumer performance chart."""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # Throughput
            throughput = consumer_data.get('throughput', {})
            kafka_tps = throughput.get('kafka_msg_per_sec', 0)
            redpanda_tps = throughput.get('redpanda_msg_per_sec', 0)
            
            platforms = ['Kafka', 'Redpanda']
            tps_values = [kafka_tps, redpanda_tps]
            
            bars1 = ax1.bar(platforms, tps_values, color=['#ff7f0e', '#2ca02c'])
            ax1.set_title('Consumer Throughput')
            ax1.set_ylabel('Messages per Second')
            ax1.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars1, tps_values):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(tps_values)*0.01,
                        f'{value:.1f}', ha='center', va='bottom')
            
            # Latency
            latency = consumer_data.get('latency', {})
            kafka_lat = latency.get('kafka_avg_ms', 0)
            redpanda_lat = latency.get('redpanda_avg_ms', 0)
            
            lat_values = [kafka_lat, redpanda_lat]
            
            bars2 = ax2.bar(platforms, lat_values, color=['#ff7f0e', '#2ca02c'])
            ax2.set_title('Consumer Latency')
            ax2.set_ylabel('Average Latency (ms)')
            ax2.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars2, lat_values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(lat_values)*0.01,
                        f'{value:.2f}', ha='center', va='bottom')
            
            plt.tight_layout()
            
            chart_file = output_dir / 'consumer_performance_comparison.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_file)
        
        except Exception as e:
            print(f"Error creating consumer chart: {e}")
            return None
    
    def _create_resource_chart(self, resource_data: Dict, output_dir: Path) -> Optional[str]:
        """Create resource usage chart."""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            platforms = ['Kafka', 'Redpanda']
            
            # CPU Usage
            cpu = resource_data.get('cpu_usage', {})
            kafka_cpu = cpu.get('kafka_avg_percent', 0)
            redpanda_cpu = cpu.get('redpanda_avg_percent', 0)
            cpu_values = [kafka_cpu, redpanda_cpu]
            
            bars1 = ax1.bar(platforms, cpu_values, color=['#ff7f0e', '#2ca02c'])
            ax1.set_title('CPU Usage')
            ax1.set_ylabel('CPU Usage (%)')
            ax1.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars1, cpu_values):
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(cpu_values)*0.01,
                        f'{value:.1f}%', ha='center', va='bottom')
            
            # Memory Usage
            memory = resource_data.get('memory_usage', {})
            kafka_mem = memory.get('kafka_avg_percent', 0)
            redpanda_mem = memory.get('redpanda_avg_percent', 0)
            mem_values = [kafka_mem, redpanda_mem]
            
            bars2 = ax2.bar(platforms, mem_values, color=['#ff7f0e', '#2ca02c'])
            ax2.set_title('Memory Usage')
            ax2.set_ylabel('Memory Usage (%)')
            ax2.grid(axis='y', alpha=0.3)
            
            for bar, value in zip(bars2, mem_values):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(mem_values)*0.01,
                        f'{value:.1f}%', ha='center', va='bottom')
            
            plt.tight_layout()
            
            chart_file = output_dir / 'resource_usage_comparison.png'
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            return str(chart_file)
        
        except Exception as e:
            print(f"Error creating resource chart: {e}")
            return None
    
    def print_summary_table(self, comparison_results: Dict):
        """Print a summary table to console."""
        comparison = comparison_results.get('comparison', {})
        
        # Prepare data for table
        table_data = []
        
        # Producer metrics
        producer = comparison.get('producer', {})
        if 'throughput' in producer:
            t = producer['throughput']
            table_data.append([
                'Producer Throughput (msg/s)',
                f"{t.get('kafka_msg_per_sec', 0):.2f}",
                f"{t.get('redpanda_msg_per_sec', 0):.2f}",
                t.get('winner', 'tie').title()
            ])
        
        if 'bandwidth' in producer:
            b = producer['bandwidth']
            table_data.append([
                'Producer Bandwidth (MB/s)',
                f"{b.get('kafka_mbps', 0):.2f}",
                f"{b.get('redpanda_mbps', 0):.2f}",
                b.get('winner', 'tie').title()
            ])
        
        # Consumer metrics
        consumer = comparison.get('consumer', {})
        if 'throughput' in consumer:
            t = consumer['throughput']
            table_data.append([
                'Consumer Throughput (msg/s)',
                f"{t.get('kafka_msg_per_sec', 0):.2f}",
                f"{t.get('redpanda_msg_per_sec', 0):.2f}",
                t.get('winner', 'tie').title()
            ])
        
        if 'latency' in consumer:
            l = consumer['latency']
            table_data.append([
                'Consumer Latency (ms)',
                f"{l.get('kafka_avg_ms', 0):.2f}",
                f"{l.get('redpanda_avg_ms', 0):.2f}",
                l.get('winner', 'tie').title()
            ])
        
        # Resource metrics
        resources = comparison.get('resources', {})
        if 'cpu_usage' in resources:
            c = resources['cpu_usage']
            table_data.append([
                'CPU Usage (%)',
                f"{c.get('kafka_avg_percent', 0):.2f}",
                f"{c.get('redpanda_avg_percent', 0):.2f}",
                c.get('winner', 'tie').title()
            ])
        
        if 'memory_usage' in resources:
            m = resources['memory_usage']
            table_data.append([
                'Memory Usage (%)',
                f"{m.get('kafka_avg_percent', 0):.2f}",
                f"{m.get('redpanda_avg_percent', 0):.2f}",
                m.get('winner', 'tie').title()
            ])
        
        # Print table
        headers = ['Metric', 'Kafka', 'Redpanda', 'Winner']
        print("\n" + "="*80)
        print(f"PERFORMANCE COMPARISON SUMMARY - {comparison_results.get('test_name', 'Unknown Test')}")
        print("="*80)
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print("="*80)




