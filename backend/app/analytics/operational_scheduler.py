"""Single APScheduler owner per PostgreSQL deployment; registration never runs backlog."""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from app.services.operational_attention_service import OperationalAttentionService

OWNER_LOCK = 261860003


def completed_day_run(service):
    return service.run(datetime.now(timezone.utc).date(),mode="SCHEDULED")


class OperationalScheduler:
    def __init__(self, engine, service=None):
        self.engine=engine
        self.service=service or OperationalAttentionService(engine)
        self.owner=None
        self.scheduler=BackgroundScheduler(timezone="UTC")

    def start(self):
        try:
            self.owner=self.engine.connect()
            owned=self.owner.execute(text("SELECT pg_try_advisory_lock(:key)"),{"key":OWNER_LOCK}).scalar_one()
            self.owner.commit()
            if not owned:
                self.owner.close()
                self.owner=None
                return False
            self.scheduler.add_job(completed_day_run,"cron",hour=0,minute=15,timezone="UTC",
                                   args=[self.service],id="operational_completed_day",max_instances=1,
                                   coalesce=True,misfire_grace_time=60,replace_existing=True)
            self.scheduler.start()
            return True
        except Exception:
            logging.getLogger("prahari").warning("Operational scheduler unavailable")
            self.stop()
            return False

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
        if self.owner is not None:
            try:
                self.owner.execute(text("SELECT pg_advisory_unlock(:key)"),{"key":OWNER_LOCK})
                self.owner.commit()
            finally:
                self.owner.close()
                self.owner=None
