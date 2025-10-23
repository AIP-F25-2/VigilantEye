#!/usr/bin/env python3
"""
Script to add sample camera devices to the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.device import Device, DeviceType, DeviceStatus

def add_sample_devices():
    """Add sample camera devices to the database"""
    app = create_app()
    
    with app.app_context():
        # Check if devices already exist
        existing_devices = Device.query.count()
        if existing_devices > 0:
            print(f"Found {existing_devices} existing devices. Skipping sample data creation.")
            return
        
        # Sample camera devices
        sample_devices = [
            {
                'device_id': 'cam_001',
                'name': 'Front Door Camera',
                'device_type': DeviceType.RTSP,
                'connection_string': 'rtsp://192.168.1.100:554/stream1',
                'rtsp_url': 'rtsp://192.168.1.100:554/stream1',
                'ip_address': '192.168.1.100',
                'port': 554,
                'manufacturer': 'Hikvision',
                'model': 'DS-2CD2143G0-I',
                'version': 'V5.6.0',
                'serial_number': 'HK001234567',
                'driver': 'RTSP',
                'capabilities': {
                    'motion_detection': True,
                    'night_vision': True,
                    'audio': True,
                    'ptz': False
                },
                'supported_formats': ['H.264', 'H.265'],
                'supported_resolutions': ['1920x1080', '1280x720', '640x480'],
                'supported_framerates': ['30fps', '25fps', '15fps'],
                'default_settings': {
                    'resolution': '1920x1080',
                    'fps': 30,
                    'quality': 'high'
                },
                'current_settings': {
                    'resolution': '1920x1080',
                    'fps': 30,
                    'quality': 'high'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': True
            },
            {
                'device_id': 'cam_002',
                'name': 'Backyard Camera',
                'device_type': DeviceType.RTSP,
                'connection_string': 'rtsp://192.168.1.101:554/stream1',
                'rtsp_url': 'rtsp://192.168.1.101:554/stream1',
                'ip_address': '192.168.1.101',
                'port': 554,
                'manufacturer': 'Dahua',
                'model': 'IPC-HFW4431R-Z',
                'version': 'V2.800.0000000.0.R',
                'serial_number': 'DH001234568',
                'driver': 'RTSP',
                'capabilities': {
                    'motion_detection': True,
                    'night_vision': True,
                    'audio': False,
                    'ptz': True
                },
                'supported_formats': ['H.264', 'H.265'],
                'supported_resolutions': ['1920x1080', '1280x720', '640x480'],
                'supported_framerates': ['30fps', '25fps', '15fps'],
                'default_settings': {
                    'resolution': '1920x1080',
                    'fps': 25,
                    'quality': 'high'
                },
                'current_settings': {
                    'resolution': '1920x1080',
                    'fps': 25,
                    'quality': 'high'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': False
            },
            {
                'device_id': 'cam_003',
                'name': 'Garage Camera',
                'device_type': DeviceType.IP,
                'connection_string': 'http://192.168.1.102:8080/video',
                'ip_address': '192.168.1.102',
                'port': 8080,
                'manufacturer': 'Axis',
                'model': 'M3045-V',
                'version': '9.80.3.5',
                'serial_number': 'AX001234569',
                'driver': 'HTTP',
                'capabilities': {
                    'motion_detection': True,
                    'night_vision': False,
                    'audio': True,
                    'ptz': False
                },
                'supported_formats': ['H.264', 'MJPEG'],
                'supported_resolutions': ['1920x1080', '1280x720', '640x480'],
                'supported_framerates': ['30fps', '25fps', '15fps'],
                'default_settings': {
                    'resolution': '1280x720',
                    'fps': 25,
                    'quality': 'medium'
                },
                'current_settings': {
                    'resolution': '1280x720',
                    'fps': 25,
                    'quality': 'medium'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': False
            },
            {
                'device_id': 'webcam_001',
                'name': 'Office Webcam',
                'device_type': DeviceType.WEBCAM,
                'connection_string': '/dev/video0',
                'manufacturer': 'Logitech',
                'model': 'C920',
                'version': '1.0',
                'serial_number': 'LG001234570',
                'driver': 'V4L2',
                'capabilities': {
                    'motion_detection': False,
                    'night_vision': False,
                    'audio': True,
                    'ptz': False
                },
                'supported_formats': ['H.264', 'MJPEG'],
                'supported_resolutions': ['1920x1080', '1280x720', '640x480'],
                'supported_framerates': ['30fps', '25fps', '15fps'],
                'default_settings': {
                    'resolution': '1280x720',
                    'fps': 30,
                    'quality': 'high'
                },
                'current_settings': {
                    'resolution': '1280x720',
                    'fps': 30,
                    'quality': 'high'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': False
            },
            {
                'device_id': 'mock_001',
                'name': 'Demo Camera 1',
                'device_type': DeviceType.RTSP,
                'connection_string': 'mock://demo/camera1',
                'rtsp_url': 'mock://demo/camera1',
                'manufacturer': 'Demo',
                'model': 'Mock Camera',
                'version': '1.0',
                'serial_number': 'MOCK001',
                'driver': 'MOCK',
                'capabilities': {
                    'motion_detection': True,
                    'night_vision': True,
                    'audio': True,
                    'ptz': True
                },
                'supported_formats': ['H.264', 'H.265'],
                'supported_resolutions': ['1920x1080', '1280x720', '640x480'],
                'supported_framerates': ['30fps', '25fps', '15fps'],
                'default_settings': {
                    'resolution': '1920x1080',
                    'fps': 30,
                    'quality': 'high'
                },
                'current_settings': {
                    'resolution': '1920x1080',
                    'fps': 30,
                    'quality': 'high'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': False
            },
            {
                'device_id': 'mock_002',
                'name': 'Demo Camera 2',
                'device_type': DeviceType.RTSP,
                'connection_string': 'mock://demo/camera2',
                'rtsp_url': 'mock://demo/camera2',
                'manufacturer': 'Demo',
                'model': 'Mock Camera',
                'version': '1.0',
                'serial_number': 'MOCK002',
                'driver': 'MOCK',
                'capabilities': {
                    'motion_detection': True,
                    'night_vision': False,
                    'audio': False,
                    'ptz': False
                },
                'supported_formats': ['H.264'],
                'supported_resolutions': ['1280x720', '640x480'],
                'supported_framerates': ['25fps', '15fps'],
                'default_settings': {
                    'resolution': '1280x720',
                    'fps': 25,
                    'quality': 'medium'
                },
                'current_settings': {
                    'resolution': '1280x720',
                    'fps': 25,
                    'quality': 'medium'
                },
                'status': DeviceStatus.AVAILABLE,
                'is_default': False
            }
        ]
        
        # Add devices to database
        for device_data in sample_devices:
            device = Device(**device_data)
            db.session.add(device)
        
        try:
            db.session.commit()
            print(f"Successfully added {len(sample_devices)} sample camera devices!")
            print("\nSample devices added:")
            for device_data in sample_devices:
                print(f"  - {device_data['name']} ({device_data['device_type'].value}) - {device_data['device_id']}")
        except Exception as e:
            db.session.rollback()
            print(f"Error adding sample devices: {e}")
            raise

if __name__ == '__main__':
    add_sample_devices()
