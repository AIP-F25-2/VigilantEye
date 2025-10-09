#!/usr/bin/env python3
"""
VIGILANTEye Deployment Script
Automates the deployment process for various platforms
"""

import os
import subprocess
import sys
import json

def check_requirements():
    """Check if required tools are installed"""
    print("Checking deployment requirements...")
    
    # Check if git is installed
    try:
        subprocess.run(['git', '--version'], capture_output=True, check=True)
        print("Git is installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Git is not installed. Please install Git first.")
        return False
    
    return True

def prepare_deployment():
    """Prepare the application for deployment"""
    print("📦 Preparing application for deployment...")
    
    # Ensure all required files exist
    required_files = ['Procfile', 'runtime.txt', 'requirements.txt', 'demo_app.py']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Missing required file: {file}")
            return False
        print(f"✅ Found {file}")
    
    # Check if git repository is initialized
    if not os.path.exists('.git'):
        print("🔧 Initializing Git repository...")
        subprocess.run(['git', 'init'], check=True)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit for deployment'], check=True)
        print("✅ Git repository initialized")
    
    return True

def deploy_railway():
    """Deploy to Railway"""
    print("🚀 Deploying to Railway...")
    print("Please follow these steps:")
    print("1. Go to https://railway.app")
    print("2. Sign up/Login with GitHub")
    print("3. Click 'New Project' → 'Deploy from GitHub repo'")
    print("4. Select your VIGILANTEye repository")
    print("5. Railway will automatically deploy your app")
    print("6. Your app will be available at https://your-app-name.railway.app")

def deploy_heroku():
    """Deploy to Heroku"""
    print("🚀 Deploying to Heroku...")
    
    try:
        # Check if Heroku CLI is installed
        subprocess.run(['heroku', '--version'], capture_output=True, check=True)
        print("✅ Heroku CLI is installed")
        
        # Create Heroku app
        app_name = input("Enter your Heroku app name (or press Enter for auto-generated): ").strip()
        if app_name:
            subprocess.run(['heroku', 'create', app_name], check=True)
        else:
            subprocess.run(['heroku', 'create'], check=True)
        
        # Deploy
        subprocess.run(['git', 'push', 'heroku', 'main'], check=True)
        
        # Open app
        subprocess.run(['heroku', 'open'], check=True)
        
        print("✅ Successfully deployed to Heroku!")
        
    except subprocess.CalledProcessError:
        print("❌ Heroku CLI not found. Please install it from https://devcenter.heroku.com/articles/heroku-cli")
    except FileNotFoundError:
        print("❌ Heroku CLI not found. Please install it from https://devcenter.heroku.com/articles/heroku-cli")

def deploy_vercel():
    """Deploy to Vercel"""
    print("🚀 Deploying to Vercel...")
    
    try:
        # Check if Vercel CLI is installed
        subprocess.run(['vercel', '--version'], capture_output=True, check=True)
        print("✅ Vercel CLI is installed")
        
        # Deploy
        subprocess.run(['vercel', '--prod'], check=True)
        
        print("✅ Successfully deployed to Vercel!")
        
    except subprocess.CalledProcessError:
        print("❌ Vercel CLI not found. Please install it with: npm i -g vercel")
    except FileNotFoundError:
        print("❌ Vercel CLI not found. Please install it with: npm i -g vercel")

def main():
    """Main deployment function"""
    print("VIGILANTEye Deployment Assistant")
    print("=" * 40)
    
    if not check_requirements():
        sys.exit(1)
    
    if not prepare_deployment():
        sys.exit(1)
    
    print("\n🚀 Choose your deployment platform:")
    print("1. Railway (Recommended - Easiest)")
    print("2. Heroku (Popular Platform)")
    print("3. Vercel (Frontend + Backend)")
    print("4. Manual Instructions")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        deploy_railway()
    elif choice == '2':
        deploy_heroku()
    elif choice == '3':
        deploy_vercel()
    elif choice == '4':
        print("\n📖 Manual Deployment Instructions:")
        print("See DEPLOYMENT.md for detailed instructions")
    else:
        print("❌ Invalid choice. Please run the script again.")
        sys.exit(1)
    
    print("\n🎉 Deployment process completed!")
    print("Your VIGILANTEye app will be accessible online once deployed.")

if __name__ == '__main__':
    main()
