from dataclasses import dataclass, field
from db.models import Entry, Block, Tag, Machine
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# search_entries
@dataclass
class EntryResult:
    id: int
    title: str
    phase: str
    os: str | None

# search_entry_by_id
@dataclass
class ItemDetail:
    id: int
    position: int
    kind: str
    content: str
    language: str | None

@dataclass
class BlockDetail:
    id: int
    position: int
    title: str
    items: list[ItemDetail]
    children: list["BlockDetail"] = field(default_factory=list)

@dataclass
class TagDetail:
    id: int
    name: str
    
@dataclass
class MachineDetail:
    id: int
    name: str
    os: str | None
    
@dataclass
class EntryDetail:
    id: int
    title: str
    description: str | None
    phase: str
    os: str | None
    notes: str | None
    blocks: list[BlockDetail]
    tags: list[TagDetail]
    machines: list[MachineDetail]
    
@dataclass
class Filters:
    terms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    os: str | None = None
    machine: str | None = None
    phase: str | None = None

def search_entries(session, filters: Filters) -> list[EntryResult]:
    
    conditions = []
    
    for term in filters.terms:
        conditions.append(Entry.title.contains(term, autoescape=True) | Entry.description.contains(term, autoescape=True))
    
    for tag in filters.tags:
        conditions.append(Entry.tags.any(Tag.name.contains(tag, autoescape=True)))
    
    if filters.os is not None:
        conditions.append(Entry.os == filters.os)
        
    if filters.machine is not None:
        conditions.append(Entry.machines.any(Machine.name.contains(filters.machine, autoescape=True)))
    
    if filters.phase is not None:
        conditions.append(Entry.phase == filters.phase)
    
    rows = session.execute(
        select(Entry.id, Entry.title, Entry.phase, Entry.os)
        .where(*conditions)
    ).all()
    
    results = [
        EntryResult(id=row.id, title=row.title, phase=row.phase, os=row.os)
        for row in rows
    ]
    return results

def _build_block_tree(blocks: list[Block]) -> list[BlockDetail]:
    # Entry.blocks and Block.items are already ordered by position by the ORM.
    details = {
        block.id: BlockDetail(
            id=block.id,
            position=block.position,
            title=block.title,
            items=[
                ItemDetail(
                    id=item.id,
                    position=item.position,
                    kind=item.kind,
                    content=item.content,
                    language=item.language,
                )
                for item in block.items
            ],
        )
        for block in blocks
    }

    roots = []
    for block in blocks:
        detail = details[block.id]
        if block.parent_id is None:
            roots.append(detail)
        else:
            details[block.parent_id].children.append(detail)
    return roots


def search_entry_by_id(session, id: int) -> EntryDetail | None:
    entry = session.scalars(
        select(Entry)
        .where(Entry.id == id)
        .options(
            selectinload(Entry.blocks).selectinload(Block.items),
            selectinload(Entry.tags),
            selectinload(Entry.machines)
        )
    ).one_or_none()
    
    if entry is None:
        return None

    return EntryDetail(
        id=entry.id,
        title=entry.title,
        description=entry.description,
        phase=entry.phase,
        os=entry.os,
        notes=entry.notes,
        blocks=_build_block_tree(entry.blocks),
        tags=[TagDetail(id=tag.id, name=tag.name) for tag in entry.tags],
        machines=[
            MachineDetail(id=machine.id, name=machine.name, os=machine.os)
            for machine in entry.machines
        ],
    )
