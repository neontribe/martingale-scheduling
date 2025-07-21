from .prototype import Scheduler

def do_task(data_dir: str, settings):
    print(f"Running on {data_dir} with {settings}")
    scheduler = Scheduler()
    result = scheduler.run()

    return {"status": "ok"}