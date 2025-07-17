import pandas as pd

def extract_data():
    candidate_df = pd.read_excel('20_applicants.xlsx')
    academic_df = pd.read_excel('Scholarship_Assessor_Data.xlsx')
    return candidate_df, academic_df

def parse_schedule(schedule_str):
    items = schedule_str.split(';')
    locations = []
    dates = []

    for item in items:
        item = item.strip()
        if '(' in item and ')' in item:
            date_part = item.split('(')[0].strip()
            location = item[item.find('(')+1 : item.find(')')].strip()
            dates.append(date_part)
            locations.append(location)

    return dates, locations

class Space:
    def __init__(self, date, datestr, time, location, specialisms, subjects, interviewer):
        self.date = date
        self.time = time
        self.location = location
        self.specialisms = specialisms #list
        self.subjects = subjects #list
        self.interviewer = interviewer
        self.datestr = datestr

class Subj_Candidate:
    def __init__(self, name, avail, address, specialisms, subject):
        self.name = name
        self.avail = avail
        self.address = address
        self.specialisms = specialisms
        self.subject = subject