#!/usr/bin/env python3
"""Script to reset a user's password"""
import sys
from app import create_app, db
from app.models.user import User

def reset_password(email, new_password):
    """Reset password for a user"""
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"User with email {email} not found")
            return False
        
        # Set new password (this will generate a new hash with the correct length)
        user.set_password(new_password)
        user.save()
        
        print(f"Password reset successfully for {email}")
        return True

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 6:
        print("Error: Password must be at least 6 characters long")
        sys.exit(1)
    
    reset_password(email, new_password)

