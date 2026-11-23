from django.core.management.base import BaseCommand, CommandError

from apps.audit.services import verify_audit_chain


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--institution-id", dest="institution_id")

    def handle(self, *args, **options):
        institution_id = options.get("institution_id")
        result = verify_audit_chain(institution_id=institution_id)
        if result["valid"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Audit chain valid for {result['institution_id']} ({result['count']} entries)"
                )
            )
            return
        for error in result["errors"]:
            self.stdout.write(self.style.ERROR(str(error)))
        raise CommandError(
            f"Audit chain invalid for {result['institution_id']} ({len(result['errors'])} errors)"
        )
