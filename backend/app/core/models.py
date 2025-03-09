"""
Base models for the application.
"""
from datetime import datetime
from app import db


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamps to models."""
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Profile(db.Model, TimestampMixin):
    """User profile model."""
    __tablename__ = "profiles"
    
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    interests = db.Column(db.ARRAY(db.String), nullable=True)
    conference_experience = db.Column(db.ARRAY(db.String), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relationships
    documents = db.relationship("Document", back_populates="author", lazy="dynamic")
    speeches = db.relationship("Speech", back_populates="author", lazy="dynamic")
    
    def __repr__(self):
        return f"<Profile {self.username}>"


class Document(db.Model, TimestampMixin):
    """Document model for research papers, position papers, etc."""
    __tablename__ = "documents"
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # position_paper, research, notes, etc.
    tags = db.Column(db.ARRAY(db.String), nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    
    # Foreign keys
    author_id = db.Column(db.String(36), db.ForeignKey("profiles.id"), nullable=False)
    committee_id = db.Column(db.String(36), db.ForeignKey("committees.id"), nullable=True)
    
    # Relationships
    author = db.relationship("Profile", back_populates="documents")
    committee = db.relationship("Committee", back_populates="documents")
    
    def __repr__(self):
        return f"<Document {self.title}>"


class Speech(db.Model, TimestampMixin):
    """Speech model for prepared speeches and drafts."""
    __tablename__ = "speeches"
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    speech_type = db.Column(db.String(50), nullable=False)  # opening, closing, moderated_caucus, etc.
    duration_seconds = db.Column(db.Integer, nullable=True)
    tags = db.Column(db.ARRAY(db.String), nullable=True)
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    
    # Foreign keys
    author_id = db.Column(db.String(36), db.ForeignKey("profiles.id"), nullable=False)
    committee_id = db.Column(db.String(36), db.ForeignKey("committees.id"), nullable=True)
    
    # Relationships
    author = db.relationship("Profile", back_populates="speeches")
    committee = db.relationship("Committee", back_populates="speeches")
    
    def __repr__(self):
        return f"<Speech {self.title}>"


class Committee(db.Model, TimestampMixin):
    """Committee model for MUN committees."""
    __tablename__ = "committees"
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    conference_name = db.Column(db.String(255), nullable=False)
    conference_date = db.Column(db.Date, nullable=True)
    
    # Relationships
    documents = db.relationship("Document", back_populates="committee", lazy="dynamic")
    speeches = db.relationship("Speech", back_populates="committee", lazy="dynamic")
    
    def __repr__(self):
        return f"<Committee {self.name} - {self.conference_name}>"


class ResearchQuery(db.Model, TimestampMixin):
    """Model for AI research queries and results."""
    __tablename__ = "research_queries"
    
    id = db.Column(db.String(36), primary_key=True)
    query = db.Column(db.Text, nullable=False)
    result = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, completed, failed
    model_used = db.Column(db.String(50), nullable=True)
    
    # Foreign keys
    user_id = db.Column(db.String(36), db.ForeignKey("profiles.id"), nullable=False)
    committee_id = db.Column(db.String(36), db.ForeignKey("committees.id"), nullable=True)
    
    def __repr__(self):
        return f"<ResearchQuery {self.id}>" 