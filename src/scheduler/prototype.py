import copy
import random
from datetime import datetime

from ortools.sat.python import cp_model

from .libs.classes import Space, Subj_Candidate
from .libs.utilities import extract_data, parse_schedule, create_calendar


class Scheduler:
    def __init__(self):
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.x = {}
        self.cost = {}
        self.status = None

    def _gen_matches(self, candidates, cand_copy, spaces, weights):
        cost = {}
        idx = 0

        for c in candidates:
            for s in spaces:
                copy_con = self.model.NewBoolVar("copy_con")
                self.model.Add(copy_con == 1)
                disallowed = [t for t in spaces if not (
                    (s.location == t.location) and (s.date == t.date) and (s.time == t.time) and (
                        s.interviewer != t.interviewer))]

                self.model.AddBoolAnd([self.x[cand_copy[idx], t].Not() for t in disallowed]).OnlyEnforceIf(self.x[c, s])

                if c.subject in s.subjects:
                    if s.datestr in c.avail:
                        cost[(c, s)] = weights[(c.address, s.location)]
                        cost[(cand_copy[idx], s)] = weights[(cand_copy[idx].address, s.location)]

                        mmath = str(c.specialisms["MMath"])
                        if mmath != "nan" and mmath not in str(s.specialisms["MMath"]):
                            copy_special = str(cand_copy[idx].specialisms["MMath"])
                            self.model.AddBoolOr([self.x[cand_copy[idx], s] for s in spaces if
                                                  copy_special in str(s.specialisms["MMath"])]).OnlyEnforceIf(self.x[c, s])

                        mphd = str(c.specialisms["MPhd"])
                        if mphd != "nan" and mphd not in str(s.specialisms["MPhd"]):
                            copy_special = str(cand_copy[idx].specialisms["MPhd"])
                            self.model.AddBoolOr([self.x[cand_copy[idx], s] for s in spaces if
                                                  copy_special in str(s.specialisms["MPhd"])]).OnlyEnforceIf(self.x[c, s])
                    else:
                        cost[(c, s)] = 10000
                        cost[(cand_copy[idx], s)] = 10000
                else:
                    cost[(c, s)] = 1000000
                    cost[(cand_copy[idx], s)] = 1000000
            idx += 1

        return cost

    def _gen_weights(self, candidate_df):
        weights = {}
        c_cities = candidate_df.iloc[6]
        s_cities = ["London", "Manchester", "Birmingham"]
        for i in range(0, len(c_cities)):
            for j in range(0, len(s_cities)):
                weights[(c_cities.iloc[i], s_cities[j])] = random.randint(1, 10)
        return weights

    def _gen_ME_dates(self, df):
        all_dates = df.iloc[2]
        proper_dates = []
        for s in all_dates:
            dates, locations = parse_schedule(str(s))
            for date in dates:
                date_format = '%A %d %B'
                date_obj = datetime.strptime(date, date_format)
                proper_dates.append(date_obj)
        proper_dates.sort()
        ME_dates = {}
        for i in range(0, len(proper_dates)):
            if i == 0:
                ME_dates[proper_dates[i]] = [proper_dates[i], proper_dates[i]]
            elif i == len(proper_dates) - 1:
                ME_dates[proper_dates[i]] = [proper_dates[i - 1], proper_dates[i]]
            else:
                ME_dates[proper_dates[i]] = [proper_dates[i - 1], proper_dates[i], proper_dates[i + 1]]
        return ME_dates

    def _gen_constraints(self, candidates, ME_dates, spaces):
        for c1 in candidates:
            for c2 in candidates:
                if (c1.name == c2.name) and (c1 != c2):
                    for s in spaces:
                        self.model.AddBoolAnd([
                            self.x[c2, t].Not() for t in spaces if (
                                (t.date in ME_dates[s.date] and t.location != s.location) or
                                (t.date == s.date and t.time == s.time)
                            )
                        ]).OnlyEnforceIf(self.x[c1, s])

    def run(self):
        candidate_df, academic_df = extract_data()
        ME_dates = self._gen_ME_dates(academic_df)
        spaces = Space.gen_spaces(academic_df)
        candidates, ME_all_cand = Subj_Candidate.gen_cand(candidate_df)
        weights = self._gen_weights(candidate_df)
        cand_copy = copy.deepcopy(candidates)

        # Create variables
        for c in candidates + cand_copy:
            for s in spaces:
                self.x[c, s] = self.model.NewBoolVar(f'x[{c}][{s}]')

        self._gen_constraints(candidates, ME_dates, spaces)
        self.cost = self._gen_matches(candidates, cand_copy, spaces, weights)

        all_cand = candidates + cand_copy

        # One space per candidate
        for c in all_cand:
            self.model.AddExactlyOne(self.x[c, s] for s in spaces)

        # One candidate per space
        for s in spaces:
            self.model.AddAtMostOne(self.x[c, s] for c in all_cand)

        # Minimize total cost
        self.model.Minimize(
            sum(self.cost[c, s] * self.x[c, s] for c in all_cand for s in spaces)
        )

        self.status = self.solver.Solve(self.model)

        if self.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            create_calendar(candidates, cand_copy, spaces, self.solver, self.x, self.cost)
            return "Schedule generated."
        else:
            return "No feasible solution found."
