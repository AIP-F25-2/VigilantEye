#!/usr/bin/env python3
"""
VIGILANTEye Simple Deployment Script
"""

import os
import subprocess
import sys

def main():
    print("VIGILANTEye Deployment Assistant")
    print("=" * 40)
    
    print("\nDeployment Options:")
    print("1. Railway (Recommended - Easiest)")
    print("2. Heroku (Popular Platform)")
    print("3. Vercel (Frontend + Backend)")
    print("4. Manual Instructions")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        print("\nRailway Deployment Instructions:")
        print("1. Go to https://railway.app")
        print("2. Sign up/Login with GitHub")
        print("3. Click 'New Project' -> 'Deploy from GitHub repo'")
        print("4. Select your VIGILANTEye repository")
        print("5. Railway will automatically deploy your app")
        print("6. Your app will be available at https://your-app-name.railway.app")
        
    elif choice == '2':
        print("\nHeroku Deployment Instructions:")
        print("1. Install Heroku CLI from https://devcenter.heroku.com/articles/heroku-cli")
        print("2. Run: heroku login")
        print("3. Run: heroku create your-app-name")
        print("4. Run: git push heroku main")
        print("5. Run: heroku open")
        
    elif choice == '3':
        print("\nVercel Deployment Instructions:")
        print("1. Install Vercel CLI: npm i -g vercel")
        print("2. Run: vercel login")
        print("3. Run: vercel --prod")
        print("4. Follow the prompts")
        
    elif choice == '4':
        print("\nManual Deployment Instructions:")
        print("See DEPLOYMENT.md for detailed instructions")
        
    else:
        print("Invalid choice. Please run the script again.")
        sys.exit(1)
    
    print("\nDeployment process completed!")
    print("Your VIGILANTEye app will be accessible online once deployed.")

if __name__ == '__main__':
    main()
