# -*- coding: utf-8 -*-
# Owlready2
# Copyright (C) 2019 Jean-Baptiste LAMY
# LIMICS (Laboratoire d'informatique médicale et d'ingénierie des connaissances en santé), UMR_S 1142
# University Paris 13, Sorbonne paris-Cité, Bobigny, France

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#  python ./semantic2sql/regtest2.py Test

#  python ./semantic2sql/regtest2.py Exp.test_xxx1 --keep --debug

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
    self.world = World()
    if KEEP:
      try: os.unlink("/tmp/test_quadstore.sqlite3")
      except: pass
      self.world.set_backend(filename = "/tmp/test_quadstore.sqlite3")
      
    self.onto  = self.world.get_ontology("http://test.org/onto.owl")
    #self.onto = self.world.get_ontology("/Users/rodrigo/Ont/Ont_alc/PizzaTutorial_alc.owl").load()
    
  def tearDown(self):
    if KEEP: self.world.save()
    
    if EXPLAIN:
      import semantic2sql.html_explain
      explanation = semantic2sql.html_explain.HTMLExplanation(self.rm)
      explanation.show()
      
  def sync_reasoner(self, consistent = True):
    rm = self.rm = ReasonedModel(self.world, rule_set = RULES_FILE, temporary = not KEEP, debug = DEBUG, explain = EXPLAIN)
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
        
    
class Test(BaseTest):
  def test_is_a_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class A2(A1): pass
      class R(Thing): equivalent_to = [A1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A2, R)
    
  def test_and_1(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class AB(A, B): pass
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, R)
    
  def test_and_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class AB(A1, B): pass
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, R)
    
  def test_and_3(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class AB(A1, B1): pass
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, R)
    
  def test_and_4(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class AB(Thing): is_a = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, A)
    assert issubclass(AB, B)
    
  def test_and_5(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class AB(Thing): is_a = [A1 & B1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, A1)
    assert issubclass(AB, A)
    assert issubclass(AB, B1)
    assert issubclass(AB, B)
    
  # @rules_files("")
  # def test_and_6(self):
  #   with self.onto:
  #     class A(Thing): pass
  #     class B(Thing): pass
  #     class AB(A, B): pass
  #     class R(Thing): is_a = [A & B]
      
  #   rm = self.sync_reasoner()
    
  #   self.assert_not_is_a(AB.storid, [x for x in R.is_a if x.storid < 0][0].storid)

  def test_and_7(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class ABC(A, B, C): pass
      class R(Thing): equivalent_to = [A & B & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(ABC, R)

  def test_and_8(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      class D(Thing): is_a = [(A1 & B1) | C]
      
      class R(Thing): equivalent_to = [(A & B) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  def test_and_9(self):
    with self.onto:
      class A(Thing): pass
      class Z(Thing): pass
      class A1(Thing): is_a = [A | Z]
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      class D(Thing): is_a = [(A1 & B1) | C]
      
      class R(Thing): equivalent_to = [(A & B) | C | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
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
    
  def test_and_11(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): is_a = [A1 & B1]
      
      class R(Thing): pass
      class R1(R): equivalent_to = [A1 & B1]
      
    rm = self.sync_reasoner()
    
    self.assert_is_a(C.storid, R .storid)
    self.assert_is_a(C.storid, R1.storid)
    assert issubclass(C, R1)
    assert issubclass(C, R)

  def test_some_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): is_a = [p.some(A)]
      class R(Thing): equivalent_to = [p.some(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(B, R)

  def test_some_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): is_a = [p.some(A1)]
      class R(Thing): equivalent_to = [p.some(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(B, R)

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
    
  def test_some_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): is_a = [p.some(Nothing)]
      class B(Thing): is_a = [p.some(A1) & A]
      class B1(B): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(B1, Nothing)
    
  def test_some_5(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): is_a = [p.some(A1 & B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, Nothing)
    
  def test_some_6(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): is_a = [p.some((A1 & B1) | C)]

      class R(Thing): equivalent_to = [p.some(C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)

  def test_some_7(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): is_a = [p.some(A1 & B1)]

      class R(Thing): equivalent_to = [p.some(A) & p.some(B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)

  def test_some_8(self):
    with self.onto:
      class p(ObjectProperty): pass
      class C(Thing): pass
      C.is_a = [p.some(C)]

      class R1(Thing): equivalent_to = [p.some(p.some(C))]
      class R2(Thing): equivalent_to = [p.some(p.some(p.some(C)))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C,  R1)
    assert issubclass(C,  R2)
    assert issubclass(R1, R2)

    
  def test_some_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class D(Thing): is_a = [p.some(A1 | B1)]
      class E(Thing): is_a = [p.some(A1)]
      
      class R1(Thing): equivalent_to = [p.some(A | B)]
      class R2(Thing): equivalent_to = [p.some(A) | p.some(B)]
      class R3(Thing): equivalent_to = [p.some(A1) | p.some(B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R1)
    assert issubclass(D, R2)
    assert issubclass(D, R3)
    assert issubclass(E, R1)
    assert issubclass(E, R2)
    assert issubclass(E, R3)
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)
    assert issubclass(R3, R2)
    
  def test_some_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class D(Thing): equivalent_to = [p.some(A | B)]
      class R(Thing): equivalent_to = [p.some(A) | p.some(B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    assert issubclass(R, D)
    
  def test_some_or_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class A1B1(Thing): is_a = [A1 | B1]
      class C(Thing): pass
      class C1(C):       is_a = [p.some(A1B1)]
      
      class R(Thing): equivalent_to = [(p.some(A1) & C) | p.some(B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C1, R)
    
  def test_some_or_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class R1(Thing): equivalent_to = [p.some(A | B | C)]
      class R2(Thing): equivalent_to = [p.some(A) | p.some(B) | p.some(C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)

  def test_some_or_5(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      C.is_a = [A | B, p.some(C)]
      
      class R1(Thing): equivalent_to = [p.some(A) | p.some(B)]
      class R2(Thing): equivalent_to = [p.some(p.some(A)) | p.some(p.some(B))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R1)
    assert issubclass(C, R2)

  def test_some_or_6(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class C(Thing): pass
      C.is_a = [A | B, p.some(C), p.only(A1)]
      
      class R(Thing): equivalent_to = [p.some(B) | p.some(A1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)





    
  def test_only_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): is_a = [p.only(A1)]

      class R(Thing): equivalent_to = [p.only(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(B, R)
    
  def test_only_and_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class R1(Thing): equivalent_to = [p.only(A) & p.only(B)]
      class R2(Thing): equivalent_to = [p.only(A & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)
    
  def test_only_and_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class R1(Thing): equivalent_to = [p.only(A) & C & p.only(B)]
      class R2(Thing): equivalent_to = [p.only(A & B) & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)
    
  def test_only_and_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class R1(Thing): equivalent_to = [p.only(A1) & p.only(B1)]
      class R2(Thing): equivalent_to = [p.only(A & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R1, R2)
    
  def test_only_and_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class R1(Thing): equivalent_to = [p.only(A) & p.only(B)]
      class R2(Thing): equivalent_to = [p.only(A1 & B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R2, R1)
    
  def test_only_and_5(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): is_a = [p.only(A), p.only(B)]
      class R(Thing): equivalent_to = [p.only(A & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)

    
  def test_only_and_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class R1(Thing): equivalent_to = [(p.only(A) & p.only(B)) | C]
      class R2(Thing): equivalent_to = [ p.only(A & B) | C ]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)
    
  def test_only_and_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      #class R1(Thing): equivalent_to = [p.only(A) & p.only(B | C)]
      class R1(Thing): is_a = [p.only(A), p.only(B | C)]
      class R2(Thing): equivalent_to = [p.only((A & B) | C)]
      
    rm = self.sync_reasoner()
    
    print(R1.is_a, R1.equivalent_to)
    print(R2.is_a, R2.equivalent_to)
    
    assert issubclass(R1, R2)
    
  def test_only_and_or_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class R1(Thing): equivalent_to = [p.only(A | C) & p.only(B | C)]
      class R2(Thing): equivalent_to = [p.only((A & B) | C)]
      
    rm = self.sync_reasoner()
    
    print(R1.is_a, R1.equivalent_to)
    print(R2.is_a, R2.equivalent_to)
    
    assert issubclass(R1, R2)
    assert issubclass(R2, R1)
    

    
  def test_only_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): is_a = [p.only(A1) | p.only(B1)]

      class R(Thing): equivalent_to = [p.only(A | B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
    
  def test_some_only_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): is_a = [p.only(A)]
      class C1(C): pass
      class D(Thing): is_a = [p1.some(B)]
      class D1(D): pass
      class E(C1, D1): pass
      class E1(E): pass
      
      class R(Thing): equivalent_to = [p1.some(A & B)]
      
    rm = self.sync_reasoner()

    self.assert_is_a(E1.storid, R.storid)
    assert issubclass(E1, R)
    
  def test_some_only_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class Z(Thing): pass
      class C(Thing): is_a = [p.only(A) | Z]
      class C1(C): pass
      class D(Thing): is_a = [p.some(B)]
      class D1(D): pass
      class E(C1, D1): pass
      class E1(E): pass
      
      class R(Thing): equivalent_to = [p.some(A & B) | Z]
      
    rm = self.sync_reasoner()
    
    self.assert_is_a(E1.storid, R.storid)
    assert issubclass(E1, R)
    
  def test_some_only_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class Z(Thing): pass
      class C(Thing): is_a = [p.only(A)]
      class C1(C): pass
      class D(Thing): is_a = [p.some(B) | Z]
      class D1(D): pass
      class E(C1, D1): pass
      class E1(E): pass
      
      class R(Thing): equivalent_to = [p.some(A & B) | Z]
      
    rm = self.sync_reasoner()

    self.assert_is_a(E1.storid, R.storid)
    assert issubclass(E1, R)
    
  def test_some_only_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class Za(Thing): pass
      class Zb(Thing): pass
      class Zc(Thing): pass
      class C(Thing): is_a = [p.only(A)]
      class C1(C): pass
      class D(Thing): is_a = [p.some(B) | Za | Zb | Zc]
      class D1(D): pass
      class E(C1, D1): pass
      class E1(E): pass
      
      class R(Thing): equivalent_to = [p.some(A & B) | Za | Zb | Zc]
      
    rm = self.sync_reasoner()

    self.assert_is_a(E1.storid, R.storid)
    assert issubclass(E1, R)
    
  def test_some_only_5(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class Za(Thing): pass
      class Zb(Thing): pass
      class Zc(Thing): pass
      class C(Thing): is_a = [p.only(A) | Za]
      class C1(C): pass
      class D(Thing): is_a = [p.some(B) | Zb | Zc]
      class D1(D): pass
      class E(C1, D1): pass
      class E1(E): pass
      
      class R(Thing): equivalent_to = [p.some(A & B) | Za | Zb | Zc]
      
    rm = self.sync_reasoner()

    self.assert_is_a(E1.storid, R.storid)
    assert issubclass(E1, R)

  def test_some_only_6(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class H(Thing): is_a = [p.some(A1), p.only(B1)]
      
      class R(Thing): equivalent_to = [p.some(A & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(H, R)

  def test_some_only_7(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class H(Thing): is_a = [p.some(A1), p.only(B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(H, Nothing)
    
  def test_some_only_8(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      
      class M(Thing): is_a = [p.some(A | B), p.only(A1)]
      
      class R(Thing): equivalent_to = [p.some(A1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
    
  def test_some_only_and_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      class A(Thing): equivalent_to = [B & C & D]
      
      class F(Thing): is_a = [p.only(B & C), p.some(B & D)]
      
      class R(Thing): equivalent_to = [p.some(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(F, R)
    
    
  def test_some_only_inverse_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class B(Thing): is_a = [i.only(A)]
      class C(Thing): is_a = [p.some(B)]
      
    rm = self.sync_reasoner()
      
    assert issubclass(C, A)
    
  def test_some_only_inverse_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class Z(Thing): pass
      class B(Thing): is_a = [i.only(A)]
      class C(Thing): is_a = [p.some(B) & Z]

      class R(Thing): equivalent_to = [A & Z]
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_some_only_inverse_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class p1(p): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class B(Thing): is_a = [i.only(A)]
      class C(Thing): is_a = [p1.some(B)]
      
    rm = self.sync_reasoner()
      
    assert issubclass(C, A)
    
  def test_some_only_inverse_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class C(Thing): pass
      class B(Thing): is_a = [i.only(A)]
      class D(Thing): is_a = [p.some(B | C)]
      
      class R(Thing): equivalent_to = [A | p.some(C)]
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  def test_some_only_inverse_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class C(Thing): pass
      class B(Thing): is_a = [i.only(A) | C]
      class D(Thing): is_a = [p.some(B)]
      
      class R(Thing): equivalent_to = [A | p.some(C)]
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  def test_some_only_inverse_or_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class i(ObjectProperty): inverse = p
      class A(Thing): pass
      class C(Thing): pass
      class B(Thing): is_a = [i.only(A) | C]
      class D(Thing): is_a = [p.some(B)]
      
      class R(Thing): equivalent_to = [A | p.some(C)]
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
    
  def test_some_func_1(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class p1(p): pass
      class p2(p): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class M(Thing): is_a = [p1.some(A1), p2.some(A2)]
      class R1(Thing): equivalent_to = [p1.some(A1 & A2)]
      class R2(Thing): equivalent_to = [p2.some(A1 & A2)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R1)
    assert issubclass(M, R2)
    
  def test_some_func_2(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class M(Thing): is_a = [p.some(A1), p.some(A2)]
      class R(Thing): equivalent_to = [p.some(A1 & A2)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_some_func_3(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class M(Thing): is_a = [p.some(A1)]
      class R(Thing): equivalent_to = [p.only(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_some_func_4(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      AllDisjoint([A1, A2])
      
      class M(Thing): is_a = [p.some(A1)]
      
      class R(Thing): equivalent_to = [p.only(Not(A2))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_some_func_5(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      AllDisjoint([A1, A2])
      
      class M(Thing): is_a = [p.some(A)]
      class M1(M):    is_a = [p.some(A1)]
      
      class R(Thing): equivalent_to = [p.only(Not(A2))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M1, R)
    
  def test_some_func_6(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      
      class M(Thing): is_a = [p.some(A1)]
      
      class R(Thing): equivalent_to = [p.only(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_some_func_7(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      
      class M(Thing): pass
      class M1(M): is_a = [p.some(A1)]
      
      class R(Thing): equivalent_to = [p.only(A) & M]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M1, R)
    
  def test_some_func_8(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      
      class M(Thing): pass
      class M1(M): is_a = [p.some(A1) & p.only(B)]
      
      class R(Thing): equivalent_to = [p.only(A1 & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M1, R)
    
    
    
    
  def test_some_func_or_1(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class p1(p): pass
      class p2(p): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class Z(Thing): pass
      class M(Thing): is_a = [p1.some(A1) | Z, p2.some(A2)]
      class R1(Thing): equivalent_to = [p1.some(A1 & A2) | Z]
      class R2(Thing): equivalent_to = [p2.some(A1 & A2) | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R1)
    assert issubclass(M, R2)
    
  def test_some_func_or_2(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class p1(p): pass
      class p2(p): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class Z(Thing): pass
      class M(Thing): is_a = [p1.some(A1), p2.some(A2) | Z]
      class R1(Thing): equivalent_to = [p1.some(A1 & A2) | Z]
      class R2(Thing): equivalent_to = [p2.some(A1 & A2) | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R1)
    assert issubclass(M, R2)

  def test_some_func_or_3(self):
    with self.onto:
      class p(ObjectProperty, FunctionalProperty): pass
      class p1(p): pass
      class p2(p): pass
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class Z1(Thing): pass
      class Z2(Thing): pass
      class M(Thing): is_a = [p1.some(A1) | Z1, p2.some(A2) | Z2]
      class R1(Thing): equivalent_to = [p1.some(A1 & A2) | Z1 | Z2]
      class R2(Thing): equivalent_to = [p2.some(A1 & A2) | Z1 | Z2]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R1)
    assert issubclass(M, R2)

    
  def test_some_func_inverse_1(self):
    with self.onto:
      class s(ObjectProperty, FunctionalProperty): pass
      class inv_s(ObjectProperty): inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(ObjectProperty): inverse = r2
        
      class M(Thing): pass
      class B(Thing): pass
      class A(Thing): pass
      class N(Thing): pass
      
      M.is_a.append(r1.some(N))
      N.is_a.append(r2.some(A))
      M.is_a.append(B)
      A.is_a.append(B)
      
      class R(Thing): equivalent_to = [ inv_r2.some(N) ]
        
    rm = self.sync_reasoner()

    assert issubclass(M, A)
    assert issubclass(M, R)
    assert self.nb_inferences == 2
    
  def test_some_func_inverse_2(self):
    with self.onto:
      class s(ObjectProperty, FunctionalProperty): pass
      class inv_s(ObjectProperty): inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(ObjectProperty): inverse = r2
        
      class M(Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class N1(Thing): pass
      class N2(Thing): pass

      M .is_a.append(r1.some(N1))
      N1.is_a.append(r2.some(N2 & A))
      M .is_a.append(B)
      class inter(Thing):
        equivalent_to = [N2 & A]
        is_a          = [B]
      
      class R(Thing): equivalent_to = [ inv_r2.some(N1) ]
        
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    assert issubclass(M, inter)

  def test_some_func_inverse_or_1(self):
    with self.onto:
      class s(ObjectProperty, FunctionalProperty): pass
      class inv_s(ObjectProperty): inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(ObjectProperty): inverse = r2
        
      class M(Thing): pass
      class B(Thing): pass
      class A(Thing): pass
      class N(Thing): pass
      class Z(Thing): pass
      
      M.is_a.append(r1.some(N) | Z)
      N.is_a.append(r2.some(A))
      M.is_a.append(B)
      A.is_a.append(B)
      
      class R1(Thing): equivalent_to = [ A | Z]
      class R2(Thing): equivalent_to = [ inv_r2.some(N) | Z]
        
    rm = self.sync_reasoner()

    assert issubclass(M, R1)
    assert issubclass(M, R2)
        
  def test_some_func_inverse_or_2(self):
    with self.onto:
      class s(ObjectProperty, FunctionalProperty): pass
      class inv_s(ObjectProperty): inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(ObjectProperty): inverse = r2
        
      class M(Thing): pass
      class B(Thing): pass
      class A(Thing): pass
      class N(Thing): pass
      class Z(Thing): pass
      
      M.is_a.append(r1.some(N))
      N.is_a.append(r2.some(A) | Z)
      M.is_a.append(B)
      A.is_a.append(B)
      
      class R1(Thing): equivalent_to = [ A | Z]
      class R2(Thing): equivalent_to = [ inv_r2.some(N) | Z]
        
    rm = self.sync_reasoner()

    assert issubclass(M, R1)
    assert issubclass(M, R2)
    
  def test_some_func_inverse_or_3(self):
    with self.onto:
      class s(ObjectProperty, FunctionalProperty): pass
      class inv_s(ObjectProperty): inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(ObjectProperty): inverse = r2
        
      class M(Thing): pass
      class B(Thing): pass
      class A(Thing): pass
      class N(Thing): pass
      class Z1(Thing): pass
      class Z2(Thing): pass
      
      M.is_a.append(r1.some(N) | Z1)
      N.is_a.append(r2.some(A) | Z2)
      M.is_a.append(B)
      A.is_a.append(B)
      
      class R1(Thing): equivalent_to = [ A | Z1 | Z2]
      class R2(Thing): equivalent_to = [ inv_r2.some(N) | Z1 | Z2]
        
    rm = self.sync_reasoner()

    assert issubclass(M, R1)
    assert issubclass(M, R2)
        
    
  def test_and_some_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class A1B1(A1, B1): pass
      class C(Thing): is_a = [p.some(A1B1)]
      class R(Thing): equivalent_to = [p.some(A & B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
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
    


  def test_or_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class R(Thing): equivalent_to = [A | B1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A,  R)
    assert issubclass(A1, R)
    assert issubclass(B1, R)

    rm.world.graph.dump()

  def test_or_2(self):
    with self.onto:
      class C(Thing): pass
      class A(C): pass
      class B(C): pass
      class D(Thing): is_a = [A | B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, C)

  def test_or_3(self):
    with self.onto:
      class D(Thing): pass
      class A(D): pass
      class B(D): pass
      class C(D): pass
      class E(Thing): is_a = [A | B | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, D)

  def test_or_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(A): pass
      class C(Thing): is_a = [A1 | B1]
      class R(Thing): equivalent_to = [A | B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)

  def test_or_5(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(A): pass
      class R(Thing): equivalent_to = [A | B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A1, R)
    
    
  def test_and_or_1(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class E(Thing): is_a = [A, (B | C)]
      
      class R (Thing): equivalent_to = [(A & B) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, R)
        
  def test_and_or_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): is_a = [B | C]
      class E(Thing): is_a = [A1, D]
      
      class R (Thing): equivalent_to = [(A & B) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, R)
        
  def test_and_or_3(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): is_a = [B | C]
      class E(Thing): is_a = [D, A1]
      
      class R (Thing): equivalent_to = [(A & B) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, R)

  def test_and_or_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): is_a = [B | C]
      class E(Thing): is_a = [A | C]
      class F(Thing): is_a = [D, E]
      
      class R (Thing): equivalent_to = [(A & B) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(F, R)
        
  def test_and_or_5(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      class G(Thing): is_a = [B | C, A | D]
      
      class R1(Thing): equivalent_to = [(A & B) | C | D]
      class R2(Thing): equivalent_to = [(A & C) | B | D]
      class R3(Thing): equivalent_to = [(A & D) | B | C]
      class R5(Thing): equivalent_to = [(B & D) | A | C]
      class R6(Thing): equivalent_to = [(C & D) | A | B]
      class R7(Thing): equivalent_to = [(B & C) | A | D]
      
    rm = self.sync_reasoner()

    assert issubclass(G, R1)
    assert issubclass(G, R2)
    assert issubclass(G, R3)
    assert issubclass(G, R5)
    assert issubclass(G, R6)
    assert issubclass(G, R7)
    
  def test_and_or_6(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      class G(Thing): is_a = [B | C, A | D]
      
      #class R1(Thing): equivalent_to = [(A & B) | C | D]
      class R1i(Thing): equivalent_to = [A & B]
      class R1(Thing): pass
      R1i.is_a.append(R1)
      C.is_a.append(R1)
      D.is_a.append(R1)
      #class R2(Thing): equivalent_to = [(A & C) | B | D]
      class R2i(Thing): equivalent_to = [A & C]
      class R2(Thing): pass
      R2i.is_a.append(R2)
      B.is_a.append(R2)
      D.is_a.append(R2)
      #class R3(Thing): equivalent_to = [(A & D) | B | C]
      class R3i(Thing): equivalent_to = [A & D]
      class R3(Thing): pass
      R3i.is_a.append(R3)
      B.is_a.append(R3)
      C.is_a.append(R3)
      #class R5(Thing): equivalent_to = [(B & D) | A | C]
      class R5i(Thing): equivalent_to = [B & D]
      class R5(Thing): pass
      R5i.is_a.append(R5)
      A.is_a.append(R5)
      C.is_a.append(R5)
      #class R6(Thing): equivalent_to = [(C & D) | A | B]
      class R6i(Thing): equivalent_to = [C & D]
      class R6(Thing): pass
      R6i.is_a.append(R6)
      A.is_a.append(R6)
      B.is_a.append(R6)
      #class R7(Thing): equivalent_to = [(B & C) | A | D]
      class R7i(Thing): equivalent_to = [B & C]
      class R7(Thing): pass
      R7i.is_a.append(R7)
      A.is_a.append(R7)
      D.is_a.append(R7)
      
    rm = self.sync_reasoner()

    assert issubclass(G, R1)
    assert issubclass(G, R2)
    assert issubclass(G, R3)
    assert issubclass(G, R5)
    assert issubclass(G, R6)
    assert issubclass(G, R7)
    
  def test_and_or_7(self):
    with self.onto:
      class X(Thing): pass
      class Y(Thing): pass
      class Z(Thing): pass
      class A(Thing): is_a = [X | Z]
      class B(Thing): is_a = [Y]
      
      class C(Thing): is_a = [A & B]
      
      class R(Thing): equivalent_to = [(X & Y) | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_and_or_8(self):
    with self.onto:
      class X(Thing): pass
      class Y(Thing): pass
      class Z(Thing): pass
      class A(Thing): is_a = [X | Z]
      class B(Thing): is_a = [Y]
      class C(Thing): pass
      
      class D1(Thing): is_a = [A & B & C]
      class D2(Thing): is_a = [A & C & B]
      class D3(Thing): is_a = [B & C & A]
      
      class R(Thing): equivalent_to = [((X & Y) | Z) & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D1, R)
    assert issubclass(D2, R)
    assert issubclass(D3, R)
    
  def test_and_or_9(self):
    with self.onto:
      class X(Thing): pass
      class W(Thing): pass
      class Y(Thing): pass
      class Z(Thing): pass
      class A(Thing): is_a = [X | Z]
      class B(Thing): is_a = [Y]
      
      class D(Thing): is_a = [W & A & B]
      
      class R(Thing): equivalent_to = [(X & W & Y) | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  def test_and_or_10(self):
    with self.onto:
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      class F(Thing): pass
      
      class E(Thing): is_a = [B, C | F, D]
      
      class A(Thing): equivalent_to = [ B & C & D ]
      class R(Thing): equivalent_to = [(B & C & D) | F]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, R)
    
  def test_and_or_11(self):
    with self.onto:
      class X(Thing): pass
      class X1(X): pass
      class W(Thing): pass
      class Y(Thing): pass
      class Z(Thing): pass
      class A(Thing): is_a = [(X1 | Z), Y]
      
      class R(Thing): equivalent_to = [(X & Y) | Z]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    
  def test_and_or_12(self):
    with self.onto:
      class X(Thing): pass
      class X1(X): pass
      class W(Thing): pass
      class Y(Thing): pass
      class Z1(Thing): pass
      class Z2(Thing): pass
      class A(Thing): is_a = [(X1 | Z1), (Y | Z2)]
      
      class R(Thing): equivalent_to = [(X & Y) | Z1 | Z2]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    
    
  def test_disjoint_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      
      class C(A1, B1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, Nothing)
        
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
    
  def test_disjoint_or_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): pass
      
      class M(Thing): is_a = [A1 | C, B1 | D]
      
      class R(Thing): equivalent_to = [C | D]
      
    self.onto.save("/tmp/t.owl")
    
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_or_3(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class C1(C): pass
      class D(Thing): pass
      class D1(D): pass
      
      class M(Thing): is_a = [A1 | C1, B1 | D1]
      
      class R(Thing): equivalent_to = [C | D]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_or_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [(A1 & B1) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, C)
    
  def test_disjoint_or_5(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1 & (B1 | C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, C)
    
  def test_disjoint_or_6(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): pass
      
      class M(Thing): is_a = [(A1 & (B1 | C)) | D]
      
      class R(Thing): equivalent_to = [C | D]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
    
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
    
  def test_disjoint_and_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1 & B1 & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_disjoint_only_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class M(Thing): is_a = [p.only(A1), p.only(B1)]
      
      class R(Thing): equivalent_to = [p.only(Nothing)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_only_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class M(Thing): is_a = [p.only(A1), p.only(B1 | C)]
      
      class R(Thing): equivalent_to = [p.only(C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_only_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): pass
      class M(Thing): is_a = [p.only(A1 | C), p.only(B1 | D)]
      
      class R(Thing): equivalent_to = [p.only(C | D)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)

    
  def test_not_0(self):
    with self.onto:
      class A(Thing): pass
      class M(Thing): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
  def test_not_1(self):
    with self.onto:
      class A(Thing): pass
      class M(A): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_not_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class C(Thing): is_a = [Not(A)]
      class M(C, A1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
   
  def test_not_3(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class Q (Thing): pass
      class R (Q): equivalent_to = [Not(A )]
      class R1(Q): equivalent_to = [Not(A1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R, R1)
    
  def test_not_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class M(Thing): is_a = [Not(A1), Not(Not(A1))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_not_5(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(B): pass
      
      class R(Thing): equivalent_to = [(A & B) | Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_not_6(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(B): pass
      AllDisjoint([A, B])
      
      class R(Thing): equivalent_to = [Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_not_7(self):
    with self.onto:
      class A(Thing): pass
      class NA(Thing): equivalent_to = [Not(A)]
      class B(Thing): pass
      
      A .is_a.append(B)
      NA.is_a.append(B)
      
    rm = self.sync_reasoner()
    
    assert issubclass(Thing, B)
    
    
    
  def test_long_is_a_1(self):
    with self.onto:
      parents = (Thing,)
      classes = []
      for i in range(200):
        C = types.new_class("C%s" % i, parents)
        classes.append(C)
        parents = (C,)
      
    rm = self.sync_reasoner()
    
  def test_long_and_1(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class AB(A, B): pass
      
      parents = (AB,)
      classes = []
      for i in range(200):
        Cn = types.new_class("C%s" % i, parents)
        classes.append(Cn)
        parents = (Cn,)
        
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(classes[-1], R)
    
  def test_long_and_2(self):
    with self.onto:
      class A(Thing): pass
      parents = (A,)
      classesA = []
      for i in range(200):
        An = types.new_class("A%s" % i, parents)
        classesA.append(An)
        parents = (An,)
        
      class B(Thing): pass
      parents = (B,)
      classesB = []
      for i in range(200):
        Bn = types.new_class("B%s" % i, parents)
        classesB.append(Bn)
        parents = (Bn,)
        
      class AB(classesA[-1], classesB[-1]): pass
      
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, R)
    
  def test_long_and_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(500):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.some(C))
      
      class R(Thing): equivalent_to = [And(ands)]
      class A(Thing):
        is_a = [p.some(C) for C in classes]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    assert self.nb_inferences == 1
    
  def test_long_and_4(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(500):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.only(C))
      
      class R(Thing): equivalent_to = [And(ands)]
      class A(Thing):
        is_a = [p.only(C) for C in classes]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    assert self.nb_inferences == 1
    


  def test_depth(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A2(Thing): pass

      class B(Thing): is_a = [p.some(A)]
      class C(Thing): is_a = [p.some(p.some(A))]
      class D(Thing): is_a = [p.some(B)]
      class R(Thing): equivalent_to = [p.some(A2)]
      class E(Thing): is_a = [p.some(p.some(R))]
      #class F(Thing): pass
      #E.is_a.append(p.some(F))
      #class G(Thing): pass
      #F.equivalent_to.append(p.some(G))
      
    rm = self.sync_reasoner()
    
    assert rm._restriction_depth(B.is_a[-1].storid) == 1
    assert rm._restriction_depth(C.is_a[-1].storid) == 2
    assert rm._restriction_depth(D.is_a[-1].storid) == 1
    assert rm._restriction_depth(E.is_a[-1].storid) == 3
    



  def test_eq_1(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class b(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      
      B.is_a.append(b.some(C))
      
      class E1(Thing):
        equivalent_to = [p.some(A) & p.some(B) & p.some(b.some(C))]
        
      class E2(Thing):
        equivalent_to = [p.some(A) & p.some(B)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    
  def test_eq_2(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class E1(Thing):
        equivalent_to = [p.some(A1) & p.some(B1)]
        
      class E2(Thing):
        equivalent_to = [p.some(A1) & p.some(B1)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    
  def test_eq_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class E1(Thing):
        equivalent_to = [A1 & B1 & A1]
      
      class E2(Thing):
        equivalent_to = [A1 & B1]
      
      class E3(Thing):
        equivalent_to = [p.some(A1) & B1 & p.some(A1)]
        
      class E4(Thing):
        equivalent_to = [p.some(A1) & p.some(A1)]
                
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    


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
    
  def test_concrete_2(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass

      class M(Thing):
        equivalent_to = [A & B1]
        
      m = M()
      
    rm = self.sync_reasoner()
    
    self.assert_concrete(m.storid)
    self.assert_concrete(M.storid)
    self.assert_concrete(A.storid)
    self.assert_not_concrete(A1.storid)
    self.assert_concrete(B.storid)
    self.assert_concrete(B1.storid)
    
  def test_concrete_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B):
        is_a = [p.some(Nothing)]
        
      class M(Thing):
        equivalent_to = [A | B1]
        
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

###################################################################
    
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

  def test_xxx4(self):
    with self.onto:
      for i in range(5):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(6):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      #random.C1.is_a =  [Thing, random.p1.only(random.C1 | random.C3 | random.C2)]
      #random.C2.is_a =  [random.C1]
      #random.C3.is_a =  [random.C1, random.C1 | random.C3 | random.C2, random.p1.only(random.C1 | random.C3 | random.C2), random.p1.some(random.p1.some(random.C4))]
      #random.C4.is_a =  [random.C3, random.p1.some(random.C4), random.p1.some(random.C4)]
      #random.C5.is_a =  [random.C3, random.p1.some(random.p1.some(random.C4))]

      random.C1.is_a =  [random.p1.only(random.C1 | random.C3 | random.C2)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C1,
                         random.C1 | random.C3 | random.C2,
                         random.p1.some(random.p1.some(random.C4)),
      ]
      random.C4.is_a =  [random.C3,
                         random.p1.some(random.C4)]
      

    rm = self.sync_reasoner()
    print(rm.max_restriction_depth)

  def test_xxx5(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(2):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
    
      random.C1.is_a =  [
        random.p1.only(random.C2),
      ]
      random.C2.is_a =  [
        random.C1,
        random.p1.some(random.C2),
        random.p1.only(random.C2) | random.p1.some(random.p1.only(random.C2)) | random.p1.some(random.C1),
      ]
      
    rm = self.sync_reasoner()


  def test_xxx6(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(5):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C3 & random.C2 & random.C1)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C3 | random.C2,
                         random.p1.some(random.C2)]
      
      
    rm = self.sync_reasoner()
    print(rm._restriction_depth())
    
    
  def test_xxx7complet(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(5):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C5 & random.C2 & random.C3)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C2]
      random.C4.is_a =  [random.C2]
      random.C5.is_a =  [random.C2,
                         random.C3 | random.C4,
                         random.p1.some(random.C2)]
      
    rm = self.sync_reasoner()
    
  def test_xxx7(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  []
      random.C2.is_a =  [random.C1, random.p1.only(random.C2 & random.C3 & random.C4)]
      random.C3.is_a =  []
      random.C4.is_a =  [random.C2 | random.C3,   random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()
    
    
  def test_xxx7simp(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      class C(Thing): pass
      
      random = self.onto
      
      C.is_a = [random.C2, random.C3, random.C4]
      #C.is_a = [random.C2 & random.C3 & random.C4]
      
      random.C1.is_a =  []
      random.C2.is_a =  [random.C1, random.p1.only(C)]
      random.C3.is_a =  []
      random.C4.is_a =  [random.C2 | random.C3,   random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()

    
  def test_test1(self):
    with self.onto:
      class p(ObjectProperty): pass
      
      class A(Thing): pass
      class B(Thing): pass
      
      class Z(Thing): pass
      
      class X(Thing):
        is_a = [
          p.only(A) | Z,
          p.only(B),
          ]
        
      class R1(Thing): equivalent_to = [(p.only(A) & p.only(B)) | Z]
      #class XXX(Thing): is_a = [p.only(A) & p.only(B)]
        
      class R2(Thing): equivalent_to = [p.only(A & B) | Z]
        
    self.onto.save("/tmp/t.owl")
    rm = self.sync_reasoner()
    print(X.is_a)

    
  def test_test2(self):
    with self.onto:
      class p(ObjectProperty): pass
      
      class A(Thing): pass
      class B(Thing): pass
      
      class Z(Thing): pass
      
      class X(Thing):
        is_a = [
          p.only(A | Z),
          p.only(B),
          ]
        
      class R1(Thing):
        equivalent_to = [p.only((A & B) | Z)]
        
    self.onto.save("/tmp/t.owl")
    rm = self.sync_reasoner()
    print(X.is_a)

    

if __name__ == '__main__': unittest.main()
