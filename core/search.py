from dataclasses import dataclass, field
from db.models import Entry, Block, Command, Tag, Machine
from sqlalchemy import select, and_
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
class CommandDetail:
    id: int
    position: int | None
    command: str
    note: str | None
    example: str | None

@dataclass
class BlockDetail:
    id: int
    position: int | None
    title: str | None
    description: str | None
    commands: list[CommandDetail]

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
        .where(and_(*conditions))
    ).all()
    
    results = [
        EntryResult(id=row.id, title=row.title, phase=row.phase, os=row.os)
        for row in rows
    ]
    return results

def search_entry_by_id(session, id: int) -> EntryDetail | None:
    entry = session.scalars(
        select(Entry)
        .where(Entry.id == id)
        .options(
            selectinload(Entry.blocks).selectinload(Block.commands),
            selectinload(Entry.tags),
            selectinload(Entry.machines)
        )
    ).one_or_none()
    
    if entry is None:
        return None

    result = EntryDetail(
                id=entry.id, 
                title=entry.title,
                description=entry.description, 
                phase=entry.phase, 
                os=entry.os,
                notes=entry.notes,
                blocks=[
                    BlockDetail(
                        id=block.id,
                        position=block.position,
                        title=block.title,
                        description=block.description,
                        commands=[
                            CommandDetail(
                                id=command.id,
                                position=command.position,
                                command=command.command,
                                note=command.note,
                                example=command.example
                            )
                            for command in block.commands
                        ]
                    )
                    for block in entry.blocks],
                tags=[
                    TagDetail(
                        id=tag.id,
                        name=tag.name
                    )
                    for tag in entry.tags],
                machines=[
                    MachineDetail(
                        id=machine.id,
                        name=machine.name,
                        os=machine.os
                    )
                    for machine in entry.machines]
            )
    
    return result