from datetime import datetime, timedelta

import pandas as pd
from icalendar import Calendar, Event


def extract_data():
    candidate_df = pd.read_excel('data/20_applicants.xlsx')
    academic_df = pd.read_excel('data/Scholarship_Assessor_Data.xlsx')
    return candidate_df, academic_df


def parse_schedule(schedule_str):
    items = schedule_str.split(';')
    locations = []
    dates = []

    for item in items:
        item = item.strip()
        if '(' in item and ')' in item:
            date_part = item.split('(')[0].strip()
            location = item[item.find('(') + 1: item.find(')')].strip()
            dates.append(date_part)
            locations.append(location)

    return dates, locations


def create_calendar(candidates, cand_copy, spaces, solver, x, cost, output_file='output/interviews.ics'):
    cal = Calendar()

    current_year = datetime.now().year

    for i in range(0, len(candidates)):
        for s in spaces:
            for t in spaces:
                if solver.Value(x[candidates[i], s]) and solver.Value(x[cand_copy[i], t]):
                    # Determine event start time
                    updated_date = s.date.replace(year=current_year)
                    if s.time == 'morning':
                        start_time = datetime.combine(updated_date, datetime.strptime("09:00", "%H:%M").time())
                    elif s.time == 'afternoon':
                        start_time = datetime.combine(updated_date, datetime.strptime("13:00", "%H:%M").time())
                    else:
                        continue  # unknown time slot

                    # Create event
                    event = Event()
                    if cost[candidates[i], s] == 1000000:
                        event.add('summary',
                                  f'⚠️ Interview: {candidates[i].name} with {s.interviewer} and {t.interviewer}')
                    else:
                        event.add('summary',
                                  f'Interview: {candidates[i].name} with {s.interviewer} and {t.interviewer}')
                    event.add('dtstart', start_time)
                    event.add('dtend', start_time + timedelta(hours=1))  # Assume 1 hour interview
                    event.add('location', s.location)
                    # TODO: `c` is undefined here
                    event.add('description', f'Subject: {c.subject}')

                    if candidates[i].name == "Brian Brown":
                        print(candidates[i].subject)
                        print(s.subjects)
                        print(t.subjects)

                    cal.add_component(event)

    # Write to .ics file
    with open(output_file, 'wb') as f:
        f.write(cal.to_ical())
    print(f"Calendar written to {output_file}")
