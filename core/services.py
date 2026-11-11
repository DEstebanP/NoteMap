from db.session import Session
from db.models import PHASES, OS_TYPES  # re-exported: the interface reads them from core
from core.search import search_entries, search_entry_by_id, EntryResult, EntryDetail, Filters

class SearchService:
    def __init__(self, session_factory=Session):
        self._session_factory = session_factory

    def search(self, filters: Filters) -> list[EntryResult]:
        with self._session_factory() as session:
            return search_entries(session, filters)

    def get(self, entry_id: int) -> EntryDetail | None:
        with self._session_factory() as session:
            return search_entry_by_id(session, entry_id)