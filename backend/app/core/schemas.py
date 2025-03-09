"""
Serialization schemas for the models.
"""
from marshmallow import Schema, fields, validate, validates, ValidationError


class ProfileSchema(Schema):
    """Schema for the Profile model."""
    id = fields.String(dump_only=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=50))
    full_name = fields.String(validate=validate.Length(max=100))
    bio = fields.String(validate=validate.Length(max=500))
    avatar_url = fields.String(validate=validate.Length(max=255))
    country = fields.String(validate=validate.Length(max=100))
    interests = fields.List(fields.String())
    conference_experience = fields.List(fields.String())
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    @validates("username")
    def validate_username(self, value):
        """Validate that username contains only allowed characters."""
        if not value.isalnum() and not "_" in value:
            raise ValidationError("Username must contain only alphanumeric characters and underscores.")


class DocumentSchema(Schema):
    """Schema for the Document model."""
    id = fields.String(dump_only=True)
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    content = fields.String(required=True)
    document_type = fields.String(required=True, validate=validate.OneOf([
        "position_paper", "research", "notes", "resolution", "amendment", "other"
    ]))
    tags = fields.List(fields.String())
    is_public = fields.Boolean(default=False)
    author_id = fields.String(required=True)
    committee_id = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    author = fields.Nested(lambda: ProfileSchema(only=("id", "username", "full_name")), dump_only=True)


class SpeechSchema(Schema):
    """Schema for the Speech model."""
    id = fields.String(dump_only=True)
    title = fields.String(required=True, validate=validate.Length(min=1, max=255))
    content = fields.String(required=True)
    speech_type = fields.String(required=True, validate=validate.OneOf([
        "opening", "closing", "moderated_caucus", "unmoderated_caucus", "other"
    ]))
    duration_seconds = fields.Integer(validate=validate.Range(min=0, max=3600))
    tags = fields.List(fields.String())
    is_public = fields.Boolean(default=False)
    author_id = fields.String(required=True)
    committee_id = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Nested fields
    author = fields.Nested(lambda: ProfileSchema(only=("id", "username", "full_name")), dump_only=True)


class CommitteeSchema(Schema):
    """Schema for the Committee model."""
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    topic = fields.String(required=True, validate=validate.Length(min=1, max=255))
    description = fields.String()
    conference_name = fields.String(required=True, validate=validate.Length(min=1, max=255))
    conference_date = fields.Date()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ResearchQuerySchema(Schema):
    """Schema for the ResearchQuery model."""
    id = fields.String(dump_only=True)
    query = fields.String(required=True)
    result = fields.String(dump_only=True)
    status = fields.String(dump_only=True)
    model_used = fields.String(dump_only=True)
    user_id = fields.String(required=True)
    committee_id = fields.String()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


# Pagination schema
class PaginationSchema(Schema):
    """Schema for pagination metadata."""
    page = fields.Integer()
    per_page = fields.Integer()
    total = fields.Integer()
    pages = fields.Integer()


# Response schemas with pagination
class PaginatedResponseSchema(Schema):
    """Base schema for paginated responses."""
    data = fields.List(fields.Dict())
    meta = fields.Nested(PaginationSchema)


class PaginatedProfilesSchema(PaginatedResponseSchema):
    """Schema for paginated profiles response."""
    data = fields.List(fields.Nested(ProfileSchema))


class PaginatedDocumentsSchema(PaginatedResponseSchema):
    """Schema for paginated documents response."""
    data = fields.List(fields.Nested(DocumentSchema))


class PaginatedSpeechesSchema(PaginatedResponseSchema):
    """Schema for paginated speeches response."""
    data = fields.List(fields.Nested(SpeechSchema))


class PaginatedCommitteesSchema(PaginatedResponseSchema):
    """Schema for paginated committees response."""
    data = fields.List(fields.Nested(CommitteeSchema)) 