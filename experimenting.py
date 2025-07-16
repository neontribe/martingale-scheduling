import pandas as pd
import random

df = pd.read_excel("Scholarship_Assessor_Data.xlsx")
print(df.iloc[0,0]) #0 Name
print(df.iloc[1,0]) #1 Email
print(df.iloc[2,0]) #2 Date
print(df.iloc[3,0]) #3 Courses
print(df.iloc[4,0]) #4 MMath specialism
print(df.iloc[5,0]) #5 MPhD specialism

df2 = pd.read_excel("Application_Form_Data.xlsx")
print(df2.iloc[0,0]) #0 Start time
print(df2.iloc[1,0]) #1 Completion time
print(df2.iloc[2,0]) #2 Email
print(df2.iloc[3,0]) #3 Name
print(df2.iloc[4,0]) #4 Last modified time
print(df2.iloc[5,0]) #5 Dates
print(df2.iloc[6,0]) #6 City
print(df2.iloc[7,0]) #7 Masters subjects
print(df2.iloc[8,0]) #8 PhD subjects
print(df2.iloc[9,0]) #9 MMath specialism
print(df2.iloc[10,0]) #10 MPhd Specialism


list = []
for i in range (0,10):
    sub_list = []
    for j in range (0,3):
        string = "adventurous"
        k = j+random.randint(0,4)
        sub_list.append(string[k])
    list.append(sub_list)

print(list)
print(list[0])

list1 = [1,2,3]
list2 = [4,5,6]
list3 = [[list1] + [list2]]
print(list3)