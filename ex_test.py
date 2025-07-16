from owlready2 import *
import sys, os, unittest, tempfile, atexit, types

from semantic2sql.reasoned_model import *

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
    #if hasattr(self, 'world'):
    #    self.world.close()
    #    del self.world

    self.world = World()
    if KEEP:
      try: os.unlink("/tmp/test_quadstore.sqlite3")
      except: pass
      self.world.set_backend(filename = "/tmp/test_quadstore.sqlite3")
      
    # Load your local ontology instead of creating a new one
    #self.onto = self.world.get_ontology("/Users/rodrigo/Ont/examples/ex_med.owl").load()
    #self.onto = self.world.get_ontology("/Users/rodrigo/Ont/examples/ex(in)_med.xml").load()
    self.onto = self.world.get_ontology("/Users/rodrigo/Ont/Ont_alc/PizzaTutorial_alc.owl").load()


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
class Test(BaseTest):
  ## Not equivalent 
   def test_and_10(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class D(Thing): is_a = [A1 & B1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, A)
    assert issubclass(D, B)

    def test_some_3(self):
        with self.onto:
            class p(ObjectProperty): pass
            class A(Thing): pass
            class A1(A): is_a = [p.some(Nothing)]
            class B(Thing): is_a = [p.some(A1)]
            class B1(B): pass
        
        rm = self.sync_reasoner()
    
        self.assert_is_a(A1.storid, Nothing.storid)
        self.assert_is_a(B1.storid, Nothing.storid)
        assert issubclass(A1, Nothing)
        assert issubclass(B1, Nothing)
    ######################################################
   
   def test_and_some_3(self):
        with self.onto:
            class p(ObjectProperty): pass
            class A(Thing): pass
            class B(Thing): pass
            AllDisjoint([A, B])
            class C(Thing): pass
            class D(Thing): is_a = [p.some(A & B) & C]
            class E(Thing): is_a = [p.some(A & B) | C]
        
        
        rm = self.sync_reasoner()
        
        assert issubclass(D, Nothing)
        assert issubclass(E, C)

   # some error in Owlready2 
   #def test_or_2(self):
   #    with self.onto:
   #     class C(Thing): pass
   #     class A(C): pass
   #     class B(C): pass
   #     class D(Thing): is_a = [A | B]
      
   #     rm = self.sync_reasoner()
        
   #     assert issubclass(D, C)

   def test_disjoint_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      AllDisjoint([A, B, C])
      
      class D(A1, B1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, Nothing) 

   def test_disjoint_or_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1, B1 | C]
      
    rm = self.sync_reasoner()

    assert issubclass(M, C)

   
   def test_disjoint_and_1(self):
       with self.onto:
            class A(Thing): pass
            class A1(A): pass
            class B(Thing): pass
            class B1(B): pass
            AllDisjoint([A, B])
            
            class M(Thing): is_a = [A1 & B1]
       
       rm = self.sync_reasoner()
       
       assert issubclass(M, Nothing)
     
   
    #def test_not_0(self):
    # with self.onto:
    #   class A(Thing): pass
    #   class M(Thing): is_a = [Not(A)]
       
    # rm = self.sync_reasoner()
     
   def test_not_1(self):
     with self.onto:
       class A(Thing): pass
       class M(A): is_a = [Not(A)]
       
     rm = self.sync_reasoner()
     
     assert issubclass(M, Nothing)
     
 
   def test_long_is_a_1(self):
     with self.onto:
       parents = (Thing,)
       classes = []
       for i in range(200):
         C = types.new_class("C%s" % i, parents)
         classes.append(C)
         parents = (C,)
       
     rm = self.sync_reasoner()
 
   def test_concrete_1(self):
     with self.onto:
       class p(Thing >> Thing): pass
       class A(Thing): pass
       class A1(A): pass
       class B(Thing): pass
       class B1(B): pass
 
       class M(Thing):
         is_a = [p.some(A)]
 
       m = M()
       
     rm = self.sync_reasoner()
     
     self.assert_concrete(m.storid)
     self.assert_concrete(M.storid)
     self.assert_concrete(A.storid)
     self.assert_not_concrete(A1.storid)
     self.assert_not_concrete(B.storid)
     self.assert_not_concrete(B1.storid)    
 
   def test_individual_1(self):
     with self.onto:
       class A(Thing): pass
       class B(Thing): pass
       AllDisjoint([A, B])
       class C(A, B): pass
       c = C()
       
     rm = self.sync_reasoner(consistent = False)
     
   def test_individual_2(self):
     with self.onto:
       class p(ObjectProperty): pass
       class A(Thing): pass
       a = A("a")
       A.is_a.append(OneOf([a]))
       class A1(A): pass
       class A2(A): pass
       AllDisjoint([A1, A2])
       A1()
       A2()
       
     rm = self.sync_reasoner(consistent = False)
     
   def test_individual_3(self):
     with self.onto:
       class p(ObjectProperty): pass
       class A(Thing): pass
       a = A("a")
       A.is_a.append(OneOf([a]))
       class A1(A): pass
       class A2(A): pass
       AllDisjoint([A1, A2])
       A1()
       
     rm = self.sync_reasoner()
     
   def test_individual_4(self):
     with self.onto:
       class p(ObjectProperty): pass
       class A(Thing): pass
       a1 = A("a1")
       a2 = A("a2")
       A.is_a.append(OneOf([a1, a2]))
       class A_1(A): pass
       class A_2(A): pass
       class A_3(A): pass
       AllDisjoint([A_1, A_2, A_3])
       A_1()
       A_2()
       A_3()
       
     rm = self.sync_reasoner() 

######################################################

########### Second test class of the script ###########
class Exp(BaseTest):

  def test_yyy(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(6):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
    rm = self.sync_reasoner()




  def test_xxx1(self): # Fonctionne mais lent...
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [#random.p1.some(random.C3),
                         random.p2.only(random.C1 & random.C2 & random.C3 & random.p1.some(random.C1)),
      ]
      random.C3.is_a =  [random.C1]
      random.C4.is_a =  [random.C1,
                         random.C2,
                        (random.p1.some(random.C1) & random.C1) | (random.C3),
                         random.p2.some(random.C1),
      ]
      
    rm = self.sync_reasoner()


  def test_xxx2(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(8):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C3 & random.C2)]
      random.C3.is_a =  [random.C1]
      random.C4.is_a =  [random.C2]
      random.C6.is_a =  [random.p1.some(random.C1 & random.C2)]
      random.C7.is_a =  [random.C1,
                         (random.C3 & random.C1 & random.C2) | (random.C3 & random.p2.some(random.C3) & random.C1 & random.C2) | random.C3, random.p1.some(random.C6),
                         random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()
    
  def test_xxx3(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(3):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      # random.p1
      # random.p2
      # random.p3
      # random.p4.is_a =  [random.p5]
      # random.p5.is_a =  [random.p2]
      # random.C1.is_a =  [Thing, random.p5.only(random.C1), random.p5.only(random.C1), random.p1.some(random.C1), random.p1.some(random.C1)]
      # random.C2.is_a =  [random.C1, random.p1.some(random.C3)]
      # random.C3.is_a =  [random.C2, random.p1.some(random.C3), random.p1.some(random.C1) | random.C3 | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p5.only(random.C1) & random.C1) | random.C2, random.p4.some(random.p5.only(random.C1))]
      # random.C4.is_a =  [random.C2]
      # random.C5.is_a =  [random.C1, random.p4.some(random.p5.only(random.C1))]
      # random.C6.is_a =  [random.C1]
      
      random.C1.is_a =  [Thing,
                         random.p2.only(random.C1),
                         random.p1.some(random.C1)]
      random.C2.is_a =  [random.C1]
      #random.C3.is_a =  [random.C1,
      #                   random.p1.some(random.C1) | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p2.only(random.C1) & random.C1) | random.C2,
      #                   random.p2.some(random.p2.only(random.C1))]
      random.C3.is_a =  [random.C2,
                         random.p1.some(random.C3),
                         random.p1.some(random.C1) | random.C3 | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p2.only(random.C1) & random.C1) | random.C2,
                         random.p2.some(random.p2.only(random.C1))]

    rm = self.sync_reasoner()

    
##############################

if __name__ == '__main__': unittest.main()
