import copy
import random
from datetime import datetime

from ortools.sat.python import cp_model

from classes import Space, Subj_Candidate
from utilities import extract_data, parse_schedule, create_calendar


def gen_matches(candidates, cand_copy, spaces, weights):
    """Finds suitable matches between candidate objects and spaces by accessing the relevant attributes.
    In order for each slot to have two interviewers, a copy of candidates list is created
    and constraints imposed on that list separately"""

    cost = {}  # this is what will be minimised by the solver
    idx = 0

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
                if s.datestr in c.avail: #do the availabilities match?]

                    if (str(c.specialisms["MMath"]) not in str(s.specialisms["MMath"])) and (str(c.specialisms["MMath"]) != "nan"):
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism 
                        if x[c,s]:
                            copy_special = str(cand_copy[idx].specialisms["MMath"])
                            for t in spaces:
                                if copy_special not in str(t.specialisms["MMath"]):
                                    cost[(cand_copy[idx], t)] += 10000

                    if (str(c.specialisms["MPhd"]) not in str(s.specialisms["MPhd"])) and (str(c.specialisms["MPhd"]) != "nan"):
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism 
                        if x[c,s]:
                            copy_special = str(cand_copy[idx].specialisms["MPhd"])
                            for t in spaces:
                                if copy_special not in str(t.specialisms["MPhd"]):
                                    cost[(cand_copy[idx], t)] += 10000     
                else:
                    cost[(c,s)] += 10000 #if the availabilities don't match, want this to be unfavourable
                    cost[(cand_copy[idx],s)] += 10000
            else:
                cost[(c,s)] += 1000000 #if the subjects don't match, want this to be very unfavourable
                cost[(cand_copy[idx],s)] += 1000000
        idx += 1
    return cost


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


def gen_ME_dates(df):
    """Ensures candidate instances with the same name cannot be assigned to spaces
    on the same/consecutive days in different locations"""
    all_dates = df.iloc[2]
    proper_dates = []
    for s in all_dates:
        dates, locations = parse_schedule(str(s))
        for date in dates:
            date_format = '%A %d %B'
            date_obj = datetime.strptime(date, date_format)
            proper_dates.append(date_obj)

    # sort dates in order to check for dates which are consecutive
    proper_dates.sort()
    # create a dictionary of lists of "mutually exclusive" dates.
    ME_dates = {}
    for i in range(0, len(proper_dates)):
        if i == 0:
            ME_dates[proper_dates[i]] = [proper_dates[i], proper_dates[i]]
        elif i == len(proper_dates) - 1:
            ME_dates[proper_dates[i]] = [proper_dates[i - 1], proper_dates[i]]
        else:
            ME_dates[proper_dates[i]] = [proper_dates[i - 1], proper_dates[i], proper_dates[i + 1]]
    return ME_dates

def date_constraints(candidates, spaces, cost):
    '''Ensures impossible assignments of interviewees being double booked 
    or assigned to different locations of consecutive days'''
    for c1 in candidates:
        for c2 in candidates:
            if (c1.name == c2.name) and (c1 != c2):
                for s1 in spaces:
                    for s2 in spaces:
                        #disallow: double-booked or same day different location
                        if ((s2.date == s1.date and s1.time == s2.time) or (s2.date == s1.date and s2.location != s1.time)):
                            if x[c1,s1]:
                                cost[c2,s2] += 1000000
                        #undesirable: consecutive days, different locations
                        elif ((s2.date.days() + 1 == s1.date.days()) or (s2.date.days - 1 == s1.date.days)) and (s1.location != s2.location):
                            if x[c1,s1]:
                                cost[c2,s2] += 10000
    for s1 in spaces:
        for s2 in spaces:
            if (s1.interviewer == s2.interviewer) and (s1!= s2):
                for c1 in candidates:
                    for c2 in candidates:
                        #disallow: double-booked or same day different location
                        if ((s2.date == s1.date and s2.time == s1.time) or (s2.date == s1.date and s2.location != s1.time)):
                            if x[c1,s1]:
                                cost[c2,s2] += 1000000
                        #undesirable: consecutive days, different locations
                        elif ((s2.date.days() + 1 == s2.date.days()) or (s2.date.days - 1 == s1.date.days)) and (s2.location != s1.location):
                            if x[c1,s1]:
                                cost[c2,s2] += 10000
    return cost
                        

model = cp_model.CpModel()
candidate_df, academic_df = extract_data()
ME_dates = gen_ME_dates(academic_df)
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

cost = gen_matches(candidates, cand_copy, spaces, weights)
cost = date_constraints(candidates, spaces, cost)

all_cand = candidates + cand_copy

# Each candidate assigned to exactly one space
for c in all_cand:
    model.AddExactlyOne(x[c, s] for s in spaces)

# Each space assigned to at most one candidate
for s in spaces:
    model.AddAtMostOne(x[c, s] for c in all_cand)

# Objective: minimize total cost
model.Minimize(
    sum(cost[c, s] * x[c, s] for c in all_cand for s in spaces)
)

# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    # create and store a calendar file
    create_calendar(candidates, cand_copy, spaces, solver, x, cost)
else:
    print("No feasible solution found.")
