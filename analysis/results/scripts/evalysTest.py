# coding: utf-8
import matplotlib.pyplot as plt
from evalys.jobset import JobSet

#matplotlib.use('WX')

js = JobSet.from_csv('../../outputs/train/T1/FCFS_FCFS_T1/jobs.csv')
js.df = js.df.head(20)

js.df.hist()

#fig, axe = plt.subplots()
js.gantt()
plt.savefig("Test.png")