from django.db import IntegrityError, transaction

from .models import Application, ApplicationStatusHistory

STATUS_TRANSITIONS = {
    Application.Status.APPLIED: {
        Application.Status.SHORTLISTED,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.SHORTLISTED: {
        Application.Status.INTERVIEW,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.INTERVIEW: {
        Application.Status.OFFERED,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.OFFERED: {
        Application.Status.HIRED,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.HIRED: set(),
    Application.Status.REJECTED: set(),
    Application.Status.WITHDRAWN: set(),
}


class ApplicationError(ValueError):
    pass


class InvalidStatusTransition(ApplicationError):
    pass


class DuplicateApplication(ApplicationError):
    pass


@transaction.atomic
def create_application(student, job, cover_letter=""):
    if not job.is_active:
        raise ApplicationError("Only active jobs can be applied to.")

    try:
        application = Application.objects.create(
            student=student,
            job=job,
            cover_letter=cover_letter,
            status=Application.Status.APPLIED,
        )
    except IntegrityError as error:
        raise DuplicateApplication("You have already applied to this job.") from error

    ApplicationStatusHistory.objects.create(
        application=application,
        changed_by=student,
        from_status=None,
        to_status=Application.Status.APPLIED,
    )
    return application


@transaction.atomic
def transition_application_status(application, to_status, changed_by):
    allowed_statuses = STATUS_TRANSITIONS[application.status]
    if to_status not in allowed_statuses:
        raise InvalidStatusTransition(
            f"Cannot transition from {application.status} to {to_status}."
        )

    from_status = application.status
    application.status = to_status
    application.save(update_fields=["status", "updated_at"])
    ApplicationStatusHistory.objects.create(
        application=application,
        changed_by=changed_by,
        from_status=from_status,
        to_status=to_status,
    )
    return application
