from classes import Subj_Candidate, Space
import pandas as pd
from ortools.sat.python import cp_model
import random

df = pd.read_excel("data/Scholarship_Assessor_Data.xlsx")
df2 = pd.read_excel("data/Minimum_Application_Data.xlsx")

spaces = Space.gen_spaces(df)
candidates, trash = Subj_Candidate.gen_cand(df2)

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
model.Minimize(
    sum(weight * p for (p, weight) in penalties) + sum(x[c,s] * random.randint(1,10) for c in candidates for s in spaces)
)

for c1 in candidates:
        for c2 in candidates: #for every candidate combination
            if (c1.name == c2.name) and (c1 != c2): #for all different candidates with the same name, 
                if c1 == c2:
                    print("Uh-oh c1 = c2") #these don't run so are not the problem
                for s1 in spaces:
                    for s2 in spaces:
                        #disallow: double-booked or same day different location
                        if (s1!=s2) and ((s2.date == s1.date and s1.time == s2.time)):
                            if s1 == s2:
                                print("Uh-oh s1 = s2")
                            if (c1, s1) in x and (c2, s2) in x:
                                #print(f"Same date/time {c1.name}/{c2.name} for {s1.date}{s1.time} with {s1.interviewer} and {s2.date}{s2.time} with {s2.interviewer}")
                                # penalty if both c1 and c2 are assigned to conflicting slots
                                penalty = model.NewBoolVar(f"penalty_{c1}_{c2}_{s1}_{s2}")

                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                model.Add(penalty >= x[c1, s1] + x[c2, s2] - 1)

                                penalties.append((penalty, 1000))
                            else:
                                print(f"Missing variable for {c1}, {s1} or {c2}, {s2}")

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