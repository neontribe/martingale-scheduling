from scheduler.prototype import Scheduler

def do_task(cfg: dict):
    scheduler = Scheduler(cfg=cfg)
    scheduler.run()
    return {"status": "ok"}