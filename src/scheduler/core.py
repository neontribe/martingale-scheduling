from src.scheduler.prototype import Scheduler

def do_task(data_dir: str):
    print(f"Running on {data_dir}")
    scheduler = Scheduler()
    scheduler.run()

    return {"status": "ok"}