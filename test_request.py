import sys, time, sqlite3

import datetime

from owlready2 import *

print()
print()


db = sqlite3.connect("/tmp/test_quadstore.sqlite3", isolation_level = "EXCLUSIVE", check_same_thread = False)
#db = sqlite3.connect("/tmp/quadstore.sqlite3", isolation_level = "EXCLUSIVE", check_same_thread = False)

#import ctypes
#libsqlite3 = ctypes.cdll.LoadLibrary("libsqlite3.so")
#libsqlite3.sqlite3_db_config(, SQLITE_DBCONFIG_ENABLE_QPSG, 1, 0)

c = db.cursor()

#c.execute("""DROP INDEX ind;""")
c.execute("""DROP INDEX IF EXISTS ind;""")
c.execute("""DROP INDEX IF EXISTS ind2;""")
c.execute("""DROP INDEX IF EXISTS ind3;""")
c.execute("""DROP INDEX IF EXISTS ind4;""")
c.execute("""DROP TABLE IF EXISTS is_a_1;""")
c.execute("""DROP TABLE IF EXISTS is_a_3;""")
c.execute("""DROP TABLE IF EXISTS sqlite_stat1;""")
c.execute("""PRAGMA locking_mode = EXCLUSIVE""")

c.execute("""ANALYZE""")
#c.execute("""PRAGMA optimize""")


T = 0
def do(s):
  for s1 in s.split(";"):
    if s1.strip(): do1(s1)
  
def do1(s):
  global T
  
  s = s.strip()
  if s[-1] == ";": s = s[:-1]
  print(s)

  if   s.startswith("SELECT") or s.startswith("WITH"):
    for i in c.execute("""EXPLAIN QUERY PLAN %s""" % s).fetchall(): print(i)
    
    s2 = """WITH transit AS (%s) SELECT count() FROM transit""" % s
    
    t = time.time()
    r = ", %s résultats" % (c.execute(s2).fetchone() or ["-"])[0]
    t = time.time() - t
    
  elif s.startswith("INSERT"):
    if "SELECT" in s:
      s2 = s[s.find("SELECT"):]
      for i in c.execute("""EXPLAIN QUERY PLAN %s""" % s2).fetchall(): print(i)
      
    t = time.time()
    c.execute(s)
    t = time.time() - t
    
    r = ", %s insertions" % c.execute("""SELECT COUNT() FROM %s""" % s.replace(" OR IGNORE", "").split()[2]).fetchone()[0]
    
    
  else:
    t = time.time()
    c.execute(s)
    t = time.time() - t
    r = ""
    
  T += t
  print("    => %0.5f s%s" % (t, r))
  print()



print("\n\n\n")



do("""
SELECT q8.s,q6.s,q6.o,q7.s,q7.o
FROM some q4 CROSS JOIN prop_is_a q1 CROSS JOIN only q2, flat_lists_30 q6 CROSS JOIN is_a q8, flat_lists_30 q7, is_a q9, flat_lists_37 q11, flat_lists_37 q12, is_a q14, is_a q15, is_a q5 CROSS JOIN is_a q3
WHERE q2.prop=q1.o AND q3.o=q2.s AND q4.prop=q1.s AND q5.o=q4.s AND q6.o=q3.s AND q7.o=q5.s AND q8.o=q6.s AND q8.l<=3 AND q9.s=q8.s AND q9.o=q7.s AND q9.l<=3 AND q6.s!=q7.s AND q12.s=q11.s AND q11.o!=q12.o AND q14.s=q4.value AND q14.o=q11.o AND q15.s=q2.value AND q15.o=q12.o

""")

do("""
SELECT q8.s,q6.s,q6.o,q7.s,q7.o
FROM some q4 CROSS JOIN prop_is_a q1 CROSS JOIN only q2, flat_lists_30 q6 CROSS JOIN is_a q8, flat_lists_37 q11, is_a q14, flat_lists_37 q12, is_a q15, is_a q9, flat_lists_30 q7, is_a q5 CROSS JOIN is_a q3
WHERE q2.prop=q1.o AND q3.o=q2.s AND q4.prop=q1.s AND q5.o=q4.s AND q6.o=q3.s AND q7.o=q5.s AND q8.o=q6.s AND q8.l<=3 AND q9.s=q8.s AND q9.o=q7.s AND q9.l<=3 AND q6.s!=q7.s AND q12.s=q11.s AND q11.o!=q12.o AND q14.s=q4.value AND q14.o=q11.o AND q15.s=q2.value AND q15.o=q12.o

""")

do("""
SELECT q8.s,q6.s,q6.o,q7.s,q7.o
FROM some q4, prop_is_a q1, only q2, flat_lists_30 q6, is_a q8, flat_lists_37 q11, is_a q14, flat_lists_37 q12, is_a q15, is_a q9, flat_lists_30 q7, is_a q5, is_a q3
WHERE q2.prop=q1.o AND q3.o=q2.s AND q4.prop=q1.s AND q5.o=q4.s AND q6.o=q3.s AND q7.o=q5.s AND q8.o=q6.s AND q8.l<=3 AND q9.s=q8.s AND q9.o=q7.s AND q9.l<=3 AND q6.s!=q7.s AND q12.s=q11.s AND q11.o!=q12.o AND q14.s=q4.value AND q14.o=q11.o AND q15.s=q2.value AND q15.o=q12.o

""")


do("""
SELECT q1.prop,q4.value,q7.s,q3.s,q3.o,q6.s,q6.o
FROM some q1, prop_is_a q9, only q4, flat_lists_30 q3, flat_lists_30 q6, is_a q7, is_a q8, is_a q10, infer_ancestors q12, is_a q2, is_a q5
WHERE q2.o=q1.s AND q3.o=q2.s AND q5.o=q4.s AND q6.o=q5.s AND q7.o=q6.s AND q7.l<=3 AND q8.s=q7.s AND q8.o=q3.s AND q8.l<=3 AND q9.s=q1.prop AND q9.o=q4.prop AND q10.s=q4.value AND q10.o=q1.value AND q4.value!=q1.value AND q12.s=q7.s

""")
