#!/usr/bin/env python3
"""
Main CLI entry point for Align-Press v2.

This script provides a unified interface to all CLI tools with subcommands.
"""

import argparse
import sys
from typing import List

from rich.console import Console
from rich.panel import Panel

from . import test_detector, calibrate, validate_profile, benchmark

console = Console()


def create_main_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="align-press",
        description="Align-Press v2 - Logo Detection and Alignment System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Commands:
  test        Test detector with images or camera
  calibrate   Interactive camera calibration
  validate    Validate profile configurations
  benchmark   Performance analysis of detector

Examples:
  align-press test --config config.yaml --camera 0 --show
  align-press calibrate --camera 0 --pattern-size 9 6 --square-size-mm 25
  align-press validate profiles/ --recursive --fix-common
  align-press benchmark --config config.yaml --dataset images/ --samples 50

For detailed help on each command:
  align-press <command> --help
        """
    )

    # Global options
    parser.add_argument(
        '--version',
        action='version',
        version='Align-Press v2.0.0'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )

    # Create subparsers
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='<command>'
    )

    # Test detector subcommand
    test_parser = subparsers.add_parser(
        'test',
        help='Test detector with images or camera',
        description='Test the logo detector with static images or live camera feed'
    )
    _add_test_arguments(test_parser)

    # Calibrate subcommand
    calibrate_parser = subparsers.add_parser(
        'calibrate',
        help='Interactive camera calibration',
        description='Calibrate camera using chessboard patterns'
    )
    _add_calibrate_arguments(calibrate_parser)

    # Validate subcommand
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate profile configurations',
        description='Validate profile files against schemas'
    )
    _add_validate_arguments(validate_parser)

    # Benchmark subcommand
    benchmark_parser = subparsers.add_parser(
        'benchmark',
        help='Performance analysis of detector',
        description='Run performance benchmarks on detector'
    )
    _add_benchmark_arguments(benchmark_parser)

    return parser


def _add_test_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for test detector command."""
    # Configuration
    parser.add_argument(
        '--config', '-c',
        type=str,
        required=True,
        help='Path to detector configuration file'
    )

    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--image', '-i',
        type=str,
        help='Path to input image file'
    )
    input_group.add_argument(
        '--camera',
        type=int,
        help='Camera device ID'
    )

    # Optional inputs
    parser.add_argument(
        '--homography',
        type=str,
        help='Path to homography calibration file'
    )

    # Output options
    parser.add_argument(
        '--save-debug',
        type=str,
        help='Path to save debug image'
    )
    parser.add_argument(
        '--save-json',
        type=str,
        help='Path to save results as JSON'
    )

    # Camera options
    parser.add_argument(
        '--show',
        action='store_true',
        help='Show live video window'
    )
    parser.add_argument(
        '--fps',
        type=int,
        help='Target FPS for camera'
    )


def _add_calibrate_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for calibrate command."""
    parser.add_argument(
        '--camera', '-c',
        type=int,
        required=True,
        help='Camera device ID'
    )

    parser.add_argument(
        '--pattern-size',
        type=int,
        nargs=2,
        required=True,
        metavar=('WIDTH', 'HEIGHT'),
        help='Chessboard pattern size in corners'
    )

    parser.add_argument(
        '--square-size-mm',
        type=float,
        required=True,
        help='Size of chessboard squares in mm'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='Output path for calibration file'
    )

    parser.add_argument(
        '--no-preview',
        action='store_true',
        help='Run without preview window'
    )

    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing file'
    )


def _add_validate_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for validate command."""
    parser.add_argument(
        'path',
        type=str,
        help='Path to profile file or directory'
    )

    parser.add_argument(
        '--schema',
        type=str,
        help='Path to JSON schema file'
    )

    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Validate recursively'
    )

    parser.add_argument(
        '--fix-common',
        action='store_true',
        help='Fix common issues automatically'
    )


def _add_benchmark_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for benchmark command."""
    parser.add_argument(
        '--config', '-c',
        type=str,
        required=True,
        help='Path to detector configuration file'
    )

    parser.add_argument(
        '--dataset', '-d',
        type=str,
        required=True,
        help='Path to dataset directory or image'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Path to save results'
    )

    parser.add_argument(
        '--samples', '-s',
        type=int,
        help='Limit number of samples'
    )


def print_welcome() -> None:
    """Print welcome message."""
    welcome_text = """
🎯 [bold blue]Align-Press v2[/bold blue] - Logo Detection and Alignment System

Pipeline robusto OpenCV + ORB para Raspberry Pi
    """

    console.print(Panel(welcome_text.strip(), style="blue"))


def show_command_help() -> None:
    """Show available commands when no command is specified."""
    commands_help = """
[bold]Available Commands:[/bold]

[cyan]test[/cyan]        Test detector with images or live camera
[cyan]calibrate[/cyan]   Interactive camera calibration using chessboard
[cyan]validate[/cyan]    Validate profile configurations against schemas
[cyan]benchmark[/cyan]   Run performance analysis on detector

[bold]Quick Examples:[/bold]

Test detector with camera:
  [dim]align-press test --config config.yaml --camera 0 --show[/dim]

Calibrate camera:
  [dim]align-press calibrate --camera 0 --pattern-size 9 6 --square-size-mm 25 --output cal.json[/dim]

Validate profiles:
  [dim]align-press validate profiles/ --recursive[/dim]

Run benchmark:
  [dim]align-press benchmark --config config.yaml --dataset images/[/dim]

[bold]For detailed help:[/bold]
  [dim]align-press <command> --help[/dim]
    """

    console.print(commands_help)


def main(args: List[str] = None) -> int:
    """
    Main entry point for the CLI.

    Args:
        args: Command line arguments (for testing)

    Returns:
        Exit code
    """
    parser = create_main_parser()

    # Parse arguments
    if args is None:
        args = sys.argv[1:]

    parsed_args = parser.parse_args(args)

    # Handle global options
    if parsed_args.quiet:
        console.quiet = True
    elif parsed_args.verbose:
        console.print("[dim]Verbose mode enabled[/dim]")

    # Show welcome message
    if not parsed_args.quiet:
        print_welcome()

    # Check if command was provided
    if not parsed_args.command:
        if not parsed_args.quiet:
            show_command_help()
        return 0

    # Execute the appropriate command
    try:
        if parsed_args.command == 'test':
            return _run_test_detector(parsed_args)
        elif parsed_args.command == 'calibrate':
            return _run_calibrate(parsed_args)
        elif parsed_args.command == 'validate':
            return _run_validate(parsed_args)
        elif parsed_args.command == 'benchmark':
            return _run_benchmark(parsed_args)
        else:
            console.print(f"[red]Unknown command: {parsed_args.command}[/red]")
            return 1

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user[/yellow]")
        return 0
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        if parsed_args.verbose:
            console.print_exception()
        return 1


def _run_test_detector(args) -> int:
    """Run test detector command."""
    # Convert args to format expected by test_detector.main()
    test_args = ['--config', args.config]

    if args.image:
        test_args.extend(['--image', args.image])
    else:
        test_args.extend(['--camera', str(args.camera)])

    if args.homography:
        test_args.extend(['--homography', args.homography])

    if args.save_debug:
        test_args.extend(['--save-debug', args.save_debug])

    if args.save_json:
        test_args.extend(['--save-json', args.save_json])

    if args.show:
        test_args.append('--show')

    if args.fps:
        test_args.extend(['--fps', str(args.fps)])

    if hasattr(args, 'verbose') and args.verbose:
        test_args.append('--verbose')

    if hasattr(args, 'quiet') and args.quiet:
        test_args.append('--quiet')

    # Temporarily replace sys.argv for the subcommand
    old_argv = sys.argv
    try:
        sys.argv = ['test_detector'] + test_args
        return test_detector.main()
    finally:
        sys.argv = old_argv


def _run_calibrate(args) -> int:
    """Run calibrate command."""
    calibrate_args = [
        '--camera', str(args.camera),
        '--pattern-size', str(args.pattern_size[0]), str(args.pattern_size[1]),
        '--square-size-mm', str(args.square_size_mm),
        '--output', args.output
    ]

    if args.no_preview:
        calibrate_args.append('--no-preview')

    if args.force:
        calibrate_args.append('--force')

    old_argv = sys.argv
    try:
        sys.argv = ['calibrate'] + calibrate_args
        return calibrate.main()
    finally:
        sys.argv = old_argv


def _run_validate(args) -> int:
    """Run validate command."""
    validate_args = [args.path]

    if args.schema:
        validate_args.extend(['--schema', args.schema])

    if args.recursive:
        validate_args.append('--recursive')

    if args.fix_common:
        validate_args.append('--fix-common')

    if hasattr(args, 'quiet') and args.quiet:
        validate_args.append('--quiet')

    old_argv = sys.argv
    try:
        sys.argv = ['validate_profile'] + validate_args
        return validate_profile.main()
    finally:
        sys.argv = old_argv


def _run_benchmark(args) -> int:
    """Run benchmark command."""
    benchmark_args = [
        '--config', args.config,
        '--dataset', args.dataset
    ]

    if args.output:
        benchmark_args.extend(['--output', args.output])

    if args.samples:
        benchmark_args.extend(['--samples', str(args.samples)])

    if hasattr(args, 'quiet') and args.quiet:
        benchmark_args.append('--quiet')

    old_argv = sys.argv
    try:
        sys.argv = ['benchmark'] + benchmark_args
        return benchmark.main()
    finally:
        sys.argv = old_argv


if __name__ == '__main__':
    sys.exit(main())