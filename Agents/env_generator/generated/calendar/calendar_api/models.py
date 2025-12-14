from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    events = relationship('Event', back_populates='creator')
    invitations = relationship('Invitation', back_populates='invitee')

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(String(250))
    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=False)
    creator_id = Column(Integer, ForeignKey('users.id'))
    creator = relationship('User', back_populates='events')
    invitations = relationship('Invitation', back_populates='event')
    reminders = relationship('Reminder', back_populates='event')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'creator_id': self.creator_id
        }

class Invitation(Base):
    __tablename__ = 'invitations'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    invitee_id = Column(Integer, ForeignKey('users.id'))
    accepted = Column(Boolean, default=False)
    event = relationship('Event', back_populates='invitations')
    invitee = relationship('User', back_populates='invitations')

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'invitee_id': self.invitee_id,
            'accepted': self.accepted
        }

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'))
    remind_time = Column(DateTime, nullable=False)
    message = Column(String(250))
    event = relationship('Event', back_populates='reminders')

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'remind_time': self.remind_time.isoformat(),
            'message': self.message
        }

# Engine and session setup for demonstration purposes (Adjust as needed)
engine = create_engine('sqlite:///calendar.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

def create_tables():
    Base.metadata.create_all(engine)

# Call create_tables() to create the tables in the database
if __name__ == '__main__':
    create_tables()