from sqlalchemy import select

from db.models import Entry
from db.session import Session

def main():
    with Session() as session:
        result = session.execute(select(Entry).where(Entry.title.contains("Fuzzing")))
        print(result.scalars().all())

if __name__ == "__main__":
    main()  