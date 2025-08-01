from src.scheduler.libs.utilities import parse_schedule
from src.scheduler.libs.classes import Space, Subj_Candidate
from src.scheduler.prototype import Scheduler
import pandas as pd
from datetime import datetime
from pathlib import Path
import copy
from collections import defaultdict


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

def test_gen_spaces_many_interviewers():

    test_dir = Path(__file__).parent
    file_path = test_dir / "data" / "Scholarship_Assessor_Data.xlsx"
    df = pd.read_excel(file_path)

    spaces = Space.gen_spaces(df)

    assert len(spaces) > 102  # 1 day = morning + afternoon = 2 spaces

    space = spaces[9]
    for i in range (0,9):
        print(f"Interviewer{spaces[i].interviewer}, {spaces[i].datestr}")

    assert space.date == datetime(1900, 11, 4, 0, 0)
    assert space.datestr == "Tuesday 4 November"
    assert space.time in ["morning", "afternoon"]
    assert space.location == "London"
    print("Actual specialisms:", space.specialisms)
    assert space.specialisms == {"MMath": {"Theoretical Physics"}, "MPhd": {"Mathematical biology"}}
    assert space.subjects == "Maths Masters; Maths PhD"
    assert space.interviewer == "Emily Wright"


def test_gen_candidates():

    test_dir = Path(__file__).parent
    file_path = test_dir / "data" / "Application_Form_Data.xlsx"
    df = pd.read_excel(file_path)

    candidates = Subj_Candidate.gen_cand(df)

    cand = candidates[8]
    
    assert cand.avail == "Tuesday 4 November (London); Monday 10 November (Birmingham); Monday 3 November (London); Thursday 6 November (Manchester)"
    assert cand.name == "Luke Rivera"
    assert cand.address == "Stoke-on-Trent"
    assert cand.specialisms == "nan"
    assert cand.subject == "AI Masters"

def test_disallowed():
    #use 1 candidate test run
    candidates = Subj_Candidate("Test McTest", "Monday 3 November", "Norwich", "Theoretical Physics", "Maths Masters")
    #several variations
    spaces = [Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "Manchester", "Theoretical Physics", "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 4, 0, 0), "Tuesday 4 November", "morning", "Manchester", "Theoretical Physics", "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "afternoon", "Manchester", "Theoretical Physics", "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "London", "Theoretical Physics", "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "Manchester", "Theoretical Physics", "Maths", "Miss. Other")]
    disallowed_dict = {}

    for i in range (0, len(spaces)):
        disallowed = [t for t in spaces if not ((spaces[i].location == t.location) and (spaces[i].date == t.date) and (spaces[i].time == t.time) and (spaces[i].interviewer != t.interviewer))]
        disallowed_dict[i] = len(disallowed)

    assert disallowed_dict[0] == 4
    assert disallowed_dict[1] == 5
    assert disallowed_dict[2] == 5
    assert disallowed_dict[3] == 5
    assert disallowed_dict[4] == 4

def special_match(candidates, cand_copy, spaces):
    idx = 0
    penalties = []
    pen_dict = defaultdict(list)
    for c in candidates:
        for s in spaces:

            c_special = set(c.specialisms)
            if ("Masters" in str(c.subject)) and (c_special.intersection(s.specialisms["MMath"]) == set()) and (str(c.specialisms) != "nan"):
                # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                copy_special = set(cand_copy[idx].specialisms)
                for t in spaces:
                    if (s != t) and (copy_special.intersection(t.specialisms["MMath"]) == set()):
                        pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Masters specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MMath']}, s2: {t.specialisms['MMath']}"))
            if ("Phd" in str(c.subject)) and (c_special.intersection(s.specialisms["MPhd"]) == set()) and (str(c.specialisms) != "nan"):
                # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                for t in spaces:
                    if (s != t) and (copy_special.intersection(t.specialisms["MPhd"]) == set()):
                        pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Phd specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MPhd']}, s2: {t.specialisms['MPhd']}"))
        idx += 1
    return pen_dict

def test_special_match_valid():
    c = [Subj_Candidate("Test McTest", "Monday 3 November", "Norwich", "Theoretical Physics", "Maths Masters")]
    spaces = [Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "Manchester", {"MMath": {"Theoretical Physics", "Statistics"}, "MPhd": "nan"}, "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Tuesday 3 November", "morning", "Manchester", {"MMath": "nan", "MPhd": "nan"}, "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "afternoon", "Manchester", {"MMath": {"Statistics"}, "MPhd": "nan"} , "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "London", {"MMath": {"Statistics", "Algebra"}, "MPhd": "nan"}, "Maths", "Dr. Interviewer"), Space(datetime(1900, 11, 3, 0, 0), "Monday 3 November", "morning", "Manchester", {"MMath": {"Theoretical Physics"}, "MPhd": "nan"}, "Maths", "Miss. Other")]
    cand_copy = copy.deepcopy(c)
    pen_dict = special_match(c, cand_copy, spaces)
    
    assert pen_dict[(c, spaces[1])] == [(cand_copy, spaces[2]), (cand_copy, spaces[3])]
    assert pen_dict[(c, spaces[2])] == [(cand_copy, spaces[1]), (cand_copy, spaces[3])]
    assert pen_dict[(c, spaces[3])] == [(cand_copy, spaces[1]), (cand_copy, spaces[2])]
    