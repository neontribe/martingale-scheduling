import copy
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from ortools.sat.python import cp_model

from .libs.classes import Space, SubjCandidate
from .libs.utilities import extract_data, create_calendar


@contextmanager
def timed(label: str, logger=print):
    """Context manager to time and log code blocks."""
    t0 = time.time()
    try:
        yield
    finally:
        logger(f"{label} in {time.time() - t0:.2f} seconds")


def resolve_base_path() -> Path:
    """Handle PyInstaller frozen vs normal script path."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS).parents[4]
    return Path(__file__).parents[2]


def resolve_paths(base: Path, *rels: str) -> list[Path]:
    """Resolve multiple relative paths against a base directory."""
    return [(base / Path(r)).resolve() for r in rels]


def get_int(prompt: str, input_fn=input, logger=print) -> int:
    """Repeated input-validation pattern."""
    while True:
        try:
            return int(input_fn(prompt))
        except Exception:
            logger("Batch size must be an integer, with no additional characters")


def plan_batches(self, candidates, cand_copy, spaces, batch_size):
    """Split candidates and spaces into groups."""
    cand_groups, cand_r = self.split_into_groups(candidates, batch_size)
    copy_groups, copy_r = self.split_into_groups(cand_copy, batch_size)
    no_batches = len(cand_groups) + 1
    space_size = len(spaces) // no_batches
    space_groups, space_r = self.split_into_groups(spaces, space_size)
    assert no_batches == len(space_groups)
    return cand_groups, copy_groups, cand_r, copy_r, space_groups, space_r, no_batches, space_size


def add_assignment_constraints(model, x, cand_list, space_list):
    """Each candidate to one space, each space to at most one candidate."""
    for c in cand_list:
        model.AddExactlyOne(x[c, s] for s in space_list)
    for s in space_list:
        model.AddAtMostOne(x[c, s] for c in cand_list)


def set_min_cost_objective(model, cost, x, penalties, cand_list, space_list):
    """Standard objective function setup."""
    model.Minimize(
        sum(cost[c, s] * x[c, s] for c in cand_list for s in space_list) + sum(weight * p for (p, weight) in penalties))


def solve_model(model, verbose=True):
    """Standardized solver creation and run."""
    solver = cp_model.CpSolver()
    if verbose:
        solver.parameters.log_search_progress = True
        solver.log_callback = print
    status = solver.Solve(model)
    feasible = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    return solver, feasible


def run_round(i, model, x, cost, penalties, cand_group, copy_group, space_group, logger=print):
    """Handles one optimization round."""
    with timed(f"Round {i} set up", logger):
        all_cand = cand_group + copy_group
        add_assignment_constraints(model, x, all_cand, space_group)
        set_min_cost_objective(model, cost, x, penalties, all_cand, space_group)
    logger(f"Now solving round {i}...")
    solver, ok = solve_model(model, verbose=True)
    logger(f"Round {i} {'solution found' if ok else 'no solution'}")
    return solver, ok


def run_final_round(model, x, cost, penalties, cand_list, space_list, logger=print):
    """Handles the final optimization round."""
    with timed("Final set up", logger):
        add_assignment_constraints(model, x, cand_list, space_list)
        set_min_cost_objective(model, cost, x, penalties, cand_list, space_list)
    logger("Now solving final round...")
    return solve_model(model, verbose=True)


def write_calendars(base_path, candidates, cand_copy, spaces, solver, x, cost, pen_dict, cost_msg):
    """Creates calendar output files."""
    output_file_data, output_file_clean = resolve_paths(base_path, "./output/data_interviews.ics",
        "./output/clean_interviews.ics")
    create_calendar(candidates, cand_copy, spaces, solver, x, cost, pen_dict, cost_msg, output_file_data,
        output_file_clean)


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
                        s.int_id != t.int_id))]

                # if connection is disallowed, ensure x bool is false
                self.model.AddBoolAnd([self.x[cand_copy[idx], t].Not() for t in disallowed]).OnlyEnforceIf(self.x[c, s])

                # currently the weights are randomised
                self.cost[(c, s)] = weights[(c.address, s.location)]
                self.cost[(cand_copy[idx], s)] = weights[(cand_copy[idx].address, s.location)]

                # do the courses and availabilities match?
                if (c.subject in s.subjects) and (s.datestr in c.avail):
                    c_special = set(c.specialisms)
                    if ("Masters" in str(c.subject)) and (c_special.intersection(s.specialisms["MMath"]) == set()) and (
                            str(c.specialisms) != "nan"):
                        # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                        copy_special = set(cand_copy[idx].specialisms)
                        for t in spaces:
                            if (s != t) and (copy_special.intersection(t.specialisms["MMath"]) == set()):
                                penalty = self.model.NewBoolVar(f"penalty1_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                self.penalties.append((penalty, 10000))
                                self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000,
                                                              f"Masters specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MMath']}, s2: {t.specialisms['MMath']}"))
                    if ("Phd" in str(c.subject)) and (c_special.intersection(s.specialisms["MPhd"]) == set()) and (
                            str(c.specialisms) != "nan"):
                        # if c assigned to s, then c duplicate must be assigned to something with the same specialism
                        for t in spaces:
                            if (s != t) and (copy_special.intersection(t.specialisms["MPhd"]) == set()):
                                penalty = self.model.NewBoolVar(f"penalty2_{c}_{cand_copy[idx]}_{s}_{t}")
                                # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                self.model.Add(penalty >= self.x[c, s] + self.x[cand_copy[idx], t] - 1)
                                self.penalties.append((penalty, 10000))
                                self.pen_dict[(c, s)].append((cand_copy[idx], t, 10000,
                                                              f"Phd specialism mismatch: c: {c.specialisms}, s1: {s.specialisms['MPhd']}, s2: {t.specialisms['MPhd']}"))
                if s.datestr in c.avail:
                    print(f"{c.name} is available on {s.datestr}")
                if s.datestr not in c.avail:
                    # if the availabilities don't match, want this to be unfavourable
                    self.cost[(c, s)] += 10000
                    self.cost[(cand_copy[idx], s)] += 10000
                    self.cost_msg[(c, s)].append("Avail mismatch")
                    self.cost_msg[(cand_copy[idx], s)].append("Avail mismatch")
                if c.subject not in s.subjects:
                    # if the subjects don't match, want this to be very unfavourable
                    self.cost[(c, s)] += 1000000
                    self.cost[(cand_copy[idx], s)] += 1000000
                    self.cost_msg[(c, s)].append("Subject mismatch")
                    self.cost_msg[(cand_copy[idx], s)].append("Subject mismatch")
            idx += 1

    def gen_matches_alt(self, candidates, cand_copy, spaces, weights):
        # Precompute space lookups to avoid repeated iterations
        space_groups = {}  # key: (location, date, time), value: list of spaces
        for space in spaces:
            key = (space.location, space.date, space.time)
            if key not in space_groups:
                space_groups[key] = []
            space_groups[key].append(space)

        # Precompute subject and availability compatibility
        compatible_pairs = set()
        for i, c in enumerate(candidates):
            for s in spaces:
                if (c.subject in s.subjects) and (s.datestr in c.avail):
                    compatible_pairs.add((i, s))

        # Process each candidate-space pair
        for idx, c in enumerate(candidates):
            cand_copy_candidate = cand_copy[idx]

            for s in spaces:
                # Calculate costs upfront
                base_cost_c = weights.get((c.address, s.location), 0)
                base_cost_copy = weights.get((cand_copy_candidate.address, s.location), 0)

                # Check basic compatibility
                is_compatible = (idx, s) in compatible_pairs

                if not is_compatible:
                    # Apply heavy penalties for incompatible pairs
                    if s.datestr not in c.avail:
                        base_cost_c += 10000
                        base_cost_copy += 10000
                        self.cost_msg[(c, s)].append("Avail mismatch")
                        self.cost_msg[(cand_copy_candidate, s)].append("Avail mismatch")

                    if c.subject not in s.subjects:
                        base_cost_c += 1000000
                        base_cost_copy += 1000000
                        self.cost_msg[(c, s)].append("Subject mismatch")
                        self.cost_msg[(cand_copy_candidate, s)].append("Subject mismatch")

                # Set costs
                self.cost[(c, s)] = base_cost_c
                self.cost[(cand_copy_candidate, s)] = base_cost_copy

                # Handle copy constraints - only for compatible pairs
                if is_compatible:
                    self._add_copy_constraints(c, cand_copy_candidate, s, space_groups, spaces)
                    self._add_specialism_penalties(c, cand_copy_candidate, s, spaces)

    def _add_copy_constraints(self, c, cand_copy_candidate, s, space_groups, spaces):
        """Add constraints ensuring copy candidate is matched to same time/date/location."""
        copy_con = self.model.NewBoolVar("copy_con")
        self.model.Add(copy_con == 1)

        # Find allowed spaces for the copy (same location, date, time, different interviewer)
        key = (s.location, s.date, s.time)
        allowed_spaces = []
        if key in space_groups:
            allowed_spaces = [t for t in space_groups[key] if t.int_id != s.int_id]

        # All other spaces are disallowed
        disallowed = [t for t in spaces if t not in allowed_spaces and t != s]

        if disallowed:
            self.model.AddBoolAnd([self.x[cand_copy_candidate, t].Not() for t in disallowed]).OnlyEnforceIf(
                self.x[c, s])

    def _add_specialism_penalties(self, c, cand_copy_candidate, s, spaces):
        """Add penalties for specialism mismatches - optimized version."""
        c_special = set(c.specialisms) if str(c.specialisms) != "nan" else set()
        copy_special = set(cand_copy_candidate.specialisms) if str(cand_copy_candidate.specialisms) != "nan" else set()

        # Masters specialism check
        if ("Masters" in str(c.subject)) and c_special and (
                c_special.intersection(s.specialisms.get("MMath", set())) == set()):
            self._add_specialism_penalty_batch(c, cand_copy_candidate, s, spaces, copy_special, "MMath", "Masters", 1)

        # PhD specialism check
        if ("PhD" in str(c.subject)) and c_special and (
                c_special.intersection(s.specialisms.get("MPhd", set())) == set()):
            self._add_specialism_penalty_batch(c, cand_copy_candidate, s, spaces, copy_special, "MPhd", "Phd", 2)

    def _add_specialism_penalty_batch(self, c, cand_copy_candidate, s, spaces, copy_special, spec_key, degree_type,
                                      penalty_id):
        """Batch process specialism penalties to reduce constraint creation."""
        # Find all spaces where copy candidate would violate specialism requirements
        violating_spaces = []
        for t in spaces:
            if (s != t) and copy_special and (copy_special.intersection(t.specialisms.get(spec_key, set())) == set()):
                violating_spaces.append(t)

        # Create a single penalty variable for this batch
        if violating_spaces:
            penalty = self.model.NewBoolVar(f"penalty{penalty_id}_{id(c)}_{id(cand_copy_candidate)}_{id(s)}")

            # Penalty is triggered if c is assigned to s AND copy is assigned to any violating space
            penalty_sum = [self.x[cand_copy_candidate, t] for t in violating_spaces]
            if penalty_sum:
                self.model.Add(penalty >= self.x[c, s] + sum(penalty_sum) - len(penalty_sum))
                self.penalties.append((penalty, 10000))

                # Add to penalty dictionary for debugging
                for t in violating_spaces:
                    self.pen_dict[(c, s)].append((cand_copy_candidate, t, 10000,
                                                  f"{degree_type} specialism mismatch: c: {c.specialisms}, s1: {s.specialisms.get(spec_key, set())}, s2: {t.specialisms.get(spec_key, set())}"))

    @staticmethod
    def gen_weights(df):
        """Creates a dictionary of weights between cities
        Currently generates this randomly"""

        weights = {}

        # Iterate through the DataFrame
        for termtime_city in df.index:
            for interview_location in df.columns:
                weight_value = df.loc[termtime_city, interview_location]
                # Convert to integer and store with tuple key
                weights[(termtime_city, interview_location)] = int(weight_value)

        return weights

    def date_constraints(self, candidates, spaces):
        """Ensures impossible assignments of interviewees being double booked
        or assigned to different locations of consecutive days"""
        for c1 in candidates:
            for c2 in candidates:
                if (c1.cand_id == c2.cand_id) and (c1 != c2):
                    for s1 in spaces:
                        for s2 in spaces:
                            # disallow: double-booked or same day different location
                            if (s1 != s2) and ((s2.date == s1.date and s1.time == s2.time) or (
                                    s2.date == s1.date and s2.location != s1.location)):
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
                                if (s2.date == s1.date and s2.time == s1.time) or (
                                        s2.date == s1.date and s2.location != s1.location):
                                    penalty = self.model.NewBoolVar(f"penalty4_{c1}_{c2}_{s1}_{s2}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                    self.penalties.append((penalty, 1000000))
                                    self.pen_dict[(c1, s1)].append(
                                        (c2, s2, 1000000, "Double-booked or same day/diff loc"))
                                    self.pen_dict[(c2, s2)].append(
                                        (c1, s1, 1000000, "Double-booked or same day/diff loc"))

                                # undesirable: consecutive days, different locations
                                elif abs((s1.date - s2.date).days) == 1 and s1.location != s2.location:
                                    penalty = self.model.NewBoolVar(f"penalty4b_{c1}_{c2}_{s1}_{s2}")
                                    # trigger penalty if both x[c1,s1] and x[c2,s2] are true
                                    self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
                                    self.penalties.append((penalty, 10000))
                                    self.pen_dict[(c1, s1)].append((c2, s2, 10000, "Consec days, diff loc"))
                                    self.pen_dict[(c2, s2)].append((c1, s1, 10000, "Consec days, diff loc"))

    def date_constraints_alt(self, candidates, spaces):
        """Optimized version with precomputed lookups and reduced constraint creation."""

        # Group candidates by id for quick lookup
        candidates_by_id = {}
        for candidate in candidates:
            if candidate.cand_id not in candidates_by_id:
                candidates_by_id[candidate.cand_id] = []
            candidates_by_id[candidate.cand_id].append(candidate)

        # Group spaces by various criteria for efficient lookups
        spaces_by_date_time = {}  # (date, time) -> [spaces]
        spaces_by_date_location = {}  # (date, location) -> [spaces]
        spaces_by_interviewer = {}  # interviewer -> [spaces]
        consecutive_date_pairs = {}  # date -> [dates that are consecutive]

        # Build lookup structures
        unique_dates = set()
        for space in spaces:  # for every space, create 3 lookup structures
            # Date-time grouping
            dt_key = (space.date, space.time)
            if dt_key not in spaces_by_date_time:
                spaces_by_date_time[dt_key] = []
            spaces_by_date_time[dt_key].append(space)

            # Date-location grouping
            dl_key = (space.date, space.location)
            if dl_key not in spaces_by_date_location:
                spaces_by_date_location[dl_key] = []
            spaces_by_date_location[dl_key].append(space)

            # Interviewer grouping
            if space.int_id not in spaces_by_interviewer:
                spaces_by_interviewer[space.int_id] = []
            spaces_by_interviewer[space.int_id].append(space)

            unique_dates.add(space.date)  # set add only adds it if not already in set

        # Build consecutive date lookup
        for date in unique_dates:
            consecutive_date_pairs[date] = []
            for other_date in unique_dates:
                if abs((date - other_date).days) == 1:
                    consecutive_date_pairs[date].append(other_date)

        # Process candidate constraints (same person, different instances)
        self._add_candidate_constraints(candidates_by_id, spaces_by_date_time, spaces_by_date_location,
                                        consecutive_date_pairs, spaces)

        # Process interviewer constraints (same interviewer, different spaces)
        self._add_interviewer_constraints(candidates, spaces_by_interviewer, spaces_by_date_time,
                                          consecutive_date_pairs)

    def _add_candidate_constraints(self, candidates_by_id, spaces_by_date_time, spaces_by_date_location,
                                   consecutive_date_pairs, spaces):
        """Add constraints for candidates with the same id (same person)."""

        for id, id_candidates in candidates_by_id.items():
            if len(id_candidates) <= 1:
                continue  # Skip if only one candidate object with this id

            # For each pair of candidates with the same id
            for i, c1 in enumerate(id_candidates):
                for c2 in id_candidates[i + 1:]:  # Avoid duplicate pairs
                    self._add_candidate_pair_constraints(c1, c2, spaces_by_date_time, spaces_by_date_location,
                                                         consecutive_date_pairs, spaces)

    def _add_candidate_pair_constraints(self, c1, c2, spaces_by_date_time, spaces_by_date_location,
                                        consecutive_date_pairs, spaces):
        """Add constraints between two candidates with the same id."""

        # Hard constraints: double-booking and same day/different location
        processed_hard_constraints = set()

        # Check each space assigned to c1
        for s1 in spaces:  # Assuming spaces contains all spaces
            # Find conflicting spaces for double-booking (same date-time)
            dt_key = (s1.date, s1.time)
            if dt_key in spaces_by_date_time:
                for s2 in spaces_by_date_time[dt_key]:
                    if s1 != s2:
                        constraint_key = (min(id(s1), id(s2)), max(id(s1), id(s2)), "double_book")
                        if constraint_key not in processed_hard_constraints:
                            processed_hard_constraints.add(constraint_key)
                            self._add_penalty(c1, c2, s1, s2, 1000000, "Double-booked", "penalty3")

            # Find conflicting spaces for same day/different location
            for location_key, location_spaces in spaces_by_date_location.items():
                date, location = location_key
                if date == s1.date and location != s1.location:
                    for s2 in location_spaces:
                        constraint_key = (min(id(s1), id(s2)), max(id(s1), id(s2)), "same_day_diff_loc")
                        if constraint_key not in processed_hard_constraints:
                            processed_hard_constraints.add(constraint_key)
                            self._add_penalty(c1, c2, s1, s2, 500000, "Same day/diff location", "penalty3")

        # Soft constraints: consecutive days, different locations
        processed_soft_constraints = set()

        for s1 in spaces:
            if s1.date in consecutive_date_pairs:
                for consec_date in consecutive_date_pairs[s1.date]:
                    for location_key, location_spaces in spaces_by_date_location.items():
                        date, location = location_key
                        if date == consec_date and location != s1.location:
                            for s2 in location_spaces:
                                constraint_key = (min(id(s1), id(s2)), max(id(s1), id(s2)), "consec_days")
                                if constraint_key not in processed_soft_constraints:
                                    processed_soft_constraints.add(constraint_key)
                                    self._add_penalty(c1, c2, s1, s2, 5000, "Consec days, diff loc", "penalty3b")

    def _add_interviewer_constraints(self, candidates, spaces_by_interviewer, spaces_by_date_time,
                                     consecutive_date_pairs):
        """Add constraints for interviewers (same interviewer can't double-book)."""

        for interviewer, interviewer_spaces in spaces_by_interviewer.items():
            if len(interviewer_spaces) <= 1:
                continue

            # For each pair of spaces with the same interviewer
            for i, s1 in enumerate(interviewer_spaces):
                for s2 in interviewer_spaces[i + 1:]:  # Avoid duplicate pairs
                    self._add_interviewer_pair_constraints(candidates, s1, s2, consecutive_date_pairs)

    def _add_interviewer_pair_constraints(self, candidates, s1, s2, consecutive_date_pairs):
        """Add constraints between spaces with the same interviewer."""

        # Hard constraints: double-booking or same day/different location
        is_hard_violation = (
                (s2.date == s1.date and s2.time == s1.time) or (s2.date == s1.date and s2.location != s1.location))

        # Soft constraints: consecutive days, different locations
        is_soft_violation = (abs((s1.date - s2.date).days) == 1 and s1.location != s2.location)

        if is_hard_violation or is_soft_violation:
            penalty_value = 1000000 if is_hard_violation else 10000
            penalty_msg = ("Double-booked or same day/diff loc" if is_hard_violation else "Consec days, diff loc")
            penalty_prefix = "penalty4" if is_hard_violation else "penalty4b"

            # Create one penalty variable for this space pair that applies to all candidate pairs
            penalty_var = self.model.NewBoolVar(f"{penalty_prefix}_{id(s1)}_{id(s2)}")

            # Sum all possible assignments to these conflicting spaces
            assignment_vars = []
            for c1 in candidates:
                for c2 in candidates:
                    if c1 != c2:
                        assignment_vars.extend([self.x[c1, s1], self.x[c2, s2]])

            # Penalty is triggered if any two different candidates are assigned to conflicting spaces
            if len(assignment_vars) >= 2:
                self.model.Add(penalty_var >= sum(assignment_vars) - len(assignment_vars) + 1)
                self.penalties.append((penalty_var, penalty_value))

                # Add to penalty dictionary for debugging (sample entries to avoid explosion)
                sample_candidates = candidates[:min(5, len(candidates))]  # Limit for performance
                for c1 in sample_candidates:
                    for c2 in sample_candidates:
                        if c1 != c2:
                            self.pen_dict[(c1, s1)].append((c2, s2, penalty_value, penalty_msg))
                            self.pen_dict[(c2, s2)].append((c1, s1, penalty_value, penalty_msg))

    def _add_penalty(self, c1, c2, s1, s2, penalty_value, message, penalty_prefix):
        """Helper method to add penalty constraints."""
        penalty = self.model.NewBoolVar(f"{penalty_prefix}_{id(c1)}_{id(c2)}_{id(s1)}_{id(s2)}")
        self.model.Add(penalty >= self.x[c1, s1] + self.x[c2, s2] - 1)
        self.penalties.append((penalty, penalty_value))
        self.pen_dict[(c1, s1)].append((c2, s2, penalty_value, message))
        self.pen_dict[(c2, s2)].append((c1, s1, penalty_value, message))

    def setup_decision_variables(self, candidates, cand_copy, spaces):
        for c in candidates + cand_copy:
            for s in spaces:
                self.x[c, s] = self.model.NewBoolVar(f'x[{c}][{s}]')

    @staticmethod
    def split_into_groups(lst, size):
        groups = [lst[i:i + size] for i in range(0, len(lst) - len(lst) % size, size)]
        remainder = lst[len(groups) * 20:]
        return groups, remainder

    def run(self, logger=print, input_fn=input):
        logger("Please be patient, this may take a few minutes")

        base_path = resolve_base_path()

        # ---- Data Extraction ----
        abs_cand_path, abs_ac_path, abs_loc_path = resolve_paths(base_path, "./data/scholarship_candidates.xlsx",
            "./data/academic_assessors.xlsx", "./data/Locations.xlsx")

        with timed("Data extraction"):
            candidate_df, academic_df, location_df = extract_data(abs_cand_path, abs_ac_path, abs_loc_path)

        # ---- Object Generation ----
        with timed("Generating data objects"):
            spaces = Space.gen_spaces(academic_df)
            candidates = SubjCandidate.gen_cand(candidate_df)
            weights = self.gen_weights(location_df)
            cand_copy = copy.deepcopy(candidates)

        logger(f"No. Interviews: {len(candidates)}")
        logger(f"No. Spaces: {len(spaces)}")

        if len(spaces) < len(candidates):
            logger("There are more candidates than spaces")
            exit()

        # ---- Model Setup ----
        with timed("Setting up decision variables"):
            self.setup_decision_variables(candidates, cand_copy, spaces)

        with timed("Generating matches"):
            self.gen_matches_alt(candidates, cand_copy, spaces, weights)

        with timed("Generating constraints"):
            self.date_constraints_alt(candidates, spaces)

        batch_size = get_int("Please enter desired batch size", input_fn, logger)

        cand_groups, copy_groups, cand_r, copy_r, space_groups, space_r, no_batches, space_size = plan_batches(self,
            candidates, cand_copy, spaces, batch_size)

        logger(f"No batches {no_batches}, no of space groups {len(space_groups)}, "
               f"space_size {space_size}, no spaces total {len(spaces)}, "
               f"no candidates total {len(candidates)}, no candidate groups {len(cand_groups)}")

        # ---- Round Processing ----
        round_status_list = []
        for i, (cg, kg, sg) in enumerate(zip(cand_groups, copy_groups, space_groups)):
            _, ok = run_round(i, self.model, self.x, self.cost, self.penalties, cg, kg, sg, logger)
            round_status_list.append(ok)

        # ---- Final Round ----
        all_cand_r = cand_r + copy_r
        last_spaces = space_r + space_groups[-1]
        solver, ok = run_final_round(self.model, self.x, self.cost, self.penalties, all_cand_r, last_spaces, logger)
        round_status_list.append(ok)

        logger("Final round solution found" if ok else "Final round solution not found")

        # ---- Calendar Output ----
        logger("Generating calendar...")
        write_calendars(base_path, candidates, cand_copy, spaces, solver, self.x, self.cost, self.pen_dict,
                        self.cost_msg)
        time.sleep(10)
