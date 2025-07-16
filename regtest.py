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

from owlready2 import *
import sys, os, unittest, tempfile, atexit, types

from semantic2sql.reasoned_model import *

if "--keep" in sys.argv:
  sys.argv.remove("--keep")
  KEEP = True
else:
  KEEP = False

if "--dump" in sys.argv:
  sys.argv.remove("--dump")
  DUMP = True
else:
  DUMP = False

if "-r" in sys.argv:
  i = sys.argv.index("-r")
  FORCED_RULES_FILE = "rules_%s.txt" % sys.argv[i+1]
  del sys.argv[i+1]
  del sys.argv[i]
else:
  FORCED_RULES_FILE = None


RULES_FILE = "rules.txt"

def rules_files(*files):
  def f(func, files = files):
    func._rules_files = files
    return func
  return f

def finalize_test_class(Test):
  for k, v in list(Test.__dict__.items()):
    if hasattr(v, "_rules_files"):
      delattr(Test, k)
      for rules_file in v._rules_files:
        def new_v(self, v = v, rules_file = rules_file):
          global RULES_FILE
          if   FORCED_RULES_FILE: RULES_FILE = FORCED_RULES_FILE
          elif rules_file:        RULES_FILE = "rules_%s.txt" % rules_file
          else:                   RULES_FILE = "rules.txt"
          v(self)
        if rules_file: setattr(Test, "%s_%s" % (k, rules_file), new_v)
        else:          setattr(Test, k, new_v)
        
        
class Test(unittest.TestCase):
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
    if KEEP:
      self.world.save()
      
  def sync_reasoner(self, consistent = True):
    rm = self.rm = ReasonedModel(self.world, rule_set = RULES_FILE, temporary = not KEEP, debug = True)
    onto_inference = self.world.get_ontology("http://test.org/inferrences_%s.owl" % self._next_onto)
    self._next_onto += 1
    
    with onto_inference:
      if consistent:
        rm.run()
      else:
        ok = False
        try:
          rm.run()
        except OwlReadyInconsistentOntologyError:
          ok = True
        assert ok
        
    self.nb_inferences = len(onto_inference.graph) - 1
    
    if DUMP:
      rm.dump_inferences()
      print()
      print("  => Inferences:")
      onto_inference.graph.dump()
    return rm

  def assert_isa(self, s, o):
    r = self.rm.cursor.execute("SELECT 1 FROM isa WHERE s=? AND o=?""", (s, o)).fetchone()
    assert not r is None

  @rules_files("")
  def test_1(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class O(Thing): pass
      class R(Thing): equivalent_to = [p.some(A)]
      o = O()
      o.p = [A(), B()]
      
    rm = self.sync_reasoner()
    
    assert set(o.is_a) == set([O, R])
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_2(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class O(Thing): pass
      class R(Thing): equivalent_to = [p.some(A)]
      o = O()
      o.p = [A1(), B()]
      
    rm = self.sync_reasoner()
    
    assert set(o.is_a) == set([O, R])
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class O(Thing): pass
      class R1(Thing): equivalent_to = [p.some(A)]
      class R2(Thing): equivalent_to = [p.some(B)]
      o = O()
      o.p = [A(), B()]
      
    rm = self.sync_reasoner()
    
    assert set(o.is_a) == set([O, R1, R2])
    assert self.nb_inferences == 2
    
  @rules_files("")
  def test_4(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      AllDisjoint([A, B])
      class O(A, B): pass
      
    rm = self.sync_reasoner()
    
    assert Nothing in O.is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_5(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      AllDisjoint([A, B])
      o = A()
      o.is_a.append(B)
      
    rm = self.sync_reasoner(consistent = False)
    
    assert self.nb_inferences == 0
    
  @rules_files("", "elh", "horn_shiq", "horn_shiq_simplifie")
  def test_6(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class R(Thing): equivalent_to = [p.some(A) & p.some(B)]
      class O(Thing):
        is_a = [p.some(A), p.some(B)]
      
    rm = self.sync_reasoner()
    
    assert R in O .is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_7(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class R(Thing): equivalent_to = [p.some(A) & p.some(B)]
      t1 = Thing("t1")
      t1.p = [A(), B()]
      
    rm = self.sync_reasoner()
    
    assert R in t1.is_a
    assert self.nb_inferences == 1
    
  @rules_files("", "elh", "horn_shiq", "horn_shiq_simplifie")
  def test_8(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(100):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = p.some(classes[0])
      for C in classes[1:]: ands = ands & p.some(C)
      
      class R(Thing): equivalent_to = [ands]
      class O(Thing):
        is_a = [p.some(C) for C in classes]
        
    rm = self.sync_reasoner()
    
    assert R in O.is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_9(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(100):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = p.some(classes[0])
      for C in classes[1:]: ands = ands & p.some(C)
      
      class R(Thing): equivalent_to = [ands]
      o1 = Thing()
      o1.p = [C() for C in classes]
      
    rm = self.sync_reasoner()
    
    assert R in o1.is_a
    assert self.nb_inferences == 1
    
  @rules_files("", "elh", "horn_shiq", "horn_shiq_simplifie")
  def test_10(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(20):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.some(C))
      ands = And(ands)
      
      class R(Thing): equivalent_to = [ands]
      class O(Thing):
        is_a = [p.some(C) for C in classes]
      
    rm = self.sync_reasoner()
    
    assert R in O.is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_11(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(20):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.some(C))
      ands = And(ands)
      
      class R(Thing): equivalent_to = [ands]
      o1 = Thing()
      o1.p = [C() for C in classes]
      
    rm = self.sync_reasoner()
    
    assert R in o1.is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_12(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class p(A >> B): pass
      
      b = Thing()
      a = Thing(p = [b])
      
    rm = self.sync_reasoner()
    
    assert A in a.is_a
    assert B in b.is_a
    assert self.nb_inferences == 2
    
  @rules_files("", "horn_shiq", "horn_shiq_simplifie")
  def test_13(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class C2(C): pass
      
      class A(Thing):
        is_a = [p.some(B), p.only(C2)]
        
      class R(Thing):
        equivalent_to = [p.some(C)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_14(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class D(Thing):
        is_a = [p.only(A)]
      class E(Thing):
        is_a = [p.only(B)]
      class F(D, E):
        is_a = [p.some(C)]
      
    rm = self.sync_reasoner()
    
    assert Nothing in F.is_a
    assert self.nb_inferences == 1
    
  @rules_files("")
  def test_15(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A2(A): pass
      class B(Thing):
        is_a = [p.some(A), p.only(A)]
      class C(Thing):
        is_a = [p.some(A2), p.only(A)]
        
    rm = self.sync_reasoner()
    
    assert rm.rule_set.name_2_rule["some_only"].total_triples == 0
    assert self.nb_inferences == 0
    
  @rules_files("", "elh", "horn_shiq", "horn_shiq_simplifie")
  def test_16(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      A.is_a.append(p.some(B))
      B.is_a.append(C)
      D.equivalent_to.append(p.some(C))
      
    rm = self.sync_reasoner()
    
    assert issubclass(A, D)
    assert self.nb_inferences == 1
    
  @rules_files("", "elh", "horn_shiq", "horn_shiq_simplifie")
  def test_17(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class q(p): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      A.is_a.append(q.some(B))
      B.is_a.append(C)
      D.equivalent_to.append(p.some(C))
      
    rm = self.sync_reasoner()

    assert issubclass(A, D)
    assert self.nb_inferences == 1
    
  @rules_files("elh")
  def test_elh_R2(self):
    with self.onto:
      class B(Thing): pass
      class C(Thing): pass
      class A(B, C): pass
      class D(Thing): pass        
      class R(D):
        equivalent_to = [B & C]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, D)
    assert self.nb_inferences == 3

  @rules_files("elh")
  def test_elh_R3(self):
    with self.onto:
      class r(Thing >> Thing): pass
      
      class C(Thing): pass
      class B(Thing):
        is_a = [r.some(C)]
      class A(B): pass
      
    rm = self.sync_reasoner()

    self.assert_isa(A.storid, B.is_a[1].storid)
    assert self.nb_inferences == 0
    
  @rules_files("elh")
  def test_elh_R4(self):
    with self.onto:
      class s(Thing >> Thing): pass
      class r(s): pass
      
      class B(Thing): pass
      class A(Thing):
        is_a = [r.some(B)]
        
      class R(Thing):
        equivalent_to = [s.some(B)]
        
    rm = self.sync_reasoner()

    assert issubclass(A, R)
    assert self.nb_inferences == 1

  @rules_files("elh")
  def test_elh_R5(self):
    with self.onto:
      class r(Thing >> Thing): pass
      
      class C(Thing): pass
      class B(C): pass
      class A(Thing):
        is_a = [r.some(B)]
        
      class D(Thing):
        equivalent_to = [r.some(C)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, D)
    assert self.nb_inferences == 1
    
    
    
  @rules_files("horn_shiq", "horn_shiq_simplifie")
  def test_shiq_R5(self):
    with self.onto:
      class s(Thing >> Thing): pass
      class r1(s): pass
      class r2(s): pass
      
      class B(Thing): pass
      class N1(B): pass
      class N2(B): pass
      class M(Thing):
        is_a = [
          r1.some(N1),
          r2.some(N2),
          s.max(1, B),
          ]
        
      class R(Thing):
        equivalent_to = [
          r1.some(N1 & N2),
          ]
      
    rm = self.sync_reasoner()

    assert R in M.is_a
    assert self.nb_inferences == 1
    
  @rules_files("horn_shiq", "horn_shiq_simplifie")
  def test_shiq_R6(self):
    with self.onto:
      class s(Thing >> Thing): pass
      class inv_s(Thing >> Thing):
        inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(Thing >> Thing):
        inverse = r2
        
      class M(Thing): pass
      class B(Thing): pass
      class A(Thing): pass
      class N(Thing): pass
      
      M.is_a.append(r1.some(N))
      N.is_a.append(r2.some(A))
      M.is_a.append(B)
      A.is_a.append(B)
      N.is_a.append(s.max(1, B))
      
      class R(Thing):
        equivalent_to = [
          inv_r2.some(N),
        ]
        
    rm = self.sync_reasoner()

    assert R in M.is_a
    assert A in M.is_a
    assert self.nb_inferences == 2
    
  @rules_files("horn_shiq", "horn_shiq_simplifie")
  def test_shiq_R6_2(self):
    with self.onto:
      class s(Thing >> Thing): pass
      class inv_s(Thing >> Thing):
        inverse = s
      class r1(inv_s): pass
      class r2(s): pass
      class inv_r2(Thing >> Thing):
        inverse = r2
        
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
      N1.is_a.append(s.max(1, B))
      
      class R(Thing):
        equivalent_to = [
          inv_r2.some(N1),
        ]
        
    rm = self.sync_reasoner()
    
    assert R in M.is_a
    assert inter in M.is_a
    assert self.nb_inferences == 4
    

  @rules_files("alch")
  def test_some_only_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      A.is_a.append(p.some(B))
      A.is_a.append(p.only(C))
      
      class R(Thing): equivalent_to = [p.some(C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)

  @rules_files("alch")
  def test_some_only_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      A.is_a.append(p.some(B))
      A.is_a.append(p.only(C))
      
      class R(Thing): equivalent_to = [p.some(B & C) | D]

    rm = self.sync_reasoner()
    
    assert issubclass(A, R)

  @rules_files("alch")
  def test_some_only_or_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      A.is_a.append(p.some(B) | D)
      A.is_a.append(p.only(C))
      
      class R(Thing): equivalent_to = [p.some(B & C) | D]
      
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)

  @rules_files("alch")
  def test_some_only_or_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class H1(Thing): pass
      class H2(Thing): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      H1.is_a.append(p.some(A) | B)
      H2.is_a.append(p.only(C) | D)
      
      #class R(Thing): equivalent_to = [p.some(B & C) | D]

    self.onto.save("/tmp/t.owl")
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)

  @rules_files("", "alch")
  def test_and_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(A, B):  pass
      class R(Thing): equivalent_to = [A & B]

    rm = self.sync_reasoner()
    
    assert issubclass(C, R)

  @rules_files("", "alch")
  def test_and_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing):  pass
      class D(Thing):  is_a = [A, B | C]
      class R(Thing): equivalent_to = [A & (B | C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  @rules_files("", "alch")
  def test_and_or_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(A, B, C):  pass
      class R(Thing): equivalent_to = [A & B & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, R)
    
  @rules_files("", "alch")
  def test_and_or_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing):  pass
      class D(Thing):  pass
      class E(Thing):  is_a = [A, B, C | D]
      class R(Thing): equivalent_to = [A & B & (C | D)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, R)
    

    
  @rules_files("", "alch")
  def test_or_1(self):
    with self.onto:
      class A(Thing): pass
      class U(Thing): is_a = [ A | Nothing ]
      
    rm = self.sync_reasoner()
    
    assert issubclass(U, A)
    
  @rules_files("", "alch")
  def test_or_2(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      AllDisjoint([A, C])
      AllDisjoint([A, D])
      AllDisjoint([B, C])
      AllDisjoint([B, D])
      class O(Thing): is_a = [(A&C) | (A&D) | (B&C) | (B&D)]
      #class O(Thing): is_a = [(A&C) | (A&D) | (B&C)]
      #class O(Thing): is_a = [(A&C) | (B&C)]
      #class O(Thing): is_a = [A&C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(O, Nothing)

  @rules_files("", "alch")
  def test_or_3(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      AllDisjoint([A, C, D])
      AllDisjoint([B, C])
      
      class U(Thing): is_a = [ A | B ]
      class O(U, C): pass

    rm = self.sync_reasoner()
    
    assert issubclass(O, Nothing)
    
  @rules_files("", "alch")
  def test_or_4(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(Thing): pass
      class D(Thing): pass
      AllDisjoint([A, C])
      AllDisjoint([A, D])
      AllDisjoint([B, C])
      AllDisjoint([B, D])
      class U1(Thing): is_a = [ A | B ]
      class U2(Thing): is_a = [ C | D ]
      class O(U1, U2): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(O, Nothing)
    
  @rules_files("", "alch")
  def test_or_5(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class A2(A): pass
      class U(Thing): is_a = [ A1 | A2 ]
      
    rm = self.sync_reasoner()
    
    assert issubclass(U, A)
    
  @rules_files("", "alch")
  def test_is_a_some_or(self):
    with self.onto:
      class p(ObjectProperty): pass
      class B(Thing): pass
      class N(Thing): pass
      class A(Thing): is_a = [p.some(B)]
      class H(Thing): is_a = [N | A]
      
      class R(Thing): equivalent_to = [N | p.some(B)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(H, R)

  @rules_files("", "alch")
  def test_some_nothing_or(self):
    with self.onto:
      class p(ObjectProperty): pass
      class K(Thing): is_a = [Nothing]
      class M(Thing): pass
      class H(Thing): is_a = [M | p.some(K)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(H, M)
    
    
  @rules_files("", "alch")
  def test_long_is_a_chain(self):
    with self.onto:
      parent = Thing
      classes = []
      for i in range(200):
        C = types.new_class("C%s" % i, (parent,))
        classes.append(C)
        parent = C
        
    rm = self.sync_reasoner()
    
  @rules_files("", "alch")
  def test_long_is_a_chain_with_and(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      parents = (A, B)
      classes = []
      for i in range(40):
        C = types.new_class("C%s" % i, parents)
        classes.append(C)
        parents = (C,)
        
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    
  @rules_files("")
  def test_X(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class C(A1): pass
      class C1(C, B1): pass
      class C2(C1): pass
      class C3(C2): pass

      parents = (C3,)
      for i in range(500):
        Cn = types.new_class("C%s" % (i + 4), parents)
        parents = (Cn,)
        
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C1, R)
    assert issubclass(C2, R)
    assert issubclass(C3, R)
    
    
finalize_test_class(Test)


if __name__ == '__main__': unittest.main()
