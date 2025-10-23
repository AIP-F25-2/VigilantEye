"""
Database migration and backup management system.
"""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class DatabaseMigrator:
    """Handle database migrations using Alembic."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.session_factory = sessionmaker(bind=self.engine)
    
    def create_migration(self, message: str) -> str:
        """Create a new migration."""
        try:
            result = subprocess.run([
                'alembic', 'revision', '--autogenerate', '-m', message
            ], capture_output=True, text=True, cwd='backend')
            
            if result.returncode == 0:
                logger.info(f"Migration created: {message}")
                return result.stdout.strip()
            else:
                logger.error(f"Failed to create migration: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error creating migration: {e}")
            return None
    
    def upgrade_database(self, revision: str = "head") -> bool:
        """Upgrade database to specified revision."""
        try:
            result = subprocess.run([
                'alembic', 'upgrade', revision
            ], capture_output=True, text=True, cwd='backend')
            
            if result.returncode == 0:
                logger.info(f"Database upgraded to {revision}")
                return True
            else:
                logger.error(f"Failed to upgrade database: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error upgrading database: {e}")
            return False
    
    def downgrade_database(self, revision: str) -> bool:
        """Downgrade database to specified revision."""
        try:
            result = subprocess.run([
                'alembic', 'downgrade', revision
            ], capture_output=True, text=True, cwd='backend')
            
            if result.returncode == 0:
                logger.info(f"Database downgraded to {revision}")
                return True
            else:
                logger.error(f"Failed to downgrade database: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error downgrading database: {e}")
            return False
    
    def get_current_revision(self) -> str:
        """Get current database revision."""
        try:
            result = subprocess.run([
                'alembic', 'current'
            ], capture_output=True, text=True, cwd='backend')
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Failed to get current revision: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error getting current revision: {e}")
            return None
    
    def get_migration_history(self) -> List[Dict[str, str]]:
        """Get migration history."""
        try:
            result = subprocess.run([
                'alembic', 'history', '--verbose'
            ], capture_output=True, text=True, cwd='backend')
            
            if result.returncode == 0:
                # Parse migration history
                migrations = []
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Rev:' in line:
                        parts = line.split()
                        migrations.append({
                            'revision': parts[1],
                            'description': ' '.join(parts[3:])
                        })
                return migrations
            else:
                logger.error(f"Failed to get migration history: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting migration history: {e}")
            return []

class DatabaseBackupManager:
    """Manage database backups."""
    
    def __init__(self, database_url: str, backup_dir: str = "backups"):
        self.database_url = database_url
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize S3 client for cloud backups
        self.s3_client = boto3.client('s3') if os.getenv('AWS_ACCESS_KEY_ID') else None
    
    def create_backup(self, backup_name: str = None) -> str:
        """Create a database backup."""
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
        
        backup_path = self.backup_dir / f"{backup_name}.sql"
        
        try:
            # Extract database connection details
            if self.database_url.startswith('postgresql://'):
                self._create_postgres_backup(backup_path)
            elif self.database_url.startswith('mysql://'):
                self._create_mysql_backup(backup_path)
            else:
                raise ValueError(f"Unsupported database type: {self.database_url}")
            
            logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def _create_postgres_backup(self, backup_path: Path):
        """Create PostgreSQL backup using pg_dump."""
        # Parse connection string
        url_parts = self.database_url.replace('postgresql://', '').split('/')
        db_name = url_parts[1]
        auth_parts = url_parts[0].split('@')
        user_pass = auth_parts[0].split(':')
        host_port = auth_parts[1].split(':')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Run pg_dump
        cmd = [
            'pg_dump',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', db_name,
            '--no-password',
            '--verbose',
            '--clean',
            '--if-exists',
            '--create'
        ]
        
        with open(backup_path, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)
            
        if result.returncode != 0:
            raise Exception(f"pg_dump failed: {result.stderr.decode()}")
    
    def _create_mysql_backup(self, backup_path: Path):
        """Create MySQL backup using mysqldump."""
        # Parse connection string
        url_parts = self.database_url.replace('mysql://', '').split('/')
        db_name = url_parts[1]
        auth_parts = url_parts[0].split('@')
        user_pass = auth_parts[0].split(':')
        host_port = auth_parts[1].split(':')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '3306'
        
        # Run mysqldump
        cmd = [
            'mysqldump',
            '-h', host,
            '-P', port,
            '-u', username,
            f'-p{password}',
            '--single-transaction',
            '--routines',
            '--triggers',
            db_name
        ]
        
        with open(backup_path, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE)
            
        if result.returncode != 0:
            raise Exception(f"mysqldump failed: {result.stderr.decode()}")
    
    def restore_backup(self, backup_path: str) -> bool:
        """Restore database from backup."""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            if self.database_url.startswith('postgresql://'):
                self._restore_postgres_backup(backup_file)
            elif self.database_url.startswith('mysql://'):
                self._restore_mysql_backup(backup_file)
            else:
                raise ValueError(f"Unsupported database type: {self.database_url}")
            
            logger.info(f"Backup restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def _restore_postgres_backup(self, backup_file: Path):
        """Restore PostgreSQL backup using psql."""
        # Parse connection string
        url_parts = self.database_url.replace('postgresql://', '').split('/')
        db_name = url_parts[1]
        auth_parts = url_parts[0].split('@')
        user_pass = auth_parts[0].split(':')
        host_port = auth_parts[1].split(':')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '5432'
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Run psql
        cmd = [
            'psql',
            '-h', host,
            '-p', port,
            '-U', username,
            '-d', db_name,
            '--no-password'
        ]
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, env=env)
            
        if result.returncode != 0:
            raise Exception(f"psql restore failed: {result.stderr.decode()}")
    
    def _restore_mysql_backup(self, backup_file: Path):
        """Restore MySQL backup using mysql."""
        # Parse connection string
        url_parts = self.database_url.replace('mysql://', '').split('/')
        db_name = url_parts[1]
        auth_parts = url_parts[0].split('@')
        user_pass = auth_parts[0].split(':')
        host_port = auth_parts[1].split(':')
        
        username = user_pass[0]
        password = user_pass[1] if len(user_pass) > 1 else ''
        host = host_port[0]
        port = host_port[1] if len(host_port) > 1 else '3306'
        
        # Run mysql
        cmd = [
            'mysql',
            '-h', host,
            '-P', port,
            '-u', username,
            f'-p{password}',
            db_name
        ]
        
        with open(backup_file, 'r') as f:
            result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE)
            
        if result.returncode != 0:
            raise Exception(f"mysql restore failed: {result.stderr.decode()}")
    
    def upload_to_s3(self, backup_path: str, bucket_name: str) -> bool:
        """Upload backup to S3."""
        if not self.s3_client:
            logger.error("S3 client not configured")
            return False
        
        try:
            backup_file = Path(backup_path)
            s3_key = f"database-backups/{backup_file.name}"
            
            self.s3_client.upload_file(backup_path, bucket_name, s3_key)
            logger.info(f"Backup uploaded to S3: s3://{bucket_name}/{s3_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload backup to S3: {e}")
            return False
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Clean up old backup files."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for backup_file in self.backup_dir.glob("*.sql"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")

class DatabaseHealthChecker:
    """Check database health and performance."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
    
    def check_connection(self) -> bool:
        """Check database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def check_performance(self) -> Dict[str, Any]:
        """Check database performance metrics."""
        try:
            with self.engine.connect() as conn:
                # Get basic performance metrics
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_connections,
                        AVG(EXTRACT(EPOCH FROM (now() - query_start))) as avg_query_time
                    FROM pg_stat_activity 
                    WHERE state = 'active'
                """))
                
                row = result.fetchone()
                return {
                    'total_connections': row[0],
                    'avg_query_time': float(row[1]) if row[1] else 0
                }
        except Exception as e:
            logger.error(f"Performance check failed: {e}")
            return {}
    
    def check_table_sizes(self) -> Dict[str, int]:
        """Check table sizes."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """))
                
                table_sizes = {}
                for row in result:
                    table_sizes[row[1]] = row[2]
                
                return table_sizes
        except Exception as e:
            logger.error(f"Table size check failed: {e}")
            return {}
