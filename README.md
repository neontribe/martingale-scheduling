# Martingale Scheduling

Event scheduling tool for Martingale's specific needs.

## Features

- **Optimized matching** of candidates to academic interviewers  
- Leverages **Google OR‑Tools** to solve a constraint‑optimization model  
- Generates an **iCalendar** (`.ics`) file with scheduled interviews  

## Requirements

- Python 3.7 or higher  
- [OR‑Tools](https://developers.google.com/optimization)  
- Other dependencies (installed automatically):  
  - `typer`  
  - `pydantic` / `pydantic-settings`  
  - `PyYAML`  
  - `openpyxl`  
  - `pandas`  
  - `icalendar`  

## Installation

Clone the repo (develop branch):

```bash
git clone --branch develop https://github.com/neontribe/martingale-scheduling.git
cd martingale-scheduling
```

## Install

```
pip install .
```

## Develop

```bash
pip install -e .
```

## Usage

### Preparing Your Data

Put your Excel data files into a directory (default data/), with these exact filenames:

- `20_applicants.xlsx` – candidate data
- `Scholarship_Assessor_Data.xlsx` – academic (interviewer) data

You can also override the data path at runtime (see below).

### Running

Run with the default "data/" directory:

```bash
scheduler
```

Or specify a custom data directory:

```bash
scheduler run --data-dir path/to/your/data
```
The tool will:

- Read the Excel files
- Build and solve the scheduling model
- Write out an iCalendar file at output/interviews.ics

## Project structure

```
.
├── config.yaml               # YAML overrides for settings
├── data/                     # Place your Excel data files here
├── output/                   # .ics file will be written here
├── pyproject.toml
├── requirements.txt
├── setup.cfg                 # entry_points: scheduler = scheduler.cli:app
└── src/
    └── scheduler/
        ├── cli.py            # Typer-based CLI
        ├── core.py           # Invokes prototype Scheduler
        ├── prototype.py      # OR-Tools model & scheduling logic
        └── libs/
            ├── classes.py    # Data classes for Spaces & Candidates
            └── utilities.py  # I/O helpers and calendar generation
```