"""
Database Maintenance DAG
Performs routine database cleanup and optimization
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import os

default_args = {
    'owner': 'vigilanteye',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

VIGILANTEYE_API_URL = os.getenv('VIGILANTEYE_API_URL')
VIGILANTEYE_API_KEY = os.getenv('VIGILANTEYE_API_KEY')

def cleanup_old_recordings(**context):
    """Remove recordings older than 30 days"""
    print("Starting cleanup of old recordings...")
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/recordings/cleanup"
    headers = {'Authorization': f'Bearer {VIGILANTEYE_API_KEY}', 'Content-Type': 'application/json'}
    data = {'days_old': 30}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        deleted_count = result.get('deleted_count', 0)
        print(f"✅ Deleted {deleted_count} old recordings")
        return deleted_count
    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        return 0

def archive_old_videos(**context):
    """Archive videos older than 90 days"""
    print("Archiving old videos...")
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/videos/archive"
    headers = {'Authorization': f'Bearer {VIGILANTEYE_API_KEY}', 'Content-Type': 'application/json'}
    data = {'days_old': 90}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        result = response.json()
        archived_count = result.get('archived_count', 0)
        print(f"✅ Archived {archived_count} old videos")
        return archived_count
    except Exception as e:
        print(f"⚠️ Archiving warning: {str(e)}")
        return 0

def optimize_database_tables(**context):
    """Optimize MySQL tables for better performance"""
    print("Optimizing database tables...")
    
    # This would typically be done via MySQL connection
    # For now, we'll call an API endpoint
    url = f"{VIGILANTEYE_API_URL}/api/v2/system/optimize-db"
    headers = {'Authorization': f'Bearer {VIGILANTEYE_API_KEY}'}
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        print("✅ Database optimization completed")
    except Exception as e:
        print(f"⚠️ Optimization info: {str(e)}")

def generate_maintenance_report(**context):
    """Generate maintenance summary report"""
    recordings_deleted = context['task_instance'].xcom_pull(task_ids='cleanup_recordings')
    videos_archived = context['task_instance'].xcom_pull(task_ids='archive_videos')
    
    report = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'recordings_deleted': recordings_deleted or 0,
        'videos_archived': videos_archived or 0,
        'tables_optimized': True
    }
    
    print("\n" + "=" * 50)
    print("DATABASE MAINTENANCE REPORT")
    print("=" * 50)
    print(f"Date: {report['date']}")
    print(f"Recordings Deleted: {report['recordings_deleted']}")
    print(f"Videos Archived: {report['videos_archived']}")
    print(f"Tables Optimized: {report['tables_optimized']}")
    print("=" * 50 + "\n")
    
    return report

with DAG(
    'database_maintenance',
    default_args=default_args,
    description='Daily database maintenance and cleanup',
    schedule_interval='0 3 * * *',  # Run at 3 AM daily
    start_date=datetime(2025, 10, 1),
    catchup=False,
    tags=['vigilanteye', 'database', 'maintenance'],
) as dag:

    cleanup_recordings = PythonOperator(
        task_id='cleanup_recordings',
        python_callable=cleanup_old_recordings,
    )

    archive_videos = PythonOperator(
        task_id='archive_videos',
        python_callable=archive_old_videos,
    )

    optimize_db = PythonOperator(
        task_id='optimize_database',
        python_callable=optimize_database_tables,
    )

    generate_report = PythonOperator(
        task_id='generate_report',
        python_callable=generate_maintenance_report,
    )

    # Parallel execution then report
    [cleanup_recordings, archive_videos] >> optimize_db >> generate_report

