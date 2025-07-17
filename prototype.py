from ortools.sat.python import cp_model
import pandas as pd
import random
from datetime import datetime
from utilities import extract_data, parse_schedule, Space, Subj_Candidate
import copy

def gen_spaces(df):
    '''One space refers to one interview slot at a particular time/date/location and with an interviewer.
    Candidates will be allocated a pair of spaces per course, to have 2 interviewers per interview'''
    spaces = []
    date_format = '%A %d %B'
    for col in df: #for every interviewer

        #extracting cells from interviewer column in dataframe
        avail = df[col].iloc[2] 
        subjects = df[col].iloc[3] 
        specialisms = {"MMath": df[col].iloc[4], "MPhd": df[col].iloc[5]}
        interviewer = df[col].iloc[0]
        dates, locations = parse_schedule(avail) #separating out the dates and corresponding locations from availability cell

        for i in range(0, len(dates)): #for every date interviewer is available
            
            #create 2 new spaces (am/pm) for each date in the avail list
            date_obj = datetime.strptime(dates[i], date_format) #create date object for ease of date arithmetic
            morning_space = Space(date_obj, dates[i], "morning", locations[i], specialisms, subjects, interviewer)
            afternoon_space = Space(date_obj, dates[i], "afternoon", locations[i], specialisms, subjects, interviewer)
            spaces.append(morning_space)
            spaces.append(afternoon_space)
            
    return spaces
    
def gen_cand(df):
    '''Instantiates the Subj_Cand class. One of these per interviewee per course they are interviewing for'''
    candidates =[]
    ME_all_cand = [] #this is a 2d list containing lists of candidate objects belonging to the same interviewee 
    # it is used to ensure that one interviewee is not double-booked (or booked on consecutive dates) for different course

    for col in df: #for every interviewee

        #extracting data from interviewee column in dataframe
        name = df[col].iloc[3]
        avail = df[col].iloc[5]
        address = df[col].iloc[6]
        mast_subjects = str(df[col].iloc[7]).split(';')
        phd_subjects = str(df[col].iloc[8]).split(';')
        specialisms = {"MMath": df[col].iloc[9], "MPhd": df[col].iloc[10]}

        ME_cand = [] #list of candidate objects belonging to this interviewee

        for ele in mast_subjects: #for every masters course being interviewed for
            if (ele != "nan") and (name != "Name"):
                course = ele+" Masters"
                subj_cand = Subj_Candidate(name, avail, address, specialisms, course) 
                candidates.append(subj_cand)
                ME_cand.append(subj_cand)

        for ele in phd_subjects: #for every phd course being interviewed for
            if ele != "nan" and (name != "Name"):
                course = ele+" PhD"
                subj_cand = Subj_Candidate(name, avail, address, specialisms, course)
                candidates.append(subj_cand)
                ME_cand.append(subj_cand)

        ME_all_cand.append(ME_cand) #ME_cand elements all belong to same interviewee
    return candidates, ME_all_cand

def gen_matches(candidates, cand_copy, spaces, weights): 
    '''Finds suitable matches between candidate objects and spaces by accessing the relevant attributes.
    In order for each slot to have two interviewers, a copy of candidates list is created 
    and constraints imposed on that list separately'''

    cost ={} #this is what will be minimised by the solver
    idx = 0

    for c in candidates:
        for s in spaces:
            #for a given space, s, matched to candidate c

            #must enforce that cand and cand_copy have to be matched to a space with the same date, time and location
            #but different interviewer
            copy_con = model.NewBoolVar("copy_con")
            disallowed = [t for t in spaces if not((s.location == t.location) and (s.date == t.date) and (s.time == t.time) and (s.interviewer != t.interviewer))]

            #if connection is disallowed, ensure x bool is false
            model.AddBoolAnd([x[cand_copy[idx],t].Not() for t in disallowed]).OnlyEnforceIf(copy_con)
            #only allow x bool to be true for disallowed connections if the constraint is turned off
            model.AddBoolOr([x[cand_copy[idx],t] for t in disallowed]).OnlyEnforceIf(copy_con.Not())

            cost[(c,s)] = 1000000 #if the availabilities don't match, want this to be basically impossible
            cost[(cand_copy[idx],s)] = 1000000
            if s.datestr in c.avail: #do the availabilities match?
                if c.subject in s.subjects: #do the courses match?

                    cost[(c, s)] = weights[(c.address,s.location)] #currently the weights are randomised
                    cost[(cand_copy[idx],s)] = weights[(cand_copy[idx].address, s.location)]

                    if (str(c.specialisms["MMath"]) not in str(s.specialisms["MMath"])) and (str(c.specialisms["MMath"]) != "nan"):
                        #if specialisms don't match, create constraint
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism 
                        special_con = model.NewBoolVar("special_con") #create bool var which describes allowable combinations
                        
                        #copy of c can only be matched to spaces with matching specialism in masters
                        copy_special = str(cand_copy[idx].specialisms["MMath"])
                        s_special = str(s.specialisms["MMath"])

                        #if constraint applies, can be connected to any s with right specialism
                        model.AddBoolOr([x[cand_copy[idx],s] for s in spaces if copy_special in s_special]).OnlyEnforceIf(special_con) #positive constraint
                        #only if constraint doesn't apply, can it be connected to any s without right specialism
                        model.AddBoolAnd([x[cand_copy[idx],s].Not() for s in spaces if copy_special in s_special]).OnlyEnforceIf(special_con.Not()) #negative constraint
                        
                    if (str(c.specialisms["MPhd"]) not in str(s.specialisms["MPhd"])) and (str(c.specialisms["MPhd"]) != "nan"):
                        #if specialisms don't match, create constraint
                        #if c assigned to s, then c duplicate must be assigned to something with the same specialism 
                        special_con = model.NewBoolVar("special_con") #create bool var which describes allowable combinations

                        #copy of c can only be matched to spaces with matching specialism in masters
                        copy_special = str(cand_copy[idx].specialisms["MPhd"])
                        s_special = str(s.specialisms["MPhd"])

                        #if constraint applies, can be connected to any s with right specialism
                        model.AddBoolOr([x[cand_copy[idx],s] for s in spaces if str(cand_copy[idx].specialisms["MPhd"]) in str(s.specialisms["MPhd"])]).OnlyEnforceIf(special_con) #positive constraint
                        #only if constraint doesn't apply can it be connected to an s without right specialism
                        model.AddBoolAnd([x[cand_copy[idx],s].Not() for s in spaces if str(cand_copy[idx].specialisms["MPhd"]) in str(s.specialisms["MPhd"])]).OnlyEnforceIf(special_con.Not()) #negative constraint
        idx += 1
    return cost

def gen_weights(candidate_df):
    '''Creates a dictionary of weights between cities
    Currently generates this randomly'''
    weights = {}
    c_cities = candidate_df.iloc[6]
    s_cities = ["London", "Manchester", "Birmingham"]
    for i in range (0, len(c_cities)):
        for j in range (0, len(s_cities)):
            weights[(c_cities.iloc[i], s_cities[j])] = random.randint(1,10) #at the moment I am just generating random weights
    return weights

def gen_ME_dates(df):
    '''Ensures candidate instances with the same name cannot be assigned to spaces 
    on the same/consecutive days in different locations'''
    all_dates = df.iloc[2]
    proper_dates = []
    for s in all_dates:
        dates, locations = parse_schedule(str(s))
        for date in dates:
            date_format = '%A %d %B'
            date_obj = datetime.strptime(date, date_format)
            proper_dates.append(date_obj)
    
    proper_dates.sort() #sort dates in order to check for dates which are consecutive
    ME_dates = {} #create a dictionary of lists of "mutually exclusive" dates. 
    for i in range(0,len(proper_dates)):
        if i == 0:
            ME_dates[proper_dates[i]] = [proper_dates[i], proper_dates[i]]
        elif i == len(proper_dates)-1:
            ME_dates[proper_dates[i]] = [proper_dates[i-1], proper_dates[i]]
        else:
            ME_dates[proper_dates[i]] = [proper_dates[i-1], proper_dates[i], proper_dates[i+1]]
    return ME_dates

def gen_constraints(ME_all_cand, ME_dates):
    '''Ensures impossible assignments of interviewees being double booked 
    or assigned to different locations of consecutive days'''
    for i in range(0, len(ME_all_cand)):
        ME_cand = ME_all_cand[i]
        for ele in ME_cand:
            date_con = model.NewBoolVar("date_con")
            for s in spaces:
                #if constraint applies, can't match ME candidates to ME dates
                model.AddBoolAnd([x[ele,t].Not() for t in spaces if ((t.date in ME_dates[s.date]) and (t.location != s.location)) or (t.date == s.date and t.time == s.time)]).OnlyEnforceIf(date_con)
                #only if constraint doesn't apply, can we match ME candidates to any of the ME dates
                model.AddBoolOr([x[ele,t] for t in spaces if ((t.date in ME_dates[s.date]) and (t.location != s.location)) or (t.date == s.date and t.time == s.time)]).OnlyEnforceIf(date_con.Not())

model = cp_model.CpModel()
candidate_df , academic_df = extract_data()
ME_dates = gen_ME_dates(academic_df)
spaces = gen_spaces(academic_df)
candidates, ME_all_cand = gen_cand(candidate_df)
weights = gen_weights(candidate_df)

cand_copy = copy.deepcopy(candidates) #maybe needs to be a deep copy
# Decision variables: x[i][j] = 1 if worker i does task j
x = {}
for c in candidates:
    for s in spaces:
        x[c, s] = model.NewBoolVar(f'x[{c}][{s}]')
for c in cand_copy:
    for s in spaces:
        x[c, s] = model.NewBoolVar(f'x[{c}][{s}]')

gen_constraints(ME_all_cand, ME_dates)
cost = gen_matches(candidates, cand_copy, spaces, weights)

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

# Output
if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]: 
    for c in range(0,len(candidates)): #needs to go through candidate copies too
        for s in spaces:
            if solver.Value(x[candidates[c], s]):
                print(f"Interviewer 1 {s.interviewer} on {s.date, s.time} assigned to  {candidates[c].name} for subject {candidates[c].subject}")
            if solver.Value(x[cand_copy[c],s]):
                print(f"Interviewer 2 {s.interviewer} on {s.date, s.time} assigned to  {cand_copy[c].name} for subject {cand_copy[c].subject}")
    print("Total Cost =", solver.ObjectiveValue())
else:
    print("No feasible solution found.")

