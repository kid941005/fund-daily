#!/usr/bin/env python3
"""
Standalone Scheduler Service

APScheduler-based job scheduler running as an independent process.
Can be managed by systemd, supervisord, or run directly.

Usage:
    # Direct run
    python scripts/scheduler_service.py

    # With systemd (create a service file):
    systemctl enable fund-daily-scheduler

    # With supervisord (add to supervisord.conf):
    [program:fund-daily-scheduler]
    command = python scripts/scheduler_service.py
    directory = /home/kid/fund-daily
    user = kid
    autostart = true
    autorestart = true
    stderr_logfile = /var/log/fund-daily-scheduler.err.log
    stdout_logfile = /var/log/fund-daily-scheduler.out.log

Environment Variables:
    SCHEDULER_STANDALONE=true     # Always set, indicates standalone mode
    REDIS_HOST                     # Redis host (default: localhost)
    REDIS_PORT                     # Redis port (default: 6379)
    REDIS_DB                       # Redis DB for scheduler (default: 1)
    REDIS_PASSWORD                 # Redis password (optional)
    SCHEDULER_LOG_LEVEL            # Log level (default: INFO)
    SCHEDULER_CLUSTER_ENABLED      # Enable cluster mode (default: true)
    SCHEDULER_INSTANCE_ID           # Override instance ID
"""

import argparse
import logging
import os
import signal
import sys
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Mark as standalone mode
os.environ["SCHEDULER_STANDALONE"] = "true"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scheduler_service")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Fund Daily Scheduler Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("SCHEDULER_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--redis-host",
        default=os.getenv("REDIS_HOST", "localhost"),
        help="Redis host",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=int(os.getenv("REDIS_PORT", "6379")),
        help="Redis port",
    )
    parser.add_argument(
        "--redis-db",
        type=int,
        default=int(os.getenv("REDIS_DB", "1")),
        help="Redis database for scheduler",
    )
    parser.add_argument(
        "--redis-password",
        default=os.getenv("REDIS_PASSWORD"),
        help="Redis password",
    )
    parser.add_argument(
        "--no-cluster",
        action="store_true",
        help="Disable cluster mode (distributed locks)",
    )
    parser.add_argument(
        "--instance-id",
        default=os.getenv("SCHEDULER_INSTANCE_ID"),
        help="Instance ID for cluster mode",
    )
    return parser.parse_args()


class SchedulerService:
    """Standalone scheduler service"""

    def __init__(self, args):
        self.args = args
        self._manager = None
        self._running = False

    def _setup_logging(self):
        """Configure logging from args"""
        import logging

        level = getattr(logging, self.args.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(level)

        # Set APScheduler log level
        logging.getLogger("apscheduler").setLevel(level)

    def _build_config(self):
        """Build scheduler config from args"""
        from src.scheduler.config import SchedulerConfig

        return SchedulerConfig(
            redis_host=self.args.redis_host,
            redis_port=self.args.redis_port,
            redis_db=self.args.redis_db,
            redis_password=self.args.redis_password,
            cluster_enabled=not self.args.no_cluster,
            instance_id=self.args.instance_id,
            log_level=self.args.log_level,
        )

    def start(self):
        """Start the scheduler service"""
        self._setup_logging()

        # Initialize config
        config = self._build_config()
        logger.info(f"Starting scheduler service (instance: {config.get_instance_id()})")
        logger.info(f"Redis: {config.redis_host}:{config.redis_port}/{config.redis_db}")
        logger.info(f"Cluster mode: {config.cluster_enabled}")

        # Import after env vars are set
        from src.scheduler.manager import SchedulerManager

        # Create scheduler manager
        self._manager = SchedulerManager(config=config)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Start scheduler
        self._manager.start()
        self._running = True

        logger.info("=" * 60)
        logger.info("Scheduler service started successfully")
        logger.info(f"Instance ID: {self._manager.instance_id}")
        logger.info("Jobs registered:")
        for job_id, meta in self._manager._config and {} or {}.items():
            pass  # Jobs are registered via manager

        # Log registered jobs
        jobs = self._manager.get_jobs()
        for job in jobs:
            next_run = job.next_run_time
            logger.info(f"  - {job.id} ({job.name}): next run at {next_run}")

        logger.info("=" * 60)
        logger.info("Scheduler is running. Press Ctrl+C to stop.")

        # Keep main thread alive
        self._wait_loop()

    def _wait_loop(self):
        """Main wait loop - keeps the service running"""
        import time
        from datetime import datetime

        while self._running:
            time.sleep(60)  # Check every minute

            if self._manager and self._manager.is_running():
                jobs = self._manager.get_jobs()
                logger.debug(f"[{datetime.now().strftime('%H:%M')}] " f"Scheduler alive, {len(jobs)} jobs registered")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals"""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name}, shutting down...")
        self.stop()

    def stop(self):
        """Stop the scheduler service"""
        self._running = False

        if self._manager:
            logger.info("Stopping scheduler...")
            self._manager.stop()
            logger.info("Scheduler stopped")

        logger.info("Scheduler service shutdown complete")
        sys.exit(0)


def create_systemd_service():
    """Generate a systemd service file for this scheduler"""
    service_content = """[Unit]
Description=Fund Daily Scheduler Service
After=network.target redis.service postgresql.service
Wants=redis.service postgresql.service

[Service]
Type=simple
User=kid
WorkingDirectory=/home/kid/fund-daily
Environment=SCHEDULER_STANDALONE=true
Environment=REDIS_HOST=localhost
Environment=REDIS_PORT=6379
Environment=REDIS_DB=1
Environment=SCHEDULER_LOG_LEVEL=INFO
Environment=SCHEDULER_CLUSTER_ENABLED=true
ExecStart=/usr/bin/python3 /home/kid/fund-daily/scripts/scheduler_service.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/fund-daily-scheduler.log
StandardError=append:/var/log/fund-daily-scheduler.log

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/kid/fund-daily

[Install]
WantedBy=multi-user.target
"""
    return service_content


def main():
    """Main entry point"""
    args = parse_args()

    # Handle special commands
    if len(sys.argv) > 1 and sys.argv[1] == "--systemd-service":
        print(create_systemd_service())
        print("\n# To install:")
        print("# 1. Save output to /etc/systemd/system/fund-daily-scheduler.service")
        print("# 2. Run: sudo systemctl daemon-reload")
        print("# 3. Run: sudo systemctl enable fund-daily-scheduler")
        print("# 4. Run: sudo systemctl start fund-daily-scheduler")
        return

    service = SchedulerService(args)
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        service.stop()
    except Exception as e:
        logger.exception(f"Scheduler service crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
