from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(4096), nullable=False)
    status = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    admin_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    deleted = Column(Boolean, nullable=False, default=False)


class TicketsFiles(Base):
    __tablename__ = 'tickets_files'

    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete="CASCADE"), primary_key=True)
    file_uuid = Column(String(36), primary_key=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(4096), nullable=False)
    user_id = Column(Integer, nullable=False)
    admin_id = Column(Integer, nullable=True, default=None)
    ticket_id = Column(Integer, ForeignKey('tickets.id', ondelete="CASCADE"))
    admin_connected = Column(Boolean, nullable=False, default=False)
    admin_disconnected = Column(Boolean, nullable=False, default=False)
    in_progress = Column(Boolean, nullable=False, default=False)
    solved = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    deleted = Column(Boolean, nullable=False, default=False)


class MessagesFiles(Base):
    __tablename__ = 'messages_files'

    message_id = Column(Integer, ForeignKey('messages.id', ondelete="CASCADE"), primary_key=True)
    file_uuid = Column(String(36), primary_key=True, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)