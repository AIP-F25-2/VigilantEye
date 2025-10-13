"""
Analytics DAG
Daily analytics generation and reporting
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import requests
import os
import json

default_args = {
    'owner': 'vigilanteye',
    'depends_on_past': False,
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

VIGILANTEYE_API_URL = os.getenv('VIGILANTEYE_API_URL')
VIGILANTEYE_API_KEY = os.getenv('VIGILANTEYE_API_KEY')

def extract_metrics(**context):
    """Extract daily metrics"""
    print("Extracting metrics from VIGILANTEye...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1)
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/analytics/metrics"
    headers = {'Authorization': f'Bearer {VIGILANTEYE_API_KEY}'}
    params = {
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    metrics = {
        'total_videos': 0,
        'total_recordings': 0,
        'total_alerts': 0,
        'active_cameras': 0,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat()
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            api_metrics = response.json()
            metrics.update(api_metrics)
            print(f"✅ Extracted metrics: {json.dumps(metrics, indent=2)}")
    except Exception as e:
        print(f"⚠️ Using default metrics due to: {str(e)}")
    
    context['task_instance'].xcom_push(key='metrics', value=metrics)
    return metrics

def calculate_trends(**context):
    """Calculate trends and patterns"""
    metrics = context['task_instance'].xcom_pull(key='metrics', task_ids='extract_metrics')
    
    print("Calculating trends...")
    
    # Calculate trends (would compare with historical data)
    trends = {
        'alerts_trend': 'stable',  # up, down, stable
        'recording_trend': 'up',
        'camera_usage': 'normal',
        'peak_hours': [9, 10, 14, 15, 16],  # Example peak hours
    }
    
    context['task_instance'].xcom_push(key='trends', value=trends)
    return trends

def generate_insights(**context):
    """Generate AI insights from metrics and trends"""
    metrics = context['task_instance'].xcom_pull(key='metrics', task_ids='extract_metrics')
    trends = context['task_instance'].xcom_pull(key='trends', task_ids='calculate_trends')
    
    print("Generating insights...")
    
    insights = []
    
    # Alert analysis
    if metrics['total_alerts'] > 50:
        insights.append({
            'type': 'warning',
            'category': 'alerts',
            'message': f"High alert count: {metrics['total_alerts']} alerts in past 24h",
            'recommendation': 'Review alert thresholds and false positive rate'
        })
    
    # Camera health
    if metrics['active_cameras'] == 0:
        insights.append({
            'type': 'error',
            'category': 'cameras',
            'message': 'No active cameras detected',
            'recommendation': 'Check camera connections and restart devices'
        })
    elif metrics['active_cameras'] < 5:
        insights.append({
            'type': 'info',
            'category': 'cameras',
            'message': f"{metrics['active_cameras']} cameras active",
            'recommendation': 'Consider adding more surveillance coverage'
        })
    
    # Recording analysis
    avg_recordings_per_camera = metrics['total_recordings'] / max(metrics['active_cameras'], 1)
    if avg_recordings_per_camera > 100:
        insights.append({
            'type': 'warning',
            'category': 'storage',
            'message': f"High recording rate: {avg_recordings_per_camera:.1f} per camera",
            'recommendation': 'Review retention policy to manage storage'
        })
    
    print(f"✅ Generated {len(insights)} insights")
    context['task_instance'].xcom_push(key='insights', value=insights)
    return insights

def save_analytics(**context):
    """Save analytics to database"""
    metrics = context['task_instance'].xcom_pull(key='metrics', task_ids='extract_metrics')
    trends = context['task_instance'].xcom_pull(key='trends', task_ids='calculate_trends')
    insights = context['task_instance'].xcom_pull(key='insights', task_ids='generate_insights')
    
    print("Saving analytics to database...")
    
    analytics_data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'metrics': metrics,
        'trends': trends,
        'insights': insights,
        'generated_at': datetime.now().isoformat()
    }
    
    url = f"{VIGILANTEYE_API_URL}/api/v2/analytics"
    headers = {
        'Authorization': f'Bearer {VIGILANTEYE_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, json=analytics_data, headers=headers)
        response.raise_for_status()
        print("✅ Analytics saved successfully")
    except Exception as e:
        print(f"❌ Error saving analytics: {str(e)}")

def send_daily_report(**context):
    """Send daily analytics report"""
    metrics = context['task_instance'].xcom_pull(key='metrics', task_ids='extract_metrics')
    insights = context['task_instance'].xcom_pull(key='insights', task_ids='generate_insights')
    
    print("\n" + "=" * 60)
    print("VIGILANTEYE DAILY ANALYTICS REPORT")
    print("=" * 60)
    print(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nKEY METRICS:")
    print(f"  • Total Videos: {metrics['total_videos']}")
    print(f"  • Total Recordings: {metrics['total_recordings']}")
    print(f"  • Total Alerts: {metrics['total_alerts']}")
    print(f"  • Active Cameras: {metrics['active_cameras']}")
    
    print(f"\nINSIGHTS ({len(insights)}):")
    for i, insight in enumerate(insights, 1):
        print(f"  {i}. [{insight['type'].upper()}] {insight['message']}")
        print(f"     → {insight['recommendation']}")
    
    print("=" * 60 + "\n")
    
    # Here you would send actual email/Slack notification
    return True

with DAG(
    'analytics_pipeline',
    default_args=default_args,
    description='Daily analytics generation and insights',
    schedule_interval='0 2 * * *',  # Run at 2 AM daily
    start_date=datetime(2025, 10, 1),
    catchup=False,
    tags=['vigilanteye', 'analytics', 'reporting'],
) as dag:

    extract = PythonOperator(
        task_id='extract_metrics',
        python_callable=extract_metrics,
    )

    calculate = PythonOperator(
        task_id='calculate_trends',
        python_callable=calculate_trends,
    )

    insights = PythonOperator(
        task_id='generate_insights',
        python_callable=generate_insights,
    )

    save = PythonOperator(
        task_id='save_analytics',
        python_callable=save_analytics,
    )

    report = PythonOperator(
        task_id='send_report',
        python_callable=send_daily_report,
    )

    # ETL flow
    extract >> calculate >> insights >> save >> report

