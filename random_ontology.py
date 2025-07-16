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

import sys, os, random, types

from owlready2 import *


# def create_random(iri = "http://test.org/random.owl", nb_class = 100, nb_is_a = None, nb_prop = None, nb_prop_is_a = None, nb_some = None, nb_only = None, nb_and = None, nb_or = None, nb_not = None, seed = None, world = default_world):
#   if nb_is_a is      None: nb_is_a      = nb_class * 2
#   if nb_some is      None: nb_some      = nb_class // 2
#   if nb_only is      None: nb_only      = nb_class // 5
#   if nb_prop is      None: nb_prop      = 5 + nb_class // 50
#   if nb_prop_is_a is None: nb_prop_is_a = nb_prop // 2
#   if nb_and  is      None: nb_and       = nb_class // 5
#   if nb_or   is      None: nb_or        = nb_class // 20
#   if nb_not  is      None: nb_not       = nb_class // 40
  
#   r = random.Random(seed)

#   onto = world.get_ontology(iri)
  
#   with onto:
#     props = []
#     for i in range(nb_prop):
#       C = types.new_class("p%s" % (i+1), (ObjectProperty,))
#       props.append(C)
      
#     i = 0
#     while i < nb_prop_is_a:
#       a = r.choice(props)
#       b = r.choice(props)
#       if a is b: continue
#       if issubclass(b, a): continue
#       if issubclass(a, b): continue
#       a.is_a.append(b)
#       if ObjectProperty in a.is_a: a.is_a.remove(ObjectProperty)
#       i += 1

#     prios = {}
      
#     atomic_classes = []
#     unary_classes  = []
#     classes        = []
#     for i in range(nb_class):
#       C = types.new_class("C%s" % (i+1), (Thing,))
#       prios[C] = i + 1
#       atomic_classes.append(C)
#       classes       .append(C)
#       unary_classes .append(C)
      
#     construct_types = ["some"] * nb_some + ["only"] * nb_only + ["or"] * nb_or + ["and"] * nb_and + ["not"] * nb_not
#     r.shuffle(construct_types)
    
#     constructs = []
#     for construct_type in construct_types:
#       if   construct_type == "some":
#         c = r.choice(props).some(r.choice(atomic_classes))
#         unary_classes.append(c)
#         classes.append(c)
        
#       elif construct_type == "only":
#         c = r.choice(props).only(r.choice(atomic_classes))
#         unary_classes.append(c)
#         classes.append(c)
        
#       elif construct_type == "and":
#         nb = r.randint(2,10)
#         c = And(list(set(r.choice(classes) for i in range(nb))))
#         prios[c] = max((prios[x] for x in c.Classes if x in prios), default = 0)
#         classes.append(c)
        
        
#     i = 0
#     for j in range(2 * nb_is_a):
#       b = r.choice(classes)
#       a_candidates = atomic_classes[prios.get(b, 0):]
#       if not a_candidates: continue
#       a = r.choice(a_candidates)
      
#       if a is b: continue
#       if _is_a(b, a): continue
#       if _is_a(a, b): continue
#       if isinstance(b, And):
#         a.equivalent_to.append(b)
#       else:
#         a.is_a.append(b)
#       if Thing in a.is_a: a.is_a.remove(Thing)
#       i += 1
#       if i >= nb_is_a: break
      
#   return onto

def create_random(iri = "http://test.org/random.owl", nb_class = 100, nb_is_a = None, nb_prop = None, nb_prop_is_a = None, nb_some = None, nb_only = None, nb_and = None, nb_or = None, nb_not = None, seed = None, world = default_world):
  if nb_is_a is      None: nb_is_a      = nb_class * 3
  if nb_some is      None: nb_some      = nb_class // 2
  if nb_only is      None: nb_only      = nb_class // 5
  if nb_prop is      None: nb_prop      = 5 + nb_class // 50
  if nb_prop_is_a is None: nb_prop_is_a = nb_prop // 2
  if nb_and  is      None: nb_and       = 2 + nb_class // 10
  if nb_or   is      None: nb_or        = nb_class // 20
  if nb_not  is      None: nb_not       = nb_class // 40
  
  r = random.Random(seed)

  onto = world.get_ontology(iri)
  
  with onto:
    props = []
    for i in range(nb_prop):
      C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      props.append(C)
      
    i = 0
    while i < nb_prop_is_a:
      a = r.choice(props)
      b = r.choice(props)
      if a is b: continue
      if issubclass(b, a): continue
      if issubclass(a, b): continue
      a.is_a.append(b)
      if ObjectProperty in a.is_a: a.is_a.remove(ObjectProperty)
      i += 1

    atomic_classes = []
    unary_classes  = []
    classes        = []
    r_classes      = []
    constructs     = []
    
    to_creates = ["class"] * (nb_class - 1) + ["some"] * nb_some + ["only"] * nb_only + ["or"] * nb_or + ["and"] * nb_and + ["not"] * nb_not
    r.shuffle(to_creates)
    to_creates.insert(0, "class")

    class_ci = class_ri = 1
    for to_create in to_creates:
      if atomic_classes:
        parent = r.choice(atomic_classes)
      else:
        parent = None
        
      if   to_create == "class":
        C = c = types.new_class("C%s" % (class_ci), (parent or Thing,))
        class_ci += 1
        atomic_classes.append(c)
        classes       .append(c)
        unary_classes .append(c)
        
      elif to_create == "some":
        c = r.choice(props).some(r.choice(classes))
        parent.is_a.append(c)
        unary_classes.append(c)
        classes.append(c)
        C.is_a.append(c)
        
      elif to_create == "only":
        c = r.choice(props).only(r.choice(classes))
        parent.is_a.append(c)
        unary_classes.append(c)
        classes.append(c)
        C.is_a.append(c)
        
      elif to_create == "and":
        nb = r.randint(2, 8)
        l = set()
        for i in range(nb):
          x = r.choice(classes)
          if isinstance(x, And): continue
          l.add(x)
        c = And(list(l))
        classes.append(c)

        #R = types.new_class("R%s" % (class_ri), (Thing,))
        #class_ri += 1
        #R.equivalent_to.append(c)
        #r_classes.append(R)
        
      elif to_create == "or":
        nb = r.randint(2, 6)
        l = set()
        for i in range(nb):
          x = r.choice(classes)
          if isinstance(x, Or): continue
          l.add(x)
        c = Or(list(l))
        C.is_a.append(c)
        classes.append(c)

  if '-o' in sys.argv:
    print()
    for p in props:
      if p.is_a == [ObjectProperty]: print("      random.%s" % p.name)
      else:                          print("      random.%s.is_a = " % p.name, p.is_a)
    for c in atomic_classes:
      if p.is_a == [Thing]: print("      random.%s" % c.name)
      else:                 print("      random.%s.is_a = " % c.name, repr(c.is_a).replace("owl.", ""))
    for c in r_classes:
      print("      random.%s.equivalent_to = " % c.name, c.equivalent_to)
    print()
    
    sys.exit()
    
  return onto

def _is_a(a, b):
  if isinstance(b, ThingClass) and issubclass(a, b): return True
  if isinstance(b, And):
    #print("!!!!", a, b)
    for b1 in b.Classes:
      if _is_a(a, b1):
        #print("    !!!!", a, b1)
        return True
      
def run_semantic2sql(onto):
  import time
  from semantic2sql.reasoned_model import ReasonedModel

  onto_inference = get_ontology("http://test.org/inferrences.owl")

  rm = ReasonedModel(default_world, debug = 0)
  
  t = time.time()
  
  with onto_inference:
    rm.run()
    rm.print_rule_usage()

  t = time.time() - t
  print(t)
  return t


seed = 11

if "-s" in sys.argv:
  seed = int(sys.argv[sys.argv.index("-s") + 1])
  
#onto = create_random(nb_class = 10, nb_and = 3, nb_or = 1, seed = 67)
#onto = create_random(nb_class = 6, nb_prop = 1, nb_prop_is_a = 0, nb_and = 2, nb_or = 1, seed = seed)
#onto = create_random(nb_class = 5, nb_prop = 1, nb_prop_is_a = 0, nb_and = 2, nb_or = 1, seed = seed)
onto = create_random(nb_class = 5, nb_prop = 1, nb_prop_is_a = 0, nb_and = 1, nb_or = 1, seed = seed)
onto.save("/tmp/t.owl")
print(".")

if   "-h" in sys.argv:
  sync_reasoner()

elif "-l" in sys.argv:
  seed = 0
  while 1:
    world = World()
    cmd = "python ./semantic2sql/random_ontology.py -s %s" % seed
    print(cmd)
    
    t = time.time()
    os.system(cmd)
    t = time.time() - t
    if t > 0.5:
      print("SEED", seed)
      break
    seed += 1
    time.sleep(0.1)
    
else:
  run_semantic2sql(onto)
