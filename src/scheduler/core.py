from src.scheduler.prototype import Scheduler

def do_task(data_dir: str):
    print(f"Running on {data_dir}")
    scheduler = Scheduler()
    result = scheduler.run()

    return {"status": "ok"}