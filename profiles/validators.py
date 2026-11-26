from django.core.exceptions import ValidationError

MAX_RESUME_SIZE = 5 * 1024 * 1024


def validate_pdf_file(value):
    """Require uploaded resumes to use the PDF extension and MIME type."""
    if not value.name.lower().endswith(".pdf"):
        raise ValidationError("Resume must be a PDF file.")

    content_type = getattr(value, "content_type", None)
    if content_type and content_type != "application/pdf":
        raise ValidationError("Resume must be a PDF file.")


def validate_resume_size(value):
    if value.size > MAX_RESUME_SIZE:
        raise ValidationError(
            f"Resume must be no larger than {MAX_RESUME_SIZE // (1024 * 1024)} MB."
        )
