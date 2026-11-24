from rest_framework.routers import DefaultRouter

from .api import JournalEntryViewSet, LedgerAccountViewSet

app_name = "accounting"

router = DefaultRouter()
router.register("accounts", LedgerAccountViewSet, basename="ledger-account")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")

urlpatterns = router.urls
