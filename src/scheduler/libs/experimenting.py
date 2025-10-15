import random

import pandas as pd
from ortools.sat.python import cp_model

from classes import Space, Subj_Candidate

df = pd.read_excel("data/Scholarship_Assessor_Data.xlsx")
df2 = pd.read_excel("data/20_applicants.xlsx")

spaces = Space.gen_spaces(df)
candidates, trash = Subj_Candidate.gen_cand(df2)

# df = pd.read_excel("Scholarship_Assessor_Data.xlsx")
# print(df.iloc[0,0]) #0 Name
# print(df.iloc[1,0]) #1 Email
# print(df.iloc[2,0]) #2 Date
# print(df.iloc[3,0]) #3 Courses
# print(df.iloc[4,0]) #4 MMath specialism
# print(df.iloc[5,0]) #5 MPhD specialism

# df2 = pd.read_excel("Application_Form_Data.xlsx")
# print(df2.iloc[0,0]) #0 Start time
# print(df2.iloc[1,0]) #1 Completion time
# print(df2.iloc[2,0]) #2 Email
# print(df2.iloc[3,0]) #3 Name
# print(df2.iloc[4,0]) #4 Last modified time
# print(df2.iloc[5,0]) #5 Dates
# print(df2.iloc[6,0]) #6 City
# print(df2.iloc[7,0]) #7 Masters subjects
# print(df2.iloc[8,0]) #8 PhD subjects
# print(df2.iloc[9,0]) #9 MMath specialism
# print(df2.iloc[10,0]) #10 MPhd Specialism

model = cp_model.CpModel()

x = {}
for c in candidates:
    for s in spaces:
        x[c, s] = model.NewBoolVar(f'x[{c}][{s}]')

penalties = []

# Each candidate assigned to exactly one space
for c in candidates:
    model.AddAtMostOne(x[c, s] for s in spaces)

for c in candidates:
    assigned = [x[c, s] for s in spaces]
    assigned_var = model.NewBoolVar(f'assigned_{c}')
    model.AddMaxEquality(assigned_var, assigned)
    penalties.append((assigned_var.Not(), 1000))  # encourage being assigned

# Each space assigned to at most one candidate
for s in spaces:
    model.AddAtMostOne(x[c, s] for c in candidates)

# Objective: minimize total cost
model.Minimize(sum(weight * p for (p, weight) in penalties) + sum(
    x[c, s] * random.randint(1, 10) for c in candidates for s in spaces))

for c1 in candidates:
    for c2 in candidates:  # for every candidate combination
        if (c1.name == c2.name) and (c1 != c2):  # for all different candidates with the same name,
            for s1 in spaces:
                for s2 in spaces:
                    # disallow: double-booked or same day different location
                    if (s1 != s2) and ((s2.date == s1.date and s1.time == s2.time)):
                        if (c1, s1) in x and (c2, s2) in x:
                            penalty = model.NewBoolVar(f"penalty1_{c1}_{c2}_{s1}_{s2}")

                            # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                            model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                            penalties.append((penalty, 1000))
                        else:
                            print(f"Missing variable for {c1}, {s1} or {c2}, {s2}")


                    elif (s1 != s2) and (s2.date == s1.date and s2.location != s1.location):
                        # print(f"Different locations, same date {c1.name}/{c2.name} for {s1.date}{s1.time} with {s1.interviewer} and {s2.date}{s2.time} with {s2.interviewer}")

                        penalty = model.NewBoolVar(f"penalty1_{c1}_{c2}_{s1}_{s2}")

                        # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                        model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                        penalties.append((penalty, 1000))

                    # undesirable: consecutive days, different locations
                    elif ((abs((s1.date - s2.date).days) == 1) and (s1.location != s2.location)):
                        penalty = model.NewBoolVar(f"penalty1_{c1}_{c2}_{s1}_{s2}")

                        # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                        model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                        penalties.append((penalty, 1000))
for s1 in spaces:
    for s2 in spaces:
        if (s1.interviewer == s2.interviewer) and (s1 != s2):
            for c1 in candidates:
                for c2 in candidates:
                    # disallow: double-booked or same day different location
                    if c1 != c2 and ((s2.date == s1.date and s2.time == s1.time) or (
                            s2.date == s1.date and s2.location != s1.location)):
                        penalty = model.NewBoolVar(f"penalty_{c1}_{c2}_{s1}_{s2}")

                        # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                        model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                        penalties.append((penalty, 1000))
                    # undesirable: consecutive days, different locations
                    elif c1 != c2 and ((abs((s1.date - s2.date).days) == 1) and (s1.location != s2.location)):
                        penalty = model.NewBoolVar(f"penalty_{c1}_{c2}_{s1}_{s2}")

                        # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                        model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                        penalties.append((penalty, 1000))
# Solve
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
    # create and store a calendar file
    solver.parameters.max_time_in_seconds = 60.0
    print("solveable!")
else:
    print("No feasible solution found.")
    print("Status:", solver.StatusName())
    print("Conflicts:", solver.NumConflicts())
    print("Branches:", solver.NumBranches())
    print("Wall time:", solver.WallTime())
