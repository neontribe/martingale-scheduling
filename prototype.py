import copy
import random
from datetime import datetime

from ortools.sat.python import cp_model

from classes import Space, Subj_Candidate
from utilities import extract_data, parse_schedule, create_calendar
from collections import defaultdict


def gen_matches(candidates, cand_copy, spaces, weights):
    """Finds suitable matches between candidate objects and spaces by accessing the relevant attributes.
    In order for each slot to have two interviewers, a copy of candidates list is created
    and constraints imposed on that list separately"""

    cost = {}  # this is what will be minimised by the solver
    pen_dict = defaultdict(list)
    cost_msg = defaultdict(list)
    idx = 0
    penalties = []

    for c in candidates:
        for s in spaces:
            # for a given space, s, matched to candidate c

            # must enforce that cand and cand_copy have to be matched to a space with the same date, time and location
            # but different interviewer
            copy_con = model.NewBoolVar("copy_con")
            model.Add(copy_con == 1)  # ensures copy_con is true
            disallowed = [t for t in spaces if not (
                    (s.location == t.location) and (s.date == t.date) and (s.time == t.time) and (
                    s.interviewer != t.interviewer))]

            #if connection is disallowed, ensure x bool is false
            model.AddBoolAnd([x[cand_copy[idx],t].Not() for t in disallowed]).OnlyEnforceIf(x[c,s])

            cost[(c, s)] = weights[(c.address,s.location)] #currently the weights are randomised
            cost[(cand_copy[idx],s)] = weights[(cand_copy[idx].address, s.location)]

            if c.subject in s.subjects: #do the courses match?
                if s.datestr in c.avail: #do the availabilities match?
                    if ("Masters" in str(c.subject)) and (str(c.specialisms) not in str(s.specialisms["MMath"])) and (str(c.specialisms) != "nan"):
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism
                        copy_special = str(cand_copy[idx].specialisms) 
                        for t in spaces:
                            if (s != t) and (copy_special not in str(t.specialisms["MMath"])):
                                penalty = model.NewBoolVar(f"penalty1_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                model.Add(penalty >= x[c, s] + x[cand_copy[idx], t] - 1)
                                penalties.append((penalty, 10000))
                                pen_dict[(c,s)].append((cand_copy[idx], t, 10000, f"Masters specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MMath']}, s2: {t.specialisms['MMath']}"))

                    if ("Phd" in str(c.subject)) and (str(c.specialisms) not in str(s.specialisms["MPhd"])) and (str(c.specialisms) != "nan"):
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism 
                        copy_special = str(cand_copy[idx].specialisms)
                        for t in spaces:
                            if (s != t) and (copy_special not in str(t.specialisms["MPhd"])):
                                penalty = model.NewBoolVar(f"penalty2_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                model.Add(penalty >= x[c, s] + x[cand_copy[idx], t] - 1)
                                penalties.append((penalty, 10000))
                                pen_dict[(c,s)].append((cand_copy[idx], t, 10000, f"Phd specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MPhd']}, s2: {t.specialisms['MPhd']}"))
                else:
                    cost[(c,s)] = cost[(c,s)]+ 10000 #if the availabilities don't match, want this to be unfavourable
                    cost[(cand_copy[idx],s)] = cost[(cand_copy[idx],s)] + 10000
                    cost_msg[(c,s)].append("Avail mismatch")
                    cost_msg[(cand_copy[idx], s)].append("Avail mismatch")
            else:
                cost[(c,s)] = cost[(c,s)]+ 1000000 #if the subjects don't match, want this to be very unfavourable
                cost[(cand_copy[idx],s)] = cost[(cand_copy[idx],s)] + 1000000
                cost_msg[(c,s)].append("Subject mismatch")
                cost_msg[(cand_copy[idx], s)].append("Subject mismatch")
        idx += 1
    return cost, penalties, pen_dict, cost_msg

def gen_weights(candidate_df):
    """Creates a dictionary of weights between cities
    Currently generates this randomly"""
    weights = {}
    c_cities = candidate_df.iloc[6]
    s_cities = ["London", "Manchester", "Birmingham"]
    for i in range (0, len(c_cities)):
        for j in range (0, len(s_cities)):
            weights[(c_cities.iloc[i], s_cities[j])] = random.randint(1,10) #at the moment I am just generating random weights
    
    return weights

def date_constraints(candidates, spaces, cost, penalties, pen_dict):
    '''Ensures impossible assignments of interviewees being double booked 
    or assigned to different locations of consecutive days'''
    for c1 in candidates:
        for c2 in candidates:
            if (c1.name == c2.name) and (c1 != c2):
                for s1 in spaces:
                    for s2 in spaces:
                        #disallow: double-booked or same day different location
                        if (s1!=s2) and ((s2.date == s1.date and s1.time == s2.time) or (s2.date == s1.date and s2.location != s1.location)):
                            penalty = model.NewBoolVar(f"penalty_3{c1}_{c2}_{s1}_{s2}")
                            # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                            model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)
                            penalties.append((penalty, 1000000)) 
                            pen_dict[(c1,s1)].append((c2, s2, 1000000, "Double-booked or same day/diff loc"))
                            pen_dict[(c2,s2)].append((c1, s1, 1000000, "Double-booked or same day/diff loc"))

                        #undesirable: consecutive days, different locations
                        elif ((abs((s1.date - s2.date).days) == 1) and (s1.location != s2.location)):
                            penalty = model.NewBoolVar(f"penalty_3{c1}_{c2}_{s1}_{s2}")
                            # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                            model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)
                            penalties.append((penalty, 10000))
                            pen_dict[(c1,s1)].append((c2, s2, 10000, "Consec days, diff loc"))
                            pen_dict[(c2,s2)].append((c1, s1, 10000, "Consec days, diff loc"))
    for s1 in spaces:
        for s2 in spaces:
            if (s1.interviewer == s2.interviewer) and (s1!= s2):
                for c1 in candidates:
                    for c2 in candidates:
                        #disallow: double-booked or same day different location
                        if c1!=c2 and ((s2.date == s1.date and s2.time == s1.time) or (s2.date == s1.date and s2.location != s1.location)):
                            penalty = model.NewBoolVar(f"penalty4_{c1}_{c2}_{s1}_{s2}")
                            # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                            model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)
                            penalties.append((penalty, 1000000))
                            pen_dict[(c1,s1)].append((c2, s2, 1000000, "Double-booked or same day/diff loc"))
                            pen_dict[(c2,s2)].append((c1, s1, 1000000, "Double-booked or same day/diff loc"))

                        #undesirable: consecutive days, different locations
                        elif c1!=c2 and ((abs((s1.date - s2.date).days) == 1) and (s1.location != s2.location)):
                            penalty = model.NewBoolVar(f"penalty4_{c1}_{c2}_{s1}_{s2}")
                            # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                            model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)
                            penalties.append((penalty, 10000))
                            pen_dict[(c1,s1)].append((c2, s2, 10000, "Consec days, diff loc"))
                            pen_dict[(c2,s2)].append((c1, s1, 10000, "Consec days, diff loc"))
    return cost, penalties, pen_dict
                        

model = cp_model.CpModel()
candidate_df, academic_df = extract_data()
#ME_dates = gen_ME_dates(academic_df)
spaces = Space.gen_spaces(academic_df)
candidates, ME_all_cand = Subj_Candidate.gen_cand(candidate_df)
weights = gen_weights(candidate_df)

# maybe needs to be a deep copy
cand_copy = copy.deepcopy(candidates)

# Decision variables: x[i][j] = 1 if worker i does task j
x = {}
for c in candidates:
    for s in spaces:
        x[c, s] = model.NewBoolVar(f'x[{c}][{s}]')
for c in cand_copy:
    for s in spaces:
        x[c, s] = model.NewBoolVar(f'x[{c}][{s}]')

cost, penalties, pen_dict, cost_msg = gen_matches(candidates, cand_copy, spaces, weights)
cost, penalties, pen_dict = date_constraints(candidates, spaces, cost, penalties, pen_dict)

all_cand = candidates + cand_copy

# Each candidate assigned to exactly one space
for c in all_cand:
    model.AddExactlyOne(x[c, s] for s in spaces)

# Each space assigned to at most one candidate
for s in spaces:
    model.AddAtMostOne(x[c, s] for c in all_cand)

# Objective: minimize total cost
model.Minimize(
    sum(cost[c, s] * x[c, s] for c in all_cand for s in spaces) + sum(weight * p for (p, weight) in penalties)
)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    # create and store a calendar file
    solver.parameters.max_time_in_seconds = 60.0
    create_calendar(candidates, cand_copy, spaces, solver, x, cost, pen_dict, cost_msg)
else:
    print("No feasible solution found.")
    print("Status:", solver.StatusName())
    print("Conflicts:", solver.NumConflicts())
    print("Branches:", solver.NumBranches())
    print("Wall time:", solver.WallTime())




