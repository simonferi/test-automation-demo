#!/usr/bin/env python3
"""
Universal Smoke Test Pipeline (Python implementation)
Works on Windows, Linux, macOS, and CI/CD environments
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    GRAY = '\033[0;90m'
    NC = '\033[0m'  # No Color
    
    @staticmethod
    def is_supported():
        """Check if terminal supports colors"""
        return sys.stdout.isatty() and os.name != 'nt' or 'ANSICON' in os.environ


class Logger:
    """Simple colored logger"""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and Colors.is_supported()
    
    def _color(self, text: str, color: str) -> str:
        if self.use_colors:
            return f"{color}{text}{Colors.NC}"
        return text
    
    def info(self, message: str):
        print(self._color(message, Colors.CYAN))
    
    def success(self, message: str):
        print(self._color(message, Colors.GREEN))
    
    def warning(self, message: str):
        print(self._color(message, Colors.YELLOW))
    
    def error(self, message: str):
        print(self._color(message, Colors.RED), file=sys.stderr)
    
    def gray(self, message: str):
        print(self._color(message, Colors.GRAY))


logger = Logger()


def create_slug(value: str) -> str:
    """Create URL-safe slug from string"""
    slug = re.sub(r'[^0-9a-z_-]+', '-', value.lower()).strip('-')
    return slug if slug else 'value'


def get_spec_info(spec_path: Path) -> Tuple[str, str]:
    """Extract service name and version from OpenAPI spec"""
    if not spec_path.exists():
        logger.error(f"Specification file not found: {spec_path}")
        sys.exit(1)
    
    try:
        content = spec_path.read_text(encoding='utf-8')
        
        # Try JSON first
        if spec_path.suffix == '.json':
            data = json.loads(content)
            title = data.get('info', {}).get('title', 'UnknownService')
            version = data.get('info', {}).get('version', '1.0.0')
        else:
            # Simple YAML parsing
            title_match = re.search(r'title:\s*["\']?([^"\'\r\n]+)["\']?', content)
            version_match = re.search(r'version:\s*["\']?([^"\'\r\n]+)["\']?', content)
            
            title = title_match.group(1).strip() if title_match else 'UnknownService'
            version = version_match.group(1).strip() if version_match else '1.0.0'
        
        return title, version
    except Exception as e:
        logger.warning(f"Could not auto-detect service info: {e}")
        return 'UnknownService', '1.0.0'


def run_uv_python(args: List[str], cwd: Path, env: dict) -> None:
    """Run Python command via uv"""
    cmd = ['uv', 'run', 'python'] + args
    result = subprocess.run(cmd, cwd=cwd, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}")


def main():
    parser = argparse.ArgumentParser(
        description='Universal Smoke Test Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run-smoke-pipeline.py --spec specs/payments.yaml
  python scripts/run-smoke-pipeline.py --spec specs/commerce.yaml --port 9102 --output-format rich
  python scripts/run-smoke-pipeline.py --spec specs/flights.yaml --tag flights --tag integration
        """
    )
    
    # Required arguments
    parser.add_argument('--spec', required=True, help='Path to OpenAPI specification file')
    
    # Optional arguments
    parser.add_argument('--service', default='', help='Service name (auto-detected if not provided)')
    parser.add_argument('--version', default='', help='Service version (auto-detected if not provided)')
    parser.add_argument('--port', default='9101', help='REST API port for mock server (default: 9101)')
    parser.add_argument('--prefix', default='smoke', help='Scenario prefix (default: smoke)')
    parser.add_argument('--tag', action='append', dest='tags', default=[], help='Scenario tag (can be specified multiple times)')
    parser.add_argument('--base-url', default='', help='Base URL for smoke tests')
    parser.add_argument('--output-format', choices=['auto', 'rich', 'plain', 'json'], default='auto',
                       help='Output format (default: auto)')
    parser.add_argument('--keep-mock', action='store_true', help='Keep mock server running after tests')
    parser.add_argument('--skip-parsing', action='store_true', help='Skip contract parsing')
    parser.add_argument('--skip-mock-config', action='store_true', help='Skip mock config generation')
    parser.add_argument('--skip-test-generation', action='store_true', help='Skip test scenario generation')
    
    args = parser.parse_args()
    
    # Setup paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    spec_path = Path(args.spec)
    
    if not spec_path.is_absolute():
        spec_path = repo_root / spec_path
    
    os.chdir(repo_root)
    
    # Setup environment
    env = os.environ.copy()
    env['CONSOLE_OUTPUT_FORMAT'] = args.output_format
    env['PYTHONPATH'] = os.pathsep.join([
        str(repo_root / 'apps' / 'contract-parser'),
        str(repo_root / 'apps' / 'test-scenario-builder'),
        str(repo_root / 'apps' / 'mock-config-builder'),
        str(repo_root / 'apps' / 'mock-server'),
        str(repo_root / 'apps' / 'test-executor'),
    ])
    
    # Auto-detect service info
    detected_service, detected_version = get_spec_info(spec_path)
    service = args.service or detected_service
    version = args.version or detected_version
    
    if not args.service:
        logger.warning(f"Auto-detected service name: {service}")
    if not args.version:
        logger.warning(f"Auto-detected version: {version}")
    
    # Auto-configure base URL
    base_url = args.base_url or f"http://127.0.0.1:{args.port}"
    if not args.base_url:
        logger.warning(f"Using base URL: {base_url}")
    
    # Auto-configure tags
    tags = args.tags if args.tags else [create_slug(service).split('-')[0]]
    if not args.tags:
        logger.warning(f"Using scenario tags: {', '.join(tags)}")
    
    # Generate file paths
    service_slug = create_slug(service)
    version_slug = create_slug(version)
    version_file = version.replace('/', '-')
    ir_file = repo_root / 'workspace' / 'catalog' / service_slug / f'{version_file}.json'
    mock_config_path = repo_root / 'artifacts' / 'mocks' / service_slug / version_slug / 'mock-config.yaml'
    bundle_dir = repo_root / 'artifacts' / 'tests' / service_slug / version_file
    
    # Print header
    print()
    logger.info("=== Smoke Test Pipeline ===")
    print(f"Service:     {service}")
    print(f"Version:     {version}")
    print(f"Spec:        {spec_path}")
    print(f"Port:        {args.port}")
    print(f"Output:      {args.output_format}")
    logger.info("===========================")
    print()
    
    mock_process = None
    
    try:
        # Step 1: Contract Parser
        if not args.skip_parsing:
            logger.info("[1/5] Running contract-parser")
            run_uv_python([
                'apps/contract-parser/contract_parser/main.py',
                '--spec', str(spec_path),
                '--output-dir', 'workspace/catalog',
                '--service-name', service
            ], repo_root, env)
        else:
            logger.gray("[1/5] Skipping contract-parser (--skip-parsing)")
            if not ir_file.exists():
                logger.error(f"IR file not found: {ir_file}. Cannot skip parsing.")
                sys.exit(1)
        
        # Step 2: Mock Config Builder
        if not args.skip_mock_config:
            logger.info("[2/5] Running mock-config-builder")
            run_uv_python([
                'apps/mock-config-builder/mock_config_builder/main.py',
                '--ir', str(ir_file),
                '--output-dir', 'artifacts/mocks',
                '--format', 'yaml',
                '--host', '127.0.0.1',
                '--port', f'rest={args.port}'
            ], repo_root, env)
        else:
            logger.gray("[2/5] Skipping mock-config-builder (--skip-mock-config)")
            if not mock_config_path.exists():
                logger.error(f"Mock config not found: {mock_config_path}. Cannot skip generation.")
                sys.exit(1)
        
        # Step 3: Test Scenario Builder
        if not args.skip_test_generation:
            logger.info("[3/5] Running test-scenario-builder")
            generator_args = [
                'apps/test-scenario-builder/test_scenario_builder/main.py',
                '--ir', str(ir_file),
                '--output-dir', 'artifacts/tests',
                '--scenario-prefix', args.prefix
            ]
            for tag in tags:
                if tag:
                    generator_args.extend(['--tag', tag])
            run_uv_python(generator_args, repo_root, env)
        else:
            logger.gray("[3/5] Skipping test-scenario-builder (--skip-test-generation)")
            if not bundle_dir.exists():
                logger.error(f"Test bundle not found: {bundle_dir}. Cannot skip generation.")
                sys.exit(1)
        
        # Step 4: Start Mock Server
        logger.info("[4/5] Starting mock-server in background")
        mock_log = repo_root / 'mock-server.log'
        with open(mock_log, 'w') as log_file:
            mock_process = subprocess.Popen(
                ['uv', 'run', 'python', 'apps/mock-server/mock_server/main.py',
                 '--config', str(mock_config_path)],
                cwd=repo_root,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
        
        # Wait for mock server to start
        time.sleep(3)
        
        # Check if process is still running
        if mock_process.poll() is not None:
            logger.error("Mock server failed to start. Log output:")
            print(mock_log.read_text())
            sys.exit(1)
        
        # Step 5: Run Test Executor
        logger.info("[5/5] Running test-executor")
        original_base_url = env.get('SMOKE_RUNTIME_BASE_URL')
        env['SMOKE_RUNTIME_BASE_URL'] = base_url
        try:
            run_uv_python([
                'apps/test-executor/test_executor/main.py',
                '--bundle', str(bundle_dir),
                '--output-dir', 'runs'
            ], repo_root, env)
        finally:
            if original_base_url:
                env['SMOKE_RUNTIME_BASE_URL'] = original_base_url
            elif 'SMOKE_RUNTIME_BASE_URL' in env:
                del env['SMOKE_RUNTIME_BASE_URL']
        
        # Show results
        runs_dir = repo_root / 'runs'
        if runs_dir.exists():
            latest_run = max(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, default=None)
            if latest_run:
                logger.success(f"\nSmoke results saved to runs/{latest_run.name}")
        
        logger.success("\n=== Pipeline Completed Successfully ===")
        
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n=== Pipeline Failed ===")
        logger.error(str(e))
        sys.exit(1)
    finally:
        # Cleanup mock server
        if mock_process and not args.keep_mock:
            logger.info("\nStopping mock server...")
            mock_process.terminate()
            try:
                mock_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mock_process.kill()
        elif mock_process and args.keep_mock:
            logger.warning(f"\nMock runtime is still running (PID: {mock_process.pid})")
            logger.warning(f"Logs: {repo_root / 'mock-server.log'}")
            logger.warning(f"Use 'kill {mock_process.pid}' to stop it")


if __name__ == '__main__':
    main()
