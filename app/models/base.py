from app import db
from datetime import datetime, timezone

def utc_now():
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)

class BaseModel(db.Model):
    """Base model class with common fields"""
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def save(self):
        """Save the model instance to database"""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Delete the model instance from database"""
        db.session.delete(self)
        db.session.commit()
        return True
