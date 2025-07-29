from src.scheduler.libs.utilities import parse_schedule
from src.scheduler.libs.classes import Space
import pandas as pd
from datetime import datetime
from pathlib import Path

def test_parse_schedule_valid():
    input_str = "Monday 3 November (London); Tuesday 4 November (Manchester)"
    expected_dates = ["Monday 3 November", "Tuesday 4 November"]
    expected_locations = ["London", "Manchester"]

    dates, locations = parse_schedule(input_str)
    assert dates == expected_dates
    assert locations == expected_locations

def test_parse_schedule_invalid_format():
    input_str = "Monday 3 November London; Tuesday 4 November Manchester"
    
    dates, locations = parse_schedule(input_str)

    # Since there are no parentheses, the lists should be empty
    assert dates == []
    assert locations == []

def test_gen_spaces_single_interviewer():
    data = {
        "Interviewer1": [
            "Dr. Marcus Reed",              # interviewer name
            "",                             # ignored
            "Monday 3 November (London)",   # availability
            "Maths Masters",                        # subjects
            "Algebra; Geometry",            # MMath specialisms
            "nan",                     # MPhd specialisms
        ]
    }

    test_dir = Path(__file__).parent
    file_path = test_dir / "data" / "gen_spaces_test.xlsx"
    df = pd.read_excel(file_path)

    spaces = Space.gen_spaces(df)

    assert len(spaces) == 2  # 1 day = morning + afternoon = 2 spaces

    space = spaces[0]

    assert space.date == datetime(1900, 11, 3, 0, 0)
    assert space.datestr == "Monday 3 November"
    assert space.time in ["morning", "afternoon"]
    assert space.location == "London"
    print("Actual specialisms:", space.specialisms)
    assert space.specialisms == {"MMath": {"Algebra", "Geometry"}, "MPhd": {"nan"}}
    assert space.subjects == "Maths Masters"
    assert space.interviewer == "Dr. Marcus Reed"

