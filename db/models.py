from sqlalchemy import (
    Column, Enum, ForeignKey, ForeignKeyConstraint, Index, Table, Text,
    UniqueConstraint, case,
)
from sqlalchemy.sql.expression import Grouping
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

PHASES = (
    'recon',
    'enumeration',
    'exploitation',
    'pivoting',
    'post_exploitation',
    'privesc',
    'setup',
    'other'
)

OS_TYPES = (
    'linux',
    'windows',
    'multiplatform',
    'other'
)

ITEM_KINDS = ('text', 'command', 'image', 'note')

class Base(DeclarativeBase):
    pass

entry_tag = Table(
    'entry_tag',
    Base.metadata,
    Column('entry_id', ForeignKey('entries.id'), primary_key=True),
    Column('tag_id', ForeignKey('tags.id'), primary_key=True),
)

entry_machine = Table(
    'entry_machine',
    Base.metadata,
    Column('entry_id', ForeignKey('entries.id'), primary_key=True),
    Column('machine_id', ForeignKey('machines.id'), primary_key=True),
)

class Entry(Base):
    __tablename__ = 'entries'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    description: Mapped[str | None] = mapped_column(Text)
    phase: Mapped[str] = mapped_column(Enum(*PHASES, name="phase_enum", create_constraint=True))
    os: Mapped[str | None] = mapped_column(Enum(*OS_TYPES, name="os_enum", create_constraint=True))
    notes: Mapped[str | None] = mapped_column(Text)

    blocks: Mapped[list["Block"]] = relationship(back_populates="entry", cascade="all, delete-orphan", order_by="Block.position")
    tags: Mapped[list["Tag"]] = relationship(secondary=entry_tag, back_populates="entries")
    machines: Mapped[list["Machine"]] = relationship(secondary=entry_machine, back_populates="entries")

class Block(Base):
    __tablename__ = 'blocks'

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey('entries.id', ondelete='CASCADE'))
    parent_id: Mapped[int | None] = mapped_column()
    position: Mapped[int]
    title: Mapped[str]

    __table_args__ = (
        UniqueConstraint('entry_id', 'id'),
        ForeignKeyConstraint(
            ['entry_id', 'parent_id'], ['blocks.entry_id', 'blocks.id'], ondelete='CASCADE'
        ),
        UniqueConstraint('parent_id', 'position'),
        # Only roots contribute an entry id; all children yield NULL in this index.
        Index('uq_blocks_root_position',
              Grouping(case((parent_id.is_(None), entry_id))), 'position', unique=True),
    )

    entry: Mapped["Entry"] = relationship(back_populates="blocks")
    parent: Mapped["Block | None"] = relationship(
        back_populates="children", foreign_keys=[parent_id], remote_side=[id]
    )
    children: Mapped[list["Block"]] = relationship(
        back_populates="parent", foreign_keys=[parent_id], order_by="Block.position",
        cascade="save-update, merge, delete", passive_deletes=True,
    )
    items: Mapped[list["Item"]] = relationship(
        back_populates="block", cascade="all, delete-orphan", order_by="Item.position"
    )

class Item(Base):
    __tablename__ = 'items'
    __table_args__ = (UniqueConstraint('block_id', 'position'),)

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey('blocks.id', ondelete='CASCADE'))
    position: Mapped[int]
    kind: Mapped[str] = mapped_column(Enum(*ITEM_KINDS, name="item_kind", create_constraint=True))
    content: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None]

    block: Mapped["Block"] = relationship(back_populates="items")

class Tag(Base):
    __tablename__='tags'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    entries: Mapped[list["Entry"]] = relationship(secondary=entry_tag, back_populates="tags")

class Machine(Base):
    __tablename__='machines'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    os: Mapped[str | None] = mapped_column(Enum(*OS_TYPES, name="os_enum", create_constraint=True))

    entries: Mapped[list["Entry"]] = relationship(secondary=entry_machine, back_populates="machines")
