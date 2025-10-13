"""
Video Processing DAG
Orchestrates video analysis and processing workflows
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
import requests
import os
import json

default_args = {
    'owner': 'vigilanteye',
    'depends_on_past': False,
    'email_on_failure': True,
    'email': ['admin@vigilanteye.com'],
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Configuration
VIGILANTEYE_API_URL = os.getenv('VIGILANTEYE_API_URL')
VIGILANTEYE_API_KEY = os.getenv('VIGILANTEYE_API_KEY')

def get_api_headers():
    """Get API headers with authentication"""
    return {
        'Authorization': f'Bearer {VIGILANTEYE_API_KEY}',
        'Content-Type': 'application/json'
    }

def fetch_pending_videos(**context):
    """Fetch videos pending analysis"""
    print(f"Fetching pending videos from {VIGILANTEYE_API_URL}")
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/videos?status=pending"
    
    try:
        response = requests.get(url, headers=get_api_headers(), timeout=30)
        response.raise_for_status()
        
        videos = response.json().get('videos', [])
        print(f"Found {len(videos)} pending videos")
        
        context['task_instance'].xcom_push(key='pending_videos', value=videos)
        return len(videos)
    except Exception as e:
        print(f"Error fetching videos: {str(e)}")
        return 0

def process_videos(**context):
    """Process each pending video"""
    videos = context['task_instance'].xcom_pull(key='pending_videos', task_ids='fetch_videos')
    
    if not videos:
        print("No videos to process")
        return {'processed': 0, 'failed': 0}
    
    processed_count = 0
    failed_count = 0
    
    for video in videos:
        video_id = video.get('id')
        print(f"Processing video ID: {video_id}")
        
        try:
            # Trigger processing
            url = f"{VIGILANTEYE_API_URL}/api/v2/videos/{video_id}/analyze"
            response = requests.post(url, headers=get_api_headers(), timeout=120)
            response.raise_for_status()
            
            processed_count += 1
            print(f"✅ Video {video_id} processed successfully")
            
        except Exception as e:
            failed_count += 1
            print(f"❌ Error processing video {video_id}: {str(e)}")
    
    result = {'processed': processed_count, 'failed': failed_count}
    context['task_instance'].xcom_push(key='processing_results', value=result)
    return result

def generate_thumbnails(**context):
    """Generate thumbnails for processed videos"""
    results = context['task_instance'].xcom_pull(key='processing_results', task_ids='process_videos')
    
    print(f"Generating thumbnails for {results['processed']} videos...")
    
    # Implementation would call thumbnail generation endpoint
    return results['processed']

def update_analytics(**context):
    """Update analytics dashboard with new data"""
    print("Updating analytics dashboard...")
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/analytics/refresh"
    
    try:
        response = requests.post(url, headers=get_api_headers())
        response.raise_for_status()
        print("✅ Analytics updated successfully")
    except Exception as e:
        print(f"❌ Error updating analytics: {str(e)}")

def cleanup_temp_files(**context):
    """Clean up temporary files from processing"""
    print("Cleaning up temporary files...")
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/system/cleanup"
    
    try:
        response = requests.post(url, headers=get_api_headers())
        response.raise_for_status()
        print("✅ Cleanup completed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {str(e)}")

# Define DAG
with DAG(
    'video_processing_pipeline',
    default_args=default_args,
    description='Process and analyze surveillance videos',
    schedule_interval=timedelta(hours=1),  # Run every hour
    start_date=datetime(2025, 10, 1),
    catchup=False,
    tags=['vigilanteye', 'video', 'processing'],
) as dag:

    fetch_videos = PythonOperator(
        task_id='fetch_videos',
        python_callable=fetch_pending_videos,
    )

    process = PythonOperator(
        task_id='process_videos',
        python_callable=process_videos,
    )

    thumbnails = PythonOperator(
        task_id='generate_thumbnails',
        python_callable=generate_thumbnails,
    )

    analytics = PythonOperator(
        task_id='update_analytics',
        python_callable=update_analytics,
    )

    cleanup = PythonOperator(
        task_id='cleanup',
        python_callable=cleanup_temp_files,
    )

    # Pipeline flow
    fetch_videos >> process >> thumbnails >> analytics >> cleanup

