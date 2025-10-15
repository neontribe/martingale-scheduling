from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from icalendar import Calendar, Event


def extract_data(abs_cand_path, abs_ac_path, abs_loc_path):
    candidate_df = pd.read_excel(abs_cand_path)
    academic_df = pd.read_excel(abs_ac_path)
    location_df = pd.read_excel(abs_loc_path, index_col=0)
    return candidate_df, academic_df, location_df


def parse_schedule(schedule_str):
    items = schedule_str.split(',')  # Changed from ';' to ',' based on your examples
    locations = []
    dates = []
    am_pm = []

    for item in items:
        item = item.strip()
        if '(' in item and ')' in item:
            # Split at the closing parenthesis to separate location from potential AM/PM
            paren_end = item.find(')') + 1
            location_part = item[:paren_end]
            am_pm_part = item[paren_end:].strip()
            
            # Extract date and location from the first part
            date_part = location_part.split('(')[0].strip()
            location = location_part[location_part.find('(') + 1: location_part.find(')')].strip()
            
            dates.append(date_part)
            locations.append(location)
            am_pm.append(am_pm_part)

    return dates, locations, am_pm


def create_calendar(candidates, cand_copy, spaces, solver, x, cost, pen_dict, cost_msg, output_file_data, output_file_clean):
    cal = Calendar() #contains ALL the info
    cal_copy = Calendar() #for restricted data
    current_year = datetime.now().year

    for i in range(0, len(candidates)):
        for s in spaces:
            for t in spaces:
                if solver.Value(x[candidates[i], s]) and solver.Value(x[cand_copy[i], t]):
                    # Determine event start time
                    updated_date = s.date.replace(year=current_year)
                    if s.time == 'AM':
                        start_time = datetime.combine(updated_date, datetime.strptime("09:00", "%H:%M").time())
                    elif s.time == 'PM':
                        start_time = datetime.combine(updated_date, datetime.strptime("13:00", "%H:%M").time())
                    else:
                        continue  # unknown time slot

                    # Create event
                    event = Event() #for calendar with all the data
                    event_copy = Event() #for private calendar with restricted data
                    pair_cost = cost[candidates[i], s]
                    pair_err = []

                    try:
                        pen = pen_dict[(candidates[i],s)]
                        for pair in pen:
                            (c2, s2, weight, err_msg) = pair
                            if solver.Value(x[c2, s2]):
                                pair_cost += weight
                                pair_err.append(err_msg)
                    except KeyError:
                        continue

                    if int(pair_cost) >= 1000000:
                        # subjects don't match
                        event.add('summary',
                                  f'🚨 Interview: {candidates[i].name} (id: {candidates[i].cand_id}) for {candidates[i].subject} with {s.interviewer} (id: {s.int_id}) and {t.interviewer} (id: {t.int_id}) ')
                    elif int(pair_cost) >= 10000:
                        event.add('summary',
                                  f'⚠️ Interview: {candidates[i].name} for {candidates[i].subject} with {s.interviewer} and {t.interviewer}')
                    else:
                        event.add('summary',
                                  f'Interview: {candidates[i].name} for {candidates[i].subject} with {s.interviewer} and {t.interviewer}')
                    event_copy.add('summary',
                                   f'Interview: {candidates[i].name} for {candidates[i].subject} with {s.interviewer} and {t.interviewer}')
                    event.add('description',
                    f'Total cost {pair_cost}. Penalties: {pair_err}, Cost: {cost_msg[(candidates[i],s)]}, Candidate location {candidates[i].address}, Candidate specialism(s) {candidates[i].specialisms}, {s.interviewer} subjects(s): {s.subjects} and specialisms: {s.specialisms}, {t.interviewer} subjects(s) {t.subjects} and specialisms {t.specialisms}')
                    event.add('dtstart', start_time)
                    event_copy.add('dtstart', start_time)
                    event.add('dtend', start_time + timedelta(hours=3)) 
                    event_copy.add('dtend', start_time + timedelta(hours = 3)) 
                    event.add('location', s.location)
                    event_copy.add('location', s.location)

                    cal.add_component(event)
                    cal_copy.add_component(event_copy)

    # Write to first .ics file
    with open(output_file_data, 'wb') as f:
        f.write(cal.to_ical())
    print(f"Calendar with extra data written to {output_file_data}")
    with open(output_file_clean, 'wb') as f:
        f.write(cal_copy.to_ical())
    print(f"Calendar without extra data written to {output_file_clean}")
