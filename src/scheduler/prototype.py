import copy
import random

from ortools.sat.python import cp_model
from collections import defaultdict

from .libs.classes import Space, Subj_Candidate
from .libs.utilities import extract_data, create_calendar


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

                # do the courses match?
                if c.subject in s.subjects:
                    # do the availabilities match?
                    if s.datestr in c.avail:
                        if ("Masters" in str(c.subject)) and (str(c.specialisms) not in str(s.specialisms["MMath"])) and (str(c.specialisms) != "nan"):
                            # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                            copy_special = str(cand_copy[idx].specialisms)
                            for t in spaces:
                                if (s != t) and (copy_special not in str(t.specialisms["MMath"])):
                                    penalty = self.model.NewBoolVar(f"penalty1_{c}_{cand_copy[idx]}_{s}_{t}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                    self.penalties.append((penalty, 10000))
                                    self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Masters specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MMath']}, s2: {t.specialisms['MMath']}"))
                        if ("Phd" in str(c.subject)) and (str(c.specialisms) not in str(s.specialisms["MPhd"])) and (str(c.specialisms) != "nan"):
                            # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                            copy_special = str(cand_copy[idx].specialisms)
                            for t in spaces:
                                if (s != t) and (copy_special not in str(t.specialisms["MPhd"])):
                                    penalty = self.model.NewBoolVar(f"penalty2_{c}_{cand_copy[idx]}_{s}_{t}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                    self.penalties.append((penalty, 10000))
                                    self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000, f"Phd specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MPhd']}, s2: {t.specialisms['MPhd']}"))
                    else:
                        # if the availabilities don't match, want this to be unfavourable
                        self.cost[(c, s)] += 10000
                        self.cost[(cand_copy[idx], s)] += 10000
                        self.cost_msg[(c, s)].append("Avail mismatch")
                        self.cost_msg[(cand_copy[idx], s)].append("Avail mismatch")
                else:
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
                weights[(c_cities.iloc[i], s_cities[j])] = random.randint(1, 10)
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
        candidate_df, academic_df = extract_data()
        spaces = Space.gen_spaces(academic_df)
        candidates, _ = Subj_Candidate.gen_cand(candidate_df)
        weights = self.gen_weights(candidate_df)
        cand_copy = copy.deepcopy(candidates)

        self.setup_decision_variables(candidates, cand_copy, spaces)
        self.gen_matches(candidates, cand_copy, spaces, weights)
        self.date_constraints(candidates, spaces)

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

        # Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)
        solver.parameters.max_time_in_seconds = 60.0

        if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            # create and store a calendar file
            create_calendar(candidates, cand_copy, spaces, solver, self.x, self.cost, self.pen_dict, self.cost_msg)
        else:
            print("No feasible solution found.")
            print("Status:", solver.StatusName())
            print("Conflicts:", solver.NumConflicts())
            print("Branches:", solver.NumBranches())
            print("Wall time:", solver.WallTime())
