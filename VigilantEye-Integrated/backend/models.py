import bcrypt
from database import get_db_connection

class User:
    def __init__(self, id=None, username=None, email=None, password_hash=None, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at
    
    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt)
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def save(self):
        """Save user to database"""
        connection = get_db_connection()
        if not connection:
            return False
        
        try:
            cursor = connection.cursor()
            
            # Check if username or email already exists
            check_query = "SELECT id FROM users WHERE username = %s OR email = %s"
            cursor.execute(check_query, (self.username, self.email))
            if cursor.fetchone():
                return False  # User already exists
            
            # Insert new user
            insert_query = """
            INSERT INTO users (username, email, password_hash) 
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (self.username, self.email, self.password_hash))
            connection.commit()
            
            # Get the inserted user's ID
            self.id = cursor.lastrowid
            return True
            
        except Exception as e:
            print(f"Error saving user: {e}")
            return False
        finally:
            try:
                cursor.close()
                connection.close()
            except Exception:
                pass
    
    @staticmethod
    def find_by_username(username):
        """Find user by username"""
        connection = get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor()
            query = "SELECT * FROM users WHERE username = %s"
            cursor.execute(query, (username,))
            result = cursor.fetchone()
            
            if result:
                return User(
                    id=result['id'],
                    username=result['username'],
                    email=result['email'],
                    password_hash=result['password_hash'],
                    created_at=result['created_at']
                )
            return None
            
        except Exception as e:
            print(f"Error finding user: {e}")
            return None
        finally:
            try:
                cursor.close()
                connection.close()
            except Exception:
                pass
    
    @staticmethod
    def find_by_email(email):
        """Find user by email"""
        connection = get_db_connection()
        if not connection:
            return None
        
        try:
            cursor = connection.cursor()
            query = "SELECT * FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            
            if result:
                return User(
                    id=result['id'],
                    username=result['username'],
                    email=result['email'],
                    password_hash=result['password_hash'],
                    created_at=result['created_at']
                )
            return None
            
        except Exception as e:
            print(f"Error finding user: {e}")
            return None
        finally:
            try:
                cursor.close()
                connection.close()
            except Exception:
                pass
    
    @staticmethod
    def authenticate(username, password):
        """Authenticate user with username and password"""
        user = User.find_by_username(username)
        if user and User.verify_password(password, user.password_hash):
            return user
        return None
