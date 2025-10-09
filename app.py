#!/usr/bin/env python3
"""
VIGILANTEye Production Application
Optimized for production deployment
"""

from demo_app import app

if __name__ == '__main__':
    import os
    
    # Production configuration
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print("🚀 Starting VIGILANTEye Production Server...")
    print(f"🌐 Port: {port}")
    print(f"🔧 Debug: {debug}")
    print("=" * 50)
    
    app.run(debug=debug, host='0.0.0.0', port=port)