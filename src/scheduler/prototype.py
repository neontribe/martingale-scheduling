import copy
import time
from pathlib import Path
import sys

from ortools.sat.python import cp_model
from collections import defaultdict

from src.scheduler.libs.classes import Space, Subj_Candidate
from src.scheduler.libs.utilities import extract_data, create_calendar

class Scheduler:
    def __init__(self):
        self.model = cp_model.CpModel()
        self.x = {}
        self.penalties = []
        self.cost = {}
        self.pen_dict = defaultdict(list)
        self.cost_msg = defaultdict(list)
        

    def gen_matches(self, candidates, cand_copy, spaces, weights):
        """Finds suitable matches between candidate objects and spaces by accessing the relevant attributes.
        In order for each slot to have two interviewers, a copy of candidates list is created
        and constraints imposed on that list separately"""

        idx = 0
        for c in candidates:
            for s in spaces:
                # for a given space, s, matched to candidate c

                # must enforce that cand and cand_copy have to be matched to a space with the same date, time and location
                # but different interviewer
                copy_con = self.model.NewBoolVar("copy_con")
                # ensures copy_con is true
                self.model.Add(copy_con == 1)
                disallowed = [t for t in spaces if not (
                    (s.location == t.location) and (s.date == t.date) and (s.time == t.time) and (
                        s.interviewer != t.interviewer))]

                # if connection is disallowed, ensure x bool is false
                self.model.AddBoolAnd([self.x[cand_copy[idx], t].Not() for t in disallowed]).OnlyEnforceIf(self.x[c, s])

                # currently the weights are randomised
                self.cost[(c, s)] = weights[(c.address, s.location)]
                self.cost[(cand_copy[idx], s)] = weights[(cand_copy[idx].address, s.location)]

                # do the courses and availabilities match?
                if (c.subject in s.subjects) and (s.datestr in c.avail):
                    c_special = set(c.specialisms)
                    if ("Masters" in str(c.subject)) and (c_special.intersection(s.specialisms["MMath"]) == set()) and (str(c.specialisms) != "nan"):
                        # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                        copy_special = set(cand_copy[idx].specialisms)
                        for t in spaces:
                            if (s != t) and (copy_special.intersection(t.specialisms["MMath"]) == set()):
                                penalty = self.model.NewBoolVar(f"penalty1_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                self.penalties.append((penalty, 10000))
                                self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Masters specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MMath']}, s2: {t.specialisms['MMath']}"))
                    if ("Phd" in str(c.subject)) and (c_special.intersection(s.specialisms["MPhd"]) == set()) and (str(c.specialisms) != "nan"):
                        # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                        for t in spaces:
                            if (s != t) and (copy_special.intersection(t.specialisms["MPhd"]) == set()):
                                penalty = self.model.NewBoolVar(f"penalty2_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                self.penalties.append((penalty, 10000))
                                self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Phd specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MPhd']}, s2: {t.specialisms['MPhd']}"))
                if (s.datestr not in c.avail):
                        # if the availabilities don't match, want this to be unfavourable
                        self.cost[(c, s)] += 10000
                        self.cost[(cand_copy[idx], s)] += 10000
                        self.cost_msg[(c, s)].append("Avail mismatch")
                        self.cost_msg[(cand_copy[idx], s)].append("Avail mismatch")
                if (c.subject not in s.subjects):
                    # if the subjects don't match, want this to be very unfavourable
                    self.cost[(c, s)] += 1000000
                    self.cost[(cand_copy[idx], s)] += 1000000
                    self.cost_msg[(c, s)].append("Subject mismatch")
                    self.cost_msg[(cand_copy[idx], s)].append("Subject mismatch")
            idx += 1

    def gen_weights(self, candidate_df):
        """Creates a dictionary of weights between cities
        Currently generates this randomly"""
        weights = {}
        c_cities = candidate_df.iloc[6]
        s_cities = ["London", "Manchester", "Birmingham"]
        for i in range(0, len(c_cities)):
            for j in range(0, len(s_cities)):
                # at the moment I am just generating random weights
                weights[(c_cities.iloc[i], s_cities[j])] = 5
        return weights


    def date_constraints(self, candidates, spaces):
        '''Ensures impossible assignments of interviewees being double booked
        or assigned to different locations of consecutive days'''
        for c1 in candidates:
            for c2 in candidates:
                if (c1.name == c2.name) and (c1 != c2):
                    for s1 in spaces:
                        for s2 in spaces:
                            # disallow: double-booked or same day different location
                            if (s1 != s2) and ((s2.date == s1.date and s1.time == s2.time) or (s2.date == s1.date and s2.location != s1.location)):
                                penalty = self.model.NewBoolVar(f"penalty3_{c1}_{c2}_{s1}_{s2}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                self.penalties.append((penalty, 1000000))
                                self.pen_dict[(c1, s1)].append((c2, s2, 1000000, "Double-booked or same day/diff loc"))
                                self.pen_dict[(c2, s2)].append((c1, s1, 1000000, "Double-booked or same day/diff loc"))

                            # undesirable: consecutive days, different locations
                            elif (abs((s1.date - s2.date).days) == 1) and (s1.location != s2.location):
                                penalty = self.model.NewBoolVar(f"penalty3b_{c1}_{c2}_{s1}_{s2}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                self.penalties.append((penalty, 10000))
                                self.pen_dict[(c1, s1)].append((c2, s2, 10000, "Consec days, diff loc"))
                                self.pen_dict[(c2, s2)].append((c1, s1, 10000, "Consec days, diff loc"))
        for s1 in spaces:
            for s2 in spaces:
                if (s1.interviewer == s2.interviewer) and (s1 != s2):
                    for c1 in candidates:
                        for c2 in candidates:
                            # disallow: double-booked or same day different location
                            if c1 != c2:
                                if (s2.date == s1.date and s2.time == s1.time) or (s2.date == s1.date and s2.location != s1.location):
                                    penalty = self.model.NewBoolVar(f"penalty4_{c1}_{c2}_{s1}_{s2}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                    self.penalties.append((penalty, 1000000))
                                    self.pen_dict[(c1, s1)].append((c2, s2, 1000000, "Double-booked or same day/diff loc"))
                                    self.pen_dict[(c2, s2)].append((c1, s1, 1000000, "Double-booked or same day/diff loc"))

                                # undesirable: consecutive days, different locations
                                elif abs((s1.date - s2.date).days) == 1 and s1.location != s2.location:
                                    penalty = self.model.NewBoolVar(f"penalty4b_{c1}_{c2}_{s1}_{s2}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                    self.penalties.append((penalty, 10000))
                                    self.pen_dict[(c1, s1)].append((c2, s2, 10000, "Consec days, diff loc"))
                                    self.pen_dict[(c2, s2)].append((c1, s1, 10000, "Consec days, diff loc"))

    def setup_decision_variables(self, candidates, cand_copy, spaces):
        for c in candidates + cand_copy:
            for s in spaces:
                self.x[c, s] = self.model.NewBoolVar(f'x[{c}][{s}]')

    def run(self):
        print("Please be patient, this may take a few minutes")
        start = time.time()
        # If frozen (compiled with PyInstaller), use the executable's path
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS).parents[4]  # or Path(sys.executable).parent
        else:
            base_path = Path(__file__).parents[2]
        rel_cand_path = Path("./data/Minimum_Application_Data.xlsx")
        rel_ac_path = Path("./data/Minimum_Assessor_Data.xlsx")
        abs_cand_path = (base_path / rel_cand_path).resolve()
        abs_ac_path = (base_path / rel_ac_path).resolve()
        candidate_df, academic_df = extract_data(abs_cand_path, abs_ac_path)
        end = time.time()
        print(f"Data has been extracted in {end - start} seconds")

        start = time.time()
        spaces = Space.gen_spaces(academic_df)
        candidates = Subj_Candidate.gen_cand(candidate_df)
        weights = self.gen_weights(candidate_df)
        cand_copy = copy.deepcopy(candidates)
        end = time.time()
        print(f"Data objects have been generated in {end - start} seconds")

        start = time.time()
        self.setup_decision_variables(candidates, cand_copy, spaces)
        self.gen_matches(candidates, cand_copy, spaces, weights)
        self.date_constraints(candidates, spaces)
        end = time.time()
        print(f"Constraints have been generated in {end - start} seconds")

        start = time.time()
        all_cand = candidates + cand_copy

        # Each candidate assigned to exactly one space
        for c in all_cand:
            self.model.AddExactlyOne(self.x[c, s] for s in spaces)

        # Each space assigned to at most one candidate
        for s in spaces:
            self.model.AddAtMostOne(self.x[c, s] for c in all_cand)

        # Objective: minimize total cost
        self.model.Minimize(
            sum(self.cost[c, s] * self.x[c, s] for c in all_cand for s in spaces) +
            sum(weight * p for (p, weight) in self.penalties)
        )
        end = time.time()
        print(f"Final set up completed in {end - start} seconds. Now solving...")

        # Solve
        start = time.time()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 60

        status = solver.Solve(self.model)
        end = time.time()
        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # create and store a calendar file
            print(f"Solution generated in {end - start} seconds. Now generating calendar...")
            output_data_rel_path  = Path("./output/data_interviews.ics")
            output_clean_rel_path = Path("./output/clean_interviews.ics")
            output_file_data = (base_path / output_data_rel_path).resolve()
            output_file_clean = (base_path / output_clean_rel_path).resolve()
            create_calendar(candidates, cand_copy, spaces, solver, self.x, self.cost, self.pen_dict, self.cost_msg, output_file_data, output_file_clean)
        else:
            print("No feasible solution found.")
            print("Status:", solver.StatusName())
            print("Conflicts:", solver.NumConflicts())
            print("Branches:", solver.NumBranches())
            print("Wall time:", solver.WallTime())
