import asyncio
import os
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models import Job, RunnerLock, Schedule, Session as RunSession

settings = get_settings()
RUNNER_ID = os.environ.get("RUNNER_ID", str(uuid.uuid4()))


async def acquire_lock(db: Session) -> bool:
    lock = db.get(RunnerLock, 1)
    now = datetime.utcnow()
    if not lock:
        db.add(RunnerLock(lock_id=1, runner_id=RUNNER_ID, heartbeat_at=now))
        db.commit()
        return True
    if (now - lock.heartbeat_at).total_seconds() > settings.runner_heartbeat_seconds:
        lock.runner_id = RUNNER_ID
        lock.heartbeat_at = now
        db.add(lock)
        db.commit()
        return True
    return lock.runner_id == RUNNER_ID


def heartbeat(db: Session) -> None:
    lock = db.get(RunnerLock, 1)
    if lock and lock.runner_id == RUNNER_ID:
        lock.heartbeat_at = datetime.utcnow()
        db.add(lock)
        db.commit()


def eligible_schedules(db: Session):
    now = datetime.utcnow()
    stmt = select(Schedule).where(Schedule.enabled == True, Schedule.start_at <= now)
    return db.exec(stmt).all()


def ensure_session(db: Session, schedule: Schedule) -> None:
    existing = db.exec(
        select(RunSession).where(
            RunSession.schedule_id == schedule.id,
            RunSession.state.in_(["queued", "starting", "running"]),
        )
    ).first()
    if existing:
        return
    job = db.get(Job, schedule.job_id)
    planned_end = None
    if schedule.duration_s:
        planned_end = schedule.start_at + timedelta(seconds=schedule.duration_s)
    elif schedule.end_at:
        planned_end = schedule.end_at
    session = RunSession(
        job_id=job.id,
        schedule_id=schedule.id,
        trigger="schedule",
        planned_start_at=schedule.start_at,
        planned_end_at=planned_end,
        state="queued",
    )
    db.add(session)
    db.commit()


async def main():
    while True:
        with Session(engine) as db:
            if not await acquire_lock(db):
                await asyncio.sleep(5)
                continue
            heartbeat(db)
            for sched in eligible_schedules(db):
                ensure_session(db, sched)
        await asyncio.sleep(settings.runner_heartbeat_seconds)


if __name__ == "__main__":
    asyncio.run(main())
