from owlready2 import *
import sys, os, unittest, tempfile, atexit, types

from semantic2sql.reasoned_model import *

# sys.setrecursionlimit(10**6)

if "--keep" in sys.argv:
  sys.argv.remove("--keep")
  KEEP = True
else:
  KEEP = False

if "--debug" in sys.argv:
  sys.argv.remove("--debug")
  DEBUG = True
else:
  DEBUG = False

if "--dump" in sys.argv:
  sys.argv.remove("--dump")
  DUMP = True
else:
  DUMP = False
  
if "--explain" in sys.argv:
  sys.argv.remove("--explain")
  EXPLAIN = True
else:
  EXPLAIN = False


if "-r" in sys.argv:
  i = sys.argv.index("-r")
  FORCED_RULES_FILE = "rules_%s.txt" % sys.argv[i+1]
  del sys.argv[i+1]
  del sys.argv[i]
else:
  FORCED_RULES_FILE = None


RULES_FILE = "rules.txt"


get_rule_set("rules.txt") # Preload rule set

class BaseTest(unittest.TestCase):
  def __init__(self, args):
    unittest.TestCase.__init__(self, args)
    self._next_onto = 1
    
  def setUp(self):
    # Clear any existing world

    self.world = World()
    if KEEP:
      try: os.unlink("/tmp/test_quadstore.sqlite3")
      except: pass
      self.world.set_backend(filename = "/tmp/test_quadstore.sqlite3")
      
    # Load your local ontology instead of creating a new one
    self.onto = self.world.get_ontology("/Users/rodrigo/Ont/lub.owl").load()
  

    # Initialize the reasoned model tables if they don't exist
    temp_rm = ReasonedModel(self.world, rule_set=RULES_FILE, temporary=True)
    #temp_rm.initialize_database()
    #temp_rm.close()

  def tearDown(self):
    if KEEP: self.world.save()
    
    if EXPLAIN:
      import semantic2sql.html_explain
      explanation = semantic2sql.html_explain.HTMLExplanation(self.rm)
      explanation.show()
      
  def sync_reasoner(self, consistent=True):
    print("Initializing ReasonedModel...")  # Debug
    rm = self.rm = ReasonedModel(self.world, rule_set = RULES_FILE, temporary = not KEEP, debug = DEBUG, explain = EXPLAIN)
    print("ReasonedModel initialized, running reasoner...")  # Debug
    
    onto_inference = self.world.get_ontology("http://test.org/inferrences_%s.owl" % self._next_onto)
    self._next_onto += 1
    
    with onto_inference:
      if consistent:
        rm.run()
        print()
        rm.print_rule_usage()
      else:
        ok = False
        try:
          rm.run()
        except OwlReadyInconsistentOntologyError:
          print()
          rm.print_rule_usage()
          ok = True
        assert ok
        
    self.nb_inferences = len(onto_inference.graph) - 1
    
    if DUMP:
      rm.dump_inferences()
      print()
      rm.dump_constructs()
      print()
      print("  => Inferences:")
      onto_inference.graph.dump()
    return rm
  
  def assert_is_a(self, s, o):
    r = self.rm.cursor.execute("SELECT 1 FROM is_a WHERE s=? AND o=?""", (s, o)).fetchone()
    assert not r is None
    
  def assert_not_is_a(self, s, o):
    r = self.rm.cursor.execute("SELECT 1 FROM is_a WHERE s=? AND o=?""", (s, o)).fetchone()
    assert r is None
    r = self.rm.cursor.execute("SELECT 1 FROM is_a_construct WHERE s=? AND o=?""", (s, o)).fetchone()
    assert r is None

  def assert_concrete(self, s):
    r = self.rm.cursor.execute("SELECT 1 FROM concrete WHERE s=?""", (s,)).fetchone()
    assert not r is None

  def assert_not_concrete(self, s):
    r = self.rm.cursor.execute("SELECT 1 FROM concrete WHERE s=?""", (s,)).fetchone()
    assert r is None

#############First Test Class (Add your tests here)###
#class SimpleTest(BaseTest):
#    def test_simple(self):
#        with self.onto:
#            class A(Thing): pass
#            class B(A): pass
        
#        rm = self.sync_reasoner()
#        self.assert_is_a(B.storid, A.storid)

class GraduateStudentCourseTest(BaseTest):
    def test_graduate_student_takes_course(self):
        with self.onto:
            # Define classes
            class GraduateStudent(Thing): pass
            class GraduateCourse(Thing): pass
            
            # Define property
            class takesCourse(Thing >> GraduateCourse): pass
            
            # Create individuals
            grad_student = GraduateStudent("grad_student_0")
            target_course = GraduateCourse("http://www.Department0.University0.edu/GraduateCourse0")
            
            # Assert relationship
            grad_student.takesCourse.append(target_course)
        
        # Run reasoner
        rm = self.sync_reasoner()
        
        # Test that the student takes the specific course
        self.assertIn(target_course.storid, [c.storid for c in grad_student.takesCourse])
        
        # Alternative assertion using direct storage IDs
        #self.assert_relation(grad_student.storid, takesCourse.storid, target_course.storid)   
    
######################################################

########### Second test class of the script ###########


##############################

if __name__ == '__main__': unittest.main()
