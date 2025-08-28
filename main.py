

#!/usr/bin/env python3

import click
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from test_orchestrator import TestOrchestrator
from report_generator import ReportGenerator


@click.group()
def cli():
    """Kafka vs Redpanda Performance Comparison Tool"""
    pass


@cli.command()
@click.option('--platform', type=click.Choice(['kafka', 'kafka-kraft', 'redpanda']), required=True,
              help='Platform to test (kafka, kafka-kraft, or redpanda)')
@click.option('--test', type=click.Choice(['light_load', 'medium_load', 'heavy_load']), 
              default='medium_load', help='Test configuration to run')
@click.option('--duration', type=int, help='Test duration in seconds (overrides test config)')
@click.option('--messages-per-second', type=int, help='Messages per second (overrides test config)')
@click.option('--message-size', type=int, help='Message size in bytes (overrides test config)')
@click.option('--threads', type=int, help='Number of producer threads (overrides test config)')
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
def single(platform, test, duration, messages_per_second, message_size, threads, producer_mode):
    """Run a single platform test."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    # Build custom config from CLI options
    custom_config = {}
    if duration:
        custom_config['duration_seconds'] = duration
    if messages_per_second:
        custom_config['messages_per_second'] = messages_per_second
    if message_size:
        custom_config['message_size_bytes'] = message_size
    if threads:
        custom_config['num_producer_threads'] = threads
    
    try:
        # Start platform
        if not orchestrator.start_platform(platform):
            click.echo(f"Failed to start {platform}", err=True)
            sys.exit(1)
        
        # Run test
        results = orchestrator.run_single_test(platform, test, custom_config)
        
        # Print summary
        click.echo(f"\nTest completed successfully!")
        click.echo(f"Platform: {platform}")
        click.echo(f"Test: {test}")
        
        if 'producer_stats' in results:
            stats = results['producer_stats']
            click.echo(f"Messages sent: {stats.get('messages_sent', 0)}")
            click.echo(f"Average throughput: {stats.get('average_throughput', 0):.2f} msg/s")
            click.echo(f"Average bandwidth: {stats.get('average_bandwidth_mbps', 0):.2f} MB/s")
        
    except Exception as e:
        click.echo(f"Test failed: {e}", err=True)
        sys.exit(1)
    
    finally:
        # Stop platform
        orchestrator.stop_platform(platform)


@cli.command()
@click.option('--test', type=click.Choice(['light_load', 'medium_load', 'heavy_load']), 
              default='medium_load', help='Test configuration to run')
@click.option('--duration', type=int, help='Test duration in seconds (overrides test config)')
@click.option('--messages-per-second', type=int, help='Messages per second (overrides test config)')
@click.option('--message-size', type=int, help='Message size in bytes (overrides test config)')
@click.option('--threads', type=int, help='Number of producer threads (overrides test config)')
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
@click.option('--generate-report', is_flag=True, help='Generate HTML report after comparison')
@click.option('--generate-charts', is_flag=True, help='Generate performance charts')
def compare(test, duration, messages_per_second, message_size, threads, producer_mode, generate_report, generate_charts):
    """Run comparison test between Kafka and Redpanda."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    # Build custom config from CLI options
    custom_config = {}
    if duration:
        custom_config['duration_seconds'] = duration
    if messages_per_second:
        custom_config['messages_per_second'] = messages_per_second
    if message_size:
        custom_config['message_size_bytes'] = message_size
    if threads:
        custom_config['num_producer_threads'] = threads
    
    try:
        # Run comparison test
        results = orchestrator.run_comparison_test(test, custom_config, producer_mode)
        
        # Generate report
        report_gen = ReportGenerator()
        report_gen.print_summary_table(results)
        
        if generate_report:
            report_file = report_gen.generate_comparison_report(results)
            click.echo(f"\nHTML report generated: {report_file}")
        
        if generate_charts:
            chart_files = report_gen.generate_charts(results)
            if chart_files:
                click.echo(f"\nCharts generated:")
                for chart_file in chart_files:
                    click.echo(f"  - {chart_file}")
        
    except Exception as e:
        click.echo(f"Comparison test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--test', type=click.Choice(['light_load', 'medium_load', 'heavy_load']), 
              default='medium_load', help='Test configuration to run')
@click.option('--duration', type=int, help='Test duration in seconds (overrides test config)')
@click.option('--messages-per-second', type=int, help='Messages per second (overrides test config)')
@click.option('--message-size', type=int, help='Message size in bytes (overrides test config)')
@click.option('--threads', type=int, help='Number of producer threads (overrides test config)')
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
@click.option('--generate-report', is_flag=True, help='Generate HTML report after comparison')
@click.option('--generate-charts', is_flag=True, help='Generate performance charts')
def three_way_compare(test, duration, messages_per_second, message_size, threads, producer_mode, generate_report, generate_charts):
    """Run three-way comparison test between Kafka (Zookeeper), Kafka KRaft, and Redpanda."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    # Build custom config from CLI options
    custom_config = {}
    if duration:
        custom_config['duration_seconds'] = duration
    if messages_per_second:
        custom_config['messages_per_second'] = messages_per_second
    if message_size:
        custom_config['message_size_bytes'] = message_size
    if threads:
        custom_config['num_producer_threads'] = threads
    
    try:
        # Run three-way comparison test
        results = orchestrator.run_three_way_comparison_test(test, custom_config, producer_mode)
        
        # Generate report
        report_gen = ReportGenerator()
        
        # Print summary for each platform
        click.echo(f"\n{'='*60}")
        click.echo(f"THREE-WAY COMPARISON RESULTS: {test}")
        click.echo(f"{'='*60}")
        
        # Print individual platform results
        for platform in ['kafka', 'kafka_kraft', 'redpanda']:
            platform_results = results.get(f'{platform}_results', {})
            if 'producer_stats' in platform_results:
                stats = platform_results['producer_stats']
                click.echo(f"\n{platform.upper().replace('_', ' ')}:")
                click.echo(f"  Messages sent: {stats.get('messages_sent', 0)}")
                click.echo(f"  Average throughput: {stats.get('average_throughput', 0):.2f} msg/s")
                click.echo(f"  Average bandwidth: {stats.get('average_bandwidth_mbps', 0):.2f} MB/s")
        
        # Print comparison winners
        comparison = results.get('comparison', {})
        if 'producer' in comparison:
            producer_comp = comparison['producer']
            if 'throughput' in producer_comp:
                click.echo(f"\nThroughput Winner: {producer_comp['throughput']['winner'].upper().replace('_', ' ')}")
                kraft_improvement = producer_comp['throughput'].get('kraft_vs_zookeeper_improvement', 0)
                if kraft_improvement != 0:
                    click.echo(f"KRaft vs Zookeeper improvement: {kraft_improvement:.1f}%")
        
        if generate_report:
            # For now, use the existing report generator with kafka vs redpanda
            # TODO: Extend report generator to support three-way comparison
            click.echo(f"\nThree-way HTML report generation not yet implemented")
        
        if generate_charts:
            # TODO: Extend chart generation for three-way comparison
            click.echo(f"\nThree-way chart generation not yet implemented")
        
    except Exception as e:
        click.echo(f"Three-way comparison test failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
@click.option('--generate-report', is_flag=True, help='Generate HTML report after all tests')
@click.option('--generate-charts', is_flag=True, help='Generate performance charts')
def all(producer_mode, generate_report, generate_charts):
    """Run all predefined tests for comprehensive comparison."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    report_gen = ReportGenerator()
    
    try:
        results_list = orchestrator.run_all_tests(producer_mode)
        
        click.echo(f"\nCompleted {len(results_list)} test comparisons")
        
        # Print summary for each test
        for results in results_list:
            if 'error' not in results:
                click.echo(f"\n{'-'*50}")
                click.echo(f"Test: {results.get('test_name', 'Unknown')}")
                report_gen.print_summary_table(results)
                
                if generate_report:
                    report_file = report_gen.generate_comparison_report(results)
                    click.echo(f"Report: {report_file}")
                
                if generate_charts:
                    chart_files = report_gen.generate_charts(results)
                    if chart_files:
                        click.echo(f"Charts: {', '.join(chart_files)}")
        
    except Exception as e:
        click.echo(f"Test suite failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('platform', type=click.Choice(['kafka', 'kafka-kraft', 'redpanda']))
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
def start(platform, producer_mode):
    """Start Kafka, Kafka KRaft, or Redpanda platform."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    try:
        if orchestrator.start_platform(platform):
            click.echo(f"{platform} started successfully")
        else:
            click.echo(f"Failed to start {platform}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting {platform}: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('platform', type=click.Choice(['kafka', 'kafka-kraft', 'redpanda']))
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
def stop(platform, producer_mode):
    """Stop Kafka, Kafka KRaft, or Redpanda platform."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    try:
        if orchestrator.stop_platform(platform):
            click.echo(f"{platform} stopped successfully")
        else:
            click.echo(f"Failed to stop {platform}", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error stopping {platform}: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('comparison_file', type=click.Path(exists=True))
@click.option('--output', help='Output file for the report')
@click.option('--charts', is_flag=True, help='Generate charts')
def report(comparison_file, output, charts):
    """Generate report from existing comparison results."""
    
    report_gen = ReportGenerator()
    
    try:
        # Load results
        results = report_gen.load_comparison_results(comparison_file)
        
        # Print summary
        report_gen.print_summary_table(results)
        
        # Generate HTML report
        if output:
            report_file = report_gen.generate_comparison_report(results, output)
        else:
            report_file = report_gen.generate_comparison_report(results)
        
        click.echo(f"\nHTML report generated: {report_file}")
        
        # Generate charts
        if charts:
            chart_files = report_gen.generate_charts(results)
            if chart_files:
                click.echo(f"\nCharts generated:")
                for chart_file in chart_files:
                    click.echo(f"  - {chart_file}")
        
    except Exception as e:
        click.echo(f"Report generation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--producer-mode', type=click.Choice(['v1', 'v2']), default='v1',
              help='Producer mode: v1 (synchronous/original) or v2 (asynchronous/high-throughput)')
def list_tests(producer_mode):
    """List available test configurations."""
    
    orchestrator = TestOrchestrator(producer_mode=producer_mode)
    
    click.echo("Available test configurations:")
    click.echo("-" * 40)
    
    for test_name, config in orchestrator.test_configs.items():
        click.echo(f"\n{test_name}:")
        for key, value in config.items():
            click.echo(f"  {key}: {value}")


if __name__ == '__main__':
    cli()


