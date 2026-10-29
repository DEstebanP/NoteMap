from db.session import Session
from core.search import search_entries, search_entry_by_id

if __name__ == "__main__":
    with Session() as session:
        result = search_entries(session, "SMB")
        print(result)
        
        entry_result = search_entry_by_id(session, 1)
        print(entry_result)