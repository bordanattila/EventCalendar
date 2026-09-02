import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Allow imports whether run from project root or storage/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'storage'))

from db_manager import Event, _default_end_time

DB_PATH = PROJECT_ROOT / 'calendar.db'
engine = create_engine(f'sqlite:///{DB_PATH}', echo=True)
SessionLocal = sessionmaker(bind=engine)

NEW_COLUMNS = {
    'ical_uid': 'VARCHAR(255)',
    'ical_etag': 'VARCHAR(255)',
    'source': 'VARCHAR(255)',
    'sync_status': 'VARCHAR(255)',
    'last_modified': 'VARCHAR(255)',
    'event_end_time': 'VARCHAR(225)',
}


def add_new_columns_to_events_table():
    """Add iCal/sync columns if they do not already exist."""
    inspector = inspect(engine)
    existing = {col['name'] for col in inspector.get_columns('scheduled_event')}

    with SessionLocal() as session:
        for column, column_type in NEW_COLUMNS.items():
            if column in existing:
                print(f'Column {column} already exists, skipping')
                continue
            session.execute(
                text(f'ALTER TABLE scheduled_event ADD COLUMN {column} {column_type}')
            )
            print(f'Added column {column}')
        session.commit()


def backfill_new_columns():
    """Backfill default values for rows missing iCal/sync data."""
    try:
        with SessionLocal() as session:
            events = session.query(Event).filter(Event.ical_uid.is_(None)).all()
            if not events:
                print('No rows need backfilling')
                return

            now = datetime.now().isoformat()
            for event in events:
                session.execute(
                    text(
                        'UPDATE scheduled_event '
                        'SET ical_uid = :ical_uid, source = :source, '
                        'sync_status = :sync_status, last_modified = :last_modified, '
                        'event_end_time = :event_end_time '
                        'WHERE id = :id'
                    ),
                    {
                        'id': event.id,
                        'ical_uid': str(uuid.uuid4()),
                        'source': 'local',
                        'sync_status': 'synced',
                        'last_modified': now,
                        'event_end_time': _default_end_time(event.time),
                    },
                )
            session.commit()
            print(f'Backfilled {len(events)} row(s)')
    except Exception as e:
        print(f'Error backfilling new columns: {e}')
        raise


if __name__ == '__main__':
    print(f'Using database: {DB_PATH}')
    add_new_columns_to_events_table()
    backfill_new_columns()
