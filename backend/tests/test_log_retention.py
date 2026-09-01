# Purge automatique de la retention du journal d'audit (audit reco #7)

from datetime import datetime, timedelta

from app.models.log import Log
from app.services.log_retention_service import RETENTION_DAYS, purge_expired_logs


def test_purge_expired_logs_removes_only_entries_older_than_retention(db_session):
    now = datetime.utcnow()

    old_log = Log(action='login', user_id=None, date=now - timedelta(days=RETENTION_DAYS + 1), detail='old')
    recent_log = Log(action='login', user_id=None, date=now - timedelta(days=1), detail='recent')
    boundary_log = Log(action='login', user_id=None, date=now - timedelta(days=RETENTION_DAYS - 1), detail='boundary')

    db_session.add_all([old_log, recent_log, boundary_log])
    db_session.commit()

    deleted = purge_expired_logs(db_session)

    remaining = {log.detail for log in db_session.query(Log).all()}
    assert deleted == 1
    assert remaining == {'recent', 'boundary'}


def test_purge_expired_logs_is_a_noop_when_nothing_expired(db_session):
    db_session.add(Log(action='login', user_id=None, date=datetime.utcnow(), detail='fresh'))
    db_session.commit()

    deleted = purge_expired_logs(db_session)

    assert deleted == 0
    assert db_session.query(Log).count() == 1


def test_purge_expired_logs_respects_custom_retention(db_session):
    db_session.add(Log(action='login', user_id=None, date=datetime.utcnow() - timedelta(days=5), detail='five-days-old'))
    db_session.commit()

    deleted = purge_expired_logs(db_session, retention_days=1)

    assert deleted == 1
    assert db_session.query(Log).count() == 0
