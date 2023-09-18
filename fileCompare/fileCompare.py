import pandas as pd
import archiveFileData
from logFileData import logFilesData1, logFilesData2

def sanitize(splitFiles):
    # remove empty lines
    splitFiles = [x.strip() for x in splitFiles if x.strip()]
    # for file in splitFiles:
    #     print(file.strip())
    return splitFiles

#   splitFiles2 = [x.split("-")[1] for x in splitFiles2 if x]
def find_duplicates(lst):
    seen = set()
    duplicates = []
    for item in lst:
        if item in seen:
            duplicates.append(item)
        seen.add(item)

    return list(duplicates)

def logFileManipulations():
    splitFiles = sanitize(logFilesData1.split(','))
    splitFiles2 = sanitize(logFilesData2.splitlines())
    print("splitFiles", len(splitFiles))
    print("splitFiles2", len(splitFiles2))

    # use pandas to compare the two lists
    # Convert lists to pandas Series
    s1 = pd.Series(splitFiles)
    s2 = pd.Series(splitFiles2)

    # Find items in list1 that are not in list2
    not_in_list2 = s1[~s1.isin(s2)].tolist()
    not_in_list1 = s2[~s2.isin(s1)].tolist()
    print("not_in_list2" ,len(not_in_list2))
    print("not_in_list1" , len(not_in_list1))


logFileManipulations()
# user archiveList from dataFiles3.py here how to import
archiveList = archiveFileData.sanitizeArchiveList()
print("find_duplicates",find_duplicates(archiveList))



