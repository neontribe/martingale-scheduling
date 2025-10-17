from .prototype import Scheduler

def do_task(cfg: dict):
    data_dir = cfg["general"]["data_dir"]
    output_dir = cfg["general"]["output_dir"]
    print(f"Running from {data_dir} outputting to {output_dir}")
    scheduler = Scheduler(cfg=cfg)
    scheduler.run()

    return {"status": "ok"}