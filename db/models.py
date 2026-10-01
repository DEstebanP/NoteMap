from sqlalchemy import Column, ForeignKey, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

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
    phase: Mapped[str]
    os: Mapped[str | None]
    notes: Mapped[str | None] = mapped_column(Text)

    blocks: Mapped[list["Block"]] = relationship(back_populates="entry", cascade="all, delete-orphan", order_by="Block.position")
    tags: Mapped[list["Tag"]] = relationship(secondary=entry_tag, back_populates="entries")
    machines: Mapped[list["Machine"]] = relationship(secondary=entry_machine, back_populates="entries")

class Block(Base):
    __tablename__='blocks'

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey('entries.id'))
    position: Mapped[int | None]
    title: Mapped[str | None]
    description: Mapped[str | None] = mapped_column(Text)

    entry: Mapped["Entry"] = relationship(back_populates="blocks")
    commands: Mapped[list["Command"]] = relationship(back_populates="block", cascade="all, delete-orphan", order_by="Command.position")

class Command(Base):
    __tablename__='commands'

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey('blocks.id'))
    position: Mapped[int | None]
    command: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    example: Mapped[str | None] = mapped_column(Text)

    block: Mapped["Block"] = relationship(back_populates="commands")

class Tag(Base):
    __tablename__='tags'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)

    entries: Mapped[list["Entry"]] = relationship(secondary=entry_tag, back_populates="tags")

class Machine(Base):
    __tablename__='machines'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    os: Mapped[str | None]

    entries: Mapped[list["Entry"]] = relationship(secondary=entry_machine, back_populates="machines")
