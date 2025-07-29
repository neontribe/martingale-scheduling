from datetime import datetime

from .utilities import parse_schedule


class Space:
    def __init__(self, date, datestr, time, location, specialisms, subjects, interviewer):
        self.date = date
        self.time = time
        self.location = location
        self.specialisms = specialisms  # list
        self.subjects = subjects  # list
        self.interviewer = interviewer
        self.datestr = datestr

    @staticmethod
    def gen_spaces(df):
        """One space refers to one interview slot at a particular time/date/location and with an interviewer.
        Candidates will be allocated a pair of spaces per course, to have 2 interviewers per interview"""
        spaces = []
        date_format = '%A %d %B'
        for col in df:  # for every interviewer

            # extracting cells from interviewer column in dataframe
            avail = df[col].iloc[2]
            subjects = df[col].iloc[3]
            
            mmath = str((df[col].iloc[4])).split(";")
            for i in range (0, len(mmath)):
                mmath[i] = mmath[i].strip()

            mphd = str((df[col].iloc[5])).split(";")
            for i in range (0, len(mphd)):
                mphd[i] = mphd[i].strip()

            mmath = set(mmath)
            mphd = set(mphd)
            specialisms = {"MMath TEST": mmath, "MPhd": mphd}
            interviewer = df[col].iloc[0]
            # separating out the dates and corresponding locations from availability cell

            dates, locations = parse_schedule(avail)

            for i in range(0, len(dates)):  # for every date interviewer is available

                # create 2 new spaces (am/pm) for each date in the avail list
                date_obj = datetime.strptime(dates[i], date_format)  # create date object for ease of date arithmetic
                morning_space = Space(date_obj, dates[i], "morning", locations[i], specialisms, subjects, interviewer)
                afternoon_space = Space(date_obj, dates[i], "afternoon", locations[i], specialisms, subjects,
                                        interviewer)
                spaces.append(morning_space)
                spaces.append(afternoon_space)

        return spaces


class Subj_Candidate:
    def __init__(self, name, avail, address, specialisms, subject):
        self.name = name
        self.avail = avail
        self.address = address
        self.specialisms = specialisms
        self.subject = subject

    @staticmethod
    def gen_cand(df):
        """Instantiates the Subj_Cand class. One of these per interviewee per course they are interviewing for"""
        candidates = []
        ME_all_cand = []  # this is a 2d list containing lists of candidate objects belonging to the same interviewee
        # it is used to ensure that one interviewee is not double-booked (or booked on consecutive dates) for different course

        for col in df:  # for every interviewee

            # extracting data from interviewee column in dataframe
            name = df[col].iloc[3]
            avail = df[col].iloc[5]
            address = df[col].iloc[6]
            mast_subjects = str(df[col].iloc[7]).split(';')
            for i in range (0, len(mast_subjects)):
                mast_subjects[i] = mast_subjects[i].strip()

            phd_subjects = str(df[col].iloc[8]).split(';')
            for i in range (0, len(phd_subjects)):
                phd_subjects[i] = phd_subjects[i].strip()
                
            mmath = str((df[col].iloc[9])).split(";")
            for i in range (0, len(mmath)):
                mmath[i] = mmath[i].strip()

            mphd = str((df[col].iloc[10])).split(";")
            for i in range (0, len(mphd)):
                mphd[i] = mphd[i].strip()
            mmath = set(mmath)
            mphd = set(mphd)

            for ele in mast_subjects:  # for every masters course being interviewed for
                if (ele != "nan") and (name != "Name"):
                    course = ele + " Masters"
                    if ele == "Maths":
                        specialism = mmath
                    else:
                        specialism = "nan"
                    subj_cand = Subj_Candidate(name, avail, address, specialism, course)
                    candidates.append(subj_cand)

            for ele in phd_subjects:  # for every phd course being interviewed for
                if ele != "nan" and (name != "Name"):
                    course = ele + " PhD"
                    if ele == "Maths":
                        specialism = mphd
                    else:
                        specialism = "nan"
                    subj_cand = Subj_Candidate(name, avail, address, specialism, course)
                    candidates.append(subj_cand)
                                
        return candidates
