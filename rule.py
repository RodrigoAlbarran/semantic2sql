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
import sys
sys.path.append("./")
import os.path
from collections import defaultdict, Counter
from owlready2 import *
from semantic2sql.pattern import *
from semantic2sql.rule_parser import *

#SQUASHED_LIST_PROPS = {owl_unionof, owl_intersectionof, owl_oneof, owl_members, owl_distinctmembers}
#CONSTRUCT_PROPS = {rdfs_subclassof, owl_unionof, owl_intersectionof, owl_oneof, owl_complementof, owl_inverse_property, SOME, VALUE, ONLY, EXACTLY, MIN, MAX, owl_onproperty, owl_onclass, owl_ondatarange, owl_withrestrictions}
#NON_INFERRABLE_TYPES = { owl_restriction, owl_alldisjointclasses, owl_alldifferent, owl_alldisjointproperties }

_RESTRICTION_TABLES = { "some", "only", "exactly" }

SHOW_NEW_CONSTRUCTS = False
SHOW_NEW_CONSTRUCTS = True


class Table(object):
  def __init__(self, rule_set, name, columns, list = None, search_name = "", is_a_thing = False):
    self.rule_set         = rule_set
    self.name             = name
    self.search_name      = search_name or name
    self.columns          = columns
    self.list             = list
    self.is_a_thing       = is_a_thing
    rule_set.tables[name] = self
    
  def __repr__(self): return "<Table '%s'>" % self.name
  
  def add(self, model, cursor, added_nb_inferences, var_2_value, sql_insert):
    if sql_insert.has_non_condition_var:
      selects  = []
      new_vars = []
      wheres   = []
      values   = []
      for column, x in zip(self.columns, sql_insert.xs):
        if isinstance(x, Variable):
          if x in var_2_value:
            wheres.append(column)
            values.append(var_2_value[x])
          else:
            selects .append(column)
            new_vars.append(x)
        else:
          wheres.append(column)
          values.append(x)
          
      sql = ("""SELECT %s FROM %s WHERE %s LIMIT 1""" % (",".join(selects), self.search_name, " AND ".join("%s=?" % where for where in wheres)))
      new_values = cursor.execute(sql, values).fetchone()
      if new_values:
        for new_var, new_value in zip(new_vars, new_values): var_2_value[new_var] = new_value
        return True
      
      #if s:
      #  var_2_value[new_vars[0]] = s
      #  del new_vars[0]
        
    else:
      new_vars = [x for x in sql_insert.xs if isinstance(x, Variable) and (not x in var_2_value)]
      
    if not self.check_new(model, sql_insert, var_2_value):
      return False 
    
    for new_var in new_vars: var_2_value[new_var] = model.new_blank_node()
    
    values = []
    for column, x in zip(self.columns, sql_insert.xs):
      if isinstance(x, Variable): values.append(var_2_value[x])
      else:                       values.append(int(x))
      
    sql = """INSERT OR IGNORE INTO %s VALUES (%s)""" % (self.name, ",".join("?" for i in range(len(self.columns))))
    cursor.execute(sql, values)
    added_nb_inferences[self] += cursor.rowcount
    
    if SHOW_NEW_CONSTRUCTS and self.name != "is_a":
      print()
      print(values[0], ":", model._get_constructs()[values[0]])
      
    return True
  
    #if cursor.rowcount:
    #  if self.is_a_thing:
    #    s = values[0]
    #    cursor.executemany("""INSERT INTO is_a VALUES (?,?,2)""", [(s, s), (s, owl_thing)])
    #    added_nb_inferences[self.rule_set.tables["is_a"]] += cursor.rowcount
    #  return 1
    #else: return 0

  def check_new(self, model, sql_insert, var_2_value): return True
  
class ObjectRestrictionTable(Table):
  def check_new(self, model, sql_insert, var_2_value):
    depth = model._restriction_depth(var_2_value[sql_insert.xs[-1]]) + 1
    return model.check_restriction_depth(depth)

  def add(self, model, cursor, added_nb_inferences, var_2_value, sql_insert):
    r = Table.add(self, model, cursor, added_nb_inferences, var_2_value, sql_insert)
    if r:
      s = var_2_value[sql_insert.xs[0]]
      cursor.execute("""INSERT OR IGNORE INTO infer_ancestors VALUES (?)""", (s,))      
      added_nb_inferences[model.rule_set.tables["infer_ancestors"]] += cursor.rowcount
    return r
  
class List(object):
  def __init__(self, rel):
    self.rel    = rel
    self.flat   = None
    self.key    = None
    self.linked = None
    self.is_a_thing = rel in (owl_intersectionof, owl_unionof, owl_complementof)
    
  def add(self, model, cursor, added_nb_inferences, elements0, s = None):
    #print("\n  ADD ", self.rel, elements0, s)
    r = model._list_cache[self].get(elements0)
    if r: return r
    
    elements = set(elements0)
    assert isinstance(elements, set) or isinstance(elements, frozenset)
    
    if not s:
      if   (self.rel == owl_intersectionof) or (self.rel == owl_unionof):
        # Deal with Thing/Nothing
        elements.discard(owl_thing)
        if owl_nothing in elements:
          if self.rel == owl_intersectionof:
            model._increment_extra("Intersection including nothing")
            model._list_cache[self][elements0] = owl_nothing
            return owl_nothing
          else:
            model._increment_extra("Non-intersection including nothing")
            elements.discard(owl_nothing)
            
        # Avoid A and/or B with B is a A
        elements_copy = list(elements)
        removeds = set()
        #for e1 in elements_copy:
        #  for e2 in elements_copy:
        #    if (e1 == e2) or (e1 in removeds) or (e2 in removeds): continue
        #    r = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, e2)).fetchone()
        #    if r:
        #      if self.rel == owl_intersectionof: elements.discard(e2); removeds.add(e2)
        #      else:                              elements.discard(e1); removeds.add(e1)
        #      model._increment_extra("A and/or B with B is a A")
        #      break

        if self.rel == owl_intersectionof:
          for e1 in elements_copy:
            for e2 in elements_copy:
              if (e1 == e2) or (e1 in removeds) or (e2 in removeds): continue
              r = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, e2)).fetchone()
              if r:
                elements.discard(e2); removeds.add(e2)
                model._increment_extra("A and B with B is a A")
                break
        else:
          def get_s_extra_is_a(e):
            r1 = cursor.execute("""SELECT o1, o2 FROM linked_lists_31 WHERE s=? LIMIT 1""", (e,)).fetchone()
            if not r1: return []
            r2 = cursor.execute("""SELECT 1 FROM flat_lists_31 WHERE s=? LIMIT 1""", (e,)).fetchone()
            if r2: return [] # Is-a relations are computed for s in flat_lists

            r = []
            r10 = get_s_extra_is_a(r1[0])
            if r10: r.extend(r10)
            else:   r.append(r1[0])
            r11 = get_s_extra_is_a(r1[1])
            if r11: r.extend(r11)
            else:   r.append(r1[1])
            return r
            
          e_2_extra_is_a = {}
          for e in elements:
            #r = cursor.execute("""SELECT o1, o2 FROM linked_lists_31 WHERE s=? LIMIT 1""", (e,)).fetchone()
            #e_2_extra_is_a[e] = r or ()
            e_2_extra_is_a[e] = get_s_extra_is_a(e)

          #print()
          for e1 in elements_copy:
            for e2 in elements_copy:
              if (e1 == e2) or (e1 in removeds) or (e2 in removeds): continue
              e1_extra_is_a = e_2_extra_is_a[e1]
              e2_extra_is_a = e_2_extra_is_a[e2]
              
              r = (e2 in e1_extra_is_a) or cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, e2)).fetchone()
              
              if not r:
                #print("!!!", e1, e1_extra_is_a, "  ", e2, e2_extra_is_a)
                if   e1_extra_is_a and not e2_extra_is_a:
                  for extra_is_a1 in e1_extra_is_a:
                    r2 = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (extra_is_a1, e2)).fetchone()
                    if r2:
                      r = True
                      break
                    
                elif e2_extra_is_a and not e1_extra_is_a:
                  for extra_is_a2 in e2_extra_is_a:
                    r2 = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, extra_is_a2)).fetchone()
                    if not r2: break
                  else:
                    r = True
                    
                elif e2_extra_is_a and e1_extra_is_a:
                  r = True
                  for extra_is_a2 in e2_extra_is_a:
                    for extra_is_a1 in e1_extra_is_a:
                      r2 = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (extra_is_a1, extra_is_a2)).fetchone()
                      if r2: break
                    else:
                      r = False
                      break
                    
              #r = (e2 in e_2_extra_is_a[e1]) or cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, e2)).fetchone()
              #r = cursor.execute("""SELECT 1 FROM is_a WHERE s=? and o=? LIMIT 1""", (e1, e2)).fetchone()
              if r:
                #print("  => discard", e1, e1_extra_is_a)
                elements.discard(e1); removeds.add(e1)
                model._increment_extra("A or B with B is a A")
                break
            
        # Avoid A and/or (A and/or B)
        for e1 in elements_copy:
          for e2 in elements_copy:
            if e1 != e2:
              r = cursor.execute("""SELECT 1 FROM %s WHERE s=? AND o=? LIMIT 1""" % self.flat.table.name, (e1, e2)).fetchone()
              if r:
                elements.discard(e2)
                model._increment_extra("A and/or (A and/or B)")
                break
              
      elif (self.rel == owl_complementof):
        assert len(elements) == 1
        if owl_thing   in elements: model._list_cache[self][elements0] = owl_nothing; return owl_nothing
        if owl_nothing in elements: model._list_cache[self][elements0] = owl_thing;   return owl_thing
        
    elements = sorted(elements)
    
    if   not elements:
      if   self.rel == owl_intersectionof:
        model._list_cache[self][elements0] = owl_thing
        model._increment_extra("Empty intersection")
        return owl_thing
      elif self.rel == owl_unionof:
        model._list_cache[self][elements0] = owl_nothing
        model._increment_extra("Empty union")
        return owl_nothing
      else:
        model._list_cache[self][elements0] = None
        return None
    elif (len(elements) == 1) and (not self.flat.single_element):
      s = elements[0]
      if (s < 0) and self.is_a_thing: # Ensure that s is a thing and a clause
        r = cursor.execute("""SELECT 1 FROM is_a WHERE s=? AND o=? LIMIT 1""", (s, owl_thing)).fetchone()
        if not r:
          cursor.execute("""INSERT OR IGNORE INTO types VALUES (?,?)""", (s, owl_class))
          added_nb_inferences[model.rule_set.tables["types"]] += cursor.rowcount
          if cursor.rowcount: model._trigger_create(rdf_type)
      model._increment_extra("Single element")
      model._list_cache[self][elements0] = s
      return s
    
    linked_ok = False
    if not s:
      if   self.key:
        k = ",".join(str(e) for e in elements)
        r = cursor.execute("""SELECT s FROM %s WHERE k=? LIMIT 1""" % self.key.table.name, (k,)).fetchone()
        if r:
          model._list_cache[self][elements0] = r[0]
          return r[0]
        
      elif self.flat.single_element:
        assert len(elements) == 1
        r = cursor.execute("""SELECT s FROM %s WHERE o=? LIMIT 1""" % self.flat.table.name, (elements[0],)).fetchone()
        if r:
          model._list_cache[self][elements0] = r[0]
          return r[0]
        
      if   self.linked and len(elements) == 2:
        r = cursor.execute("""SELECT s FROM %s WHERE o1=? AND o2=? LIMIT 1""" % self.linked.table.name, elements).fetchone()
        if r:
          s = r[0]
          r2 = cursor.execute("""SELECT 1 FROM %s WHERE s=? LIMIT 1""" % self.flat.table.name, (s,)).fetchone()
          if r2:
            model._list_cache[self][elements0] = s
            return s
          linked_ok = True
          
    if   self.linked and not linked_ok:
      nb, s = self.linked.adds([(s, frozenset(elements))])
      added_nb_inferences[self.linked.table] += nb
      r = cursor.execute("""SELECT 1 FROM %s WHERE s=? LIMIT 1""" % self.flat.table.name, (s,)).fetchone()
      if r:
        model._list_cache[self][elements0] = s
        return s
      
    elif not s:
      s = model.new_blank_node()

      
    #if s == -12:
    #  print(elements0, elements)
    #  eorjfpeor
    
    # Create new
    if self.flat:
      cursor.executemany("""INSERT INTO %s VALUES (?,?)""" % self.flat.table.name, ((s, e) for e in elements))
      added_nb_inferences[self.flat.table] += len(elements)
      
    if self.key:
      k = ",".join(str(e) for e in elements)
      cursor.execute("""INSERT INTO %s VALUES (?,?)""" % self.key.table.name, (k, s))
      
    if self.is_a_thing:
      cursor.execute("""INSERT OR IGNORE INTO types VALUES (?,?)""", (s, owl_class))
      added_nb_inferences[model.rule_set.tables["types"]] += cursor.rowcount
      if cursor.rowcount: model._trigger_create(rdf_type)
      
      cursor.execute("""INSERT OR IGNORE INTO infer_ancestors VALUES (?)""", (s,))
      added_nb_inferences[model.rule_set.tables["infer_ancestors"]] += cursor.rowcount
      #if cursor.rowcount: model._trigger_create(infer_ancestors)
      
    if self.rel == owl_unionof:
      def get_s_extra_is_a(e):
        r1 = cursor.execute("""SELECT o1, o2 FROM linked_lists_31 WHERE s=? LIMIT 1""", (e,)).fetchone()
        if not r1: return [e]
        return get_s_extra_is_a(r1[0]) + get_s_extra_is_a(r1[1])
      
      for e in elements:
        if e_2_extra_is_a[e]: # an intermediary node in a AND => promote it to a full entity
          model._increment_extra("Promote AND intermediary node")
          
          cursor.execute("""INSERT OR IGNORE INTO is_a VALUES (?,?,?)""", (e, e, 3))
          added_nb_inferences[model.rule_set.tables["is_a"]] += cursor.rowcount
          cursor.execute("""INSERT OR IGNORE INTO is_a VALUES (?,?,?)""", (e, owl_thing, 2))
          added_nb_inferences[model.rule_set.tables["is_a"]] += cursor.rowcount
          
          for child in get_s_extra_is_a(e):
            cursor.execute("""INSERT OR IGNORE INTO flat_lists_31 VALUES (?,?)""", (e, child))
            added_nb_inferences[model.rule_set.tables["flat_lists_31"]] += cursor.rowcount
            
          #print(s, elements)
          #print(model._get_constructs()[s])
          #ezmlfoe
          
    if SHOW_NEW_CONSTRUCTS:
      print()
      print(s, ":", model._get_constructs()[s])
      
    model._list_cache[self][elements0] = s
    return s
  

class Rule(object):
  creates        = set()
  dependss       = []
  table_creates  = []
  table_dependss = []
  table          = None
  complexity     = 100
  priority       = 1
  recursive      = False
  
  def __init__(self, name, type):
    self.name = name
    self.type = type
    
  def copy(self):
    clone = self.__class__(self.name, self.type)
    clone.__dict__.update(self.__dict__)
    return clone
    
  def __repr__(self): return "<%s '%s'>" % (self.__class__.__name__, self.name)
  def full_repr(self): return """    %%%%%% %s %s "%s"\n""" % (self.type, self.__class__.__name__, self.name)
  
  def load(self, rule_set, options, *data): pass
  def prepare(self, rule_set): pass
  def execute(self, model, cursor): return 0, None
  
class Builtin(Rule):
  def copy(self): return self
  def load(self, rule_set, options, type, data): pass
  
class BuiltinCreateFlatList(Builtin):
  single_element = False
  
  def load(self, rule_set, options, type, data):
    self.rels  = [default_world._abbreviate(i.value[1:-1]) for i in data]
    table_list = rule_set.get_list(self.rels[0])
    table_list.flat = self
    self.table = Table(rule_set, "flat_lists_%s" % self.rels[0], ["s", "o"], list = table_list)
    rule_set.create_2_tables[self.rels[0]].append(self.table)
    
  def execute(self, model, cursor):
    model.rule_set.created_tables.add(self.table)
    return 0, None # Flat lists are filled by normalize construct
  
class BuiltinCreateSingleElementFlatList(BuiltinCreateFlatList):
  single_element = True
  
class BuiltinNormalizeConstructs(Builtin):
  def execute(self, model, cursor): return model.normalize_constructs()

  
class BuiltinCreateKeyList(Builtin):
  def load(self, rule_set, options, type, data):
    self.rels  = [default_world._abbreviate(i.value[1:-1]) for i in data]
    table_list = rule_set.get_list(self.rels[0])
    self.table = Table(rule_set, "key_lists_%s" % self.rels[0], ["k", "s"], list = table_list)
    table_list.key = self
    
  def execute(self, model, cursor):
    cursor.execute("""CREATE %s TABLE %s(k TEXT NOT NULL, s INTEGER NOT NULL)""" % (model.temporary, self.table.name))
    model.rule_set.created_tables.add(self.table)
    model.sql_destroy += """DROP TABLE %s;\n""" % self.table.name
    
    flat_table = model.rule_set.get_list(self.rels[0]).flat.table
    cursor.executemany("""INSERT INTO %s VALUES (?,?)""" % self.table.name, [
      (",".join(str(o) for o in sorted(int(o) for o in os.split(","))), s)
      for s, os in cursor.execute("""SELECT s,group_concat(o) FROM %s GROUP BY s""" % flat_table.name)
    ])
    
    cursor.execute("""CREATE UNIQUE INDEX %s_k ON %s(k)""" % (self.table.name, self.table.name))
    return 0, None # Not counted since not used in depends


def all_combinations(l):
  """returns all the combinations of the sublist in the given list (i.e. l[0] x l[1] x ... x l[n])."""
  if len(l) == 0: return [[]]
  if len(l) == 1: return [i for i in  l[0]]
  r = []
  for a in l[0]: r.extend(a + b for b in all_combinations(l[1:]))
  return r

def all_subsets(s):
  """returns all the subsets included in this set."""
  r = [frozenset()]
  for i in s:
    for j in r[:]:
      x = j | frozenset([i])
      r.append(x)
  r = [x for x in r if len(x) >= 2]
  r.sort(key = lambda x: -len(x))
  return r


class BuiltinCreateLinkedList(Builtin):
  def load(self, rule_set, options, type, data):
    self.rels  = [default_world._abbreviate(i.value[1:-1]) for i in data]
    table_list = rule_set.get_list(self.rels[0])
    table_list.linked = self
    self.table = Table(rule_set, "linked_lists_%s" % self.rels[0], ["s", "o1", "o2"], list = table_list)
    rule_set.create_2_tables[self.rels[0]].append(self.table)
    
    if owl_intersectionof in self.rels:
      self._split_list_by_priority = self._split_list_by_priority_and
    else:
      self._split_list_by_priority = None
      
  def execute(self, model, cursor):
    self.model = model
    self.priority_cache = {}
    
    cursor.execute("""CREATE %s TABLE %s(s INTEGER NOT NULL, o1 INTEGER NOT NULL, o2 INTEGER NOT NULL)""" % (model.temporary, self.table.name))
    model.sql_destroy += """DROP TABLE %s;\n""" % self.table.name
    
    flat_list = model.rule_set.get_list(self.rels[0]).flat
    if owl_intersectionof in self.rels:
      #s_lists = cursor.execute("""SELECT s, group_concat(o) FROM %s GROUP BY s HAVING s IN (SELECT s FROM infer_descendants)""" % flat_list.table.name)
      s_lists = cursor.execute("""SELECT s, group_concat(o) FROM %s GROUP BY s""" % flat_list.table.name)
      
    else:
      s_lists = cursor.execute("""SELECT s, group_concat(o) FROM %s GROUP BY s""" % flat_list.table.name)
    #s_lists = cursor.execute("""SELECT s, group_concat(o) FROM %s GROUP BY s""" % flat_list.table.name)
    s_lists = [(s, frozenset(int(i) for i in l.split(",")))  for (s, l) in s_lists]
    s_lists.sort(key = lambda i: len(i[1]))
    
    self.occurrences = dict(cursor.execute("""SELECT o, COUNT() FROM %s GROUP BY o""" % flat_list.table.name))
    self.l_2_bn = {}
    self.bn_2_l = {}
    
    if s_lists: nb, last_linked_list = self.adds(s_lists)
    else:       nb = 0
    
    cursor.execute("""CREATE INDEX %s_o1o2 ON %s(o1,o2)""" % (self.table.name, self.table.name))
    cursor.execute("""CREATE INDEX %s_o2o1 ON %s(o2,o1)""" % (self.table.name, self.table.name))
    
    model.rule_set.created_tables.add(self.table)
    #return nb, None
  
  def _split_list_by_priority_and(self, l):
    l1 = []
    l2 = []
    for s in l:
      if s >= 0: l1.append(s)
      else:
        r = self.priority_cache.get(s)
        if r is None:
          r = self.model.cursor.execute("""SELECT 1 FROM only WHERE s=? LIMIT 1""", (s,)).fetchone()
          self.priority_cache[s] = (not r is None)
        if r: l2.append(s)
        else: l1.append(s)
    return frozenset(l1), frozenset(l2)
  
  def adds(self, s_lists):
    insertions  = []
    
    def create_balanced_linked_list(l, s = None):
      l2 = frozenset(j for i in l for j in self.bn_2_l.get(i) or (i,))
      bn = self.l_2_bn.get(l2)
      if not bn:
        bn = self.l_2_bn[l2] = s or self.model.new_blank_node()
        self.bn_2_l[bn] = l2
        if   len(l) <= 2:
          insertions.append((bn, l[0], l[-1]))
        elif len(l) <= 3:
          insertions.append((bn, l[0], create_balanced_linked_list(l[1:])))
        else:
          split_point = int(len(l) / 2)
          insertions.append((bn, create_balanced_linked_list(l[:split_point]), create_balanced_linked_list(l[split_point:])))
      return bn
      
    def do_exponential(l):
      r = []
      alreadys = set()
      for subset in all_subsets(l):
        previous = self.l_2_bn.get(subset)
        if previous:
          if len(subset) == len(l): return [previous]
          if subset.issubset(alreadys): continue
          r.append(previous)
          alreadys.update(subset)
      if r: 
        
        #return [*r, *sorted(l - alreadys)]
        return [*r, *sorted(set(l) - alreadys)]
      return sorted(l)
    
    def do_heuristic(l):
      sl = sorted(l, key = lambda i: (self.occurrences[i], i))
      return sl[:-13] + do_exponential(sl[-13:])
    
    for s, l in s_lists:
      if self._split_list_by_priority:
        l_prios = [i for i in self._split_list_by_priority(l) if i] # remove empty lists
        l_merged = []
        linked_list = None
        for l_prio in reversed(l_prios):
          if len(l_prio) < 12: ll = do_exponential(l_prio)
          else:                ll = do_heuristic  (l_prio)
          if linked_list: ll.append(linked_list)
          if ll:
            if l_prio is l_prios[0]:
              linked_list = create_balanced_linked_list(ll, s)
            else:
              if len(ll) == 1: linked_list = ll[0]
              else:            linked_list = create_balanced_linked_list(ll)
              
      else:
        if len(l) < 14: linked_list = create_balanced_linked_list(do_exponential(l), s)
        else:           linked_list = create_balanced_linked_list(do_heuristic  (l), s)
      #if s and (linked_list != s): print(s_lists, s, linked_list); assert False
      
    self.model.cursor.executemany("""INSERT INTO %s VALUES (?,?,?)""" % self.table.name, insertions)
    
    return self.model.cursor.rowcount, linked_list

  
  
class BuiltinRemoveSingleParentClass(Builtin):
  def execute(self, model, cursor):
    max_rowid = cursor.execute("""SELECT max(rowid) FROM is_a""").fetchone()[0]
    r = cursor.execute("""SELECT rowid,s,o FROM is_a WHERE s>0 AND rowid!=? GROUP BY s HAVING COUNT(o)=1""", (max_rowid,)).fetchall()
    rowids = [(i[0],) for i in r]
    cursor.executemany("""DELETE FROM is_a WHERE rowid=?""", rowids)
    
    nb = -2 * len(rowids)
    return nb, None
    
#############    SQL CLASSES  ##################


class SQLBase(object):
  def __repr__(self):
    return "<%s %s>" % (self.__class__.__name__, str(self))
  
class SQLRequest(SQLBase): pass

class SQLInsertRequest(SQLRequest):
  def __init__(self):
    self.sql_inserts = []
    self.sql_ifs     = []
    
  def __str__(self):
    if (len(self.sql_inserts) == 1) and self.sql_inserts[0].table: return "%s\n%s" % (self.sql_inserts[0], "\n  UNION ALL\n".join(str(i) for i in self.sql_ifs))
    for i in self.sql_ifs: i.sql_select.select_only_vars = True
    return "\n  UNION ALL\n".join(str(i) for i in self.sql_ifs)
  
  def with_last_inference_conditions(self, rule_set, rule):
    self.last_inference_tables = []
    if (len(self.sql_inserts) == 1) and self.sql_inserts[0].table: return "%s\n%s" % (self.sql_inserts[0], "\n  UNION ALL\n".join(i.with_last_inference_conditions(self.last_inference_tables, rule_set, rule) for i in self.sql_ifs))
    for i in self.sql_ifs: i.sql_select.select_only_vars = True
    return "\n  UNION ALL\n".join(i.with_last_inference_conditions(self.last_inference_tables, rule_set, rule) for i in self.sql_ifs)
    
class SQLSelectRequest(SQLRequest):
  def __init__(self):
    self.sql_ifs    = []
    
  def __str__(self): return "\n  UNION ALL\n".join(str(i) for i in self.sql_ifs)
  
  def with_last_inference_conditions(self, rule_set, rule):
    self.last_inference_tables = []
    return "\n  UNION ALL\n".join(i.with_last_inference_conditions(self.last_inference_tables, rule_set, rule) for i in self.sql_ifs)
    
class SQLInsert(SQLBase):
  def __init__(self, table, list = None):
    self.table                    = table
    self.list                     = list
    self.has_non_condition_var    = False
    self.xs                       = []
    self.has_clause               = False
    self.pattern                  = None
    
  def __str__(self):
    if self.table: return "INSERT OR IGNORE INTO %s" % self.table.name
    return "<SQLInsert in %s>" % self.list

  
class SQLIf(SQLBase):
  def __init__(self):
    self.sql_select = SQLSelect()
    self.sql_froms     = []
    self.sql_wheres    = []
    self.sql_not_is_as = []
    self.vars          = {}
    self.sql_from_priorities = []
    
  def clone(self):
    sql_if = SQLIf()
    sql_if.sql_select    = self.sql_select
    sql_if.sql_froms     = [sql_from.clone() for sql_from in self.sql_froms]
    sql_if.sql_wheres    = self.sql_wheres
    sql_if.sql_not_is_as = self.sql_not_is_as
    sql_if.vars          = self.vars
    return sql_if
    
  def get_var(self, name, ref = None):
    if name in self.vars: return self.vars[name]
    var = self.vars[name] = Variable(name, ref)
    return var
  
  def __str__(self):
    s = "%s" % self.sql_select
    if self.sql_froms:
      s += "\nFROM %s" % self.ordered_sql_from()
    if self.sql_wheres:
      s += "\nWHERE " + (" AND ".join(str(i) for i in self.sql_wheres))
    if self.sql_not_is_as: s += ("".join("\nAND   %s" % i for i in self.sql_not_is_as))
    return s
  
  def ordered_sql_from(self):
    remnants = set(self.sql_froms)
    for sql_froms, priority in self.sql_from_priorities: remnants.difference_update(sql_froms)
    remnants = [sql_from for sql_from in self.sql_froms if sql_from in remnants]
    sql_from_priorities = [(" CROSS JOIN ".join(str(x) for x in sql_froms), priority) for (sql_froms, priority) in self.sql_from_priorities]
    if remnants: sql_from_priorities.append((", ".join(str(x) for x in remnants), 0))
    sql_from_priorities.sort(key = lambda x: x[1])
    return ", ".join(sql_froms for (sql_froms, priority) in sql_from_priorities)
    
  def priotize_sql_from_by_matching(self, match, names, priority):
    if isinstance(match, list): match = match[0]
    i_2_sql_from = { sql_from.i : sql_from for sql_from in self.sql_froms }
    
    sql_froms = []
    for name in names:
      i = int(match[name].rsplit("_", 1)[1])
      sql_froms.append(i_2_sql_from[i])
    self.sql_from_priorities.append((sql_froms, priority))
    
  def find_sql_from_by_matching(self, match, name):
    if isinstance(match, list): match = match[0]
    i = int(match[name].rsplit("_", 1)[1])
    for sql_from in self.sql_froms:
      if sql_from.i == i: return sql_from
      
  def with_last_inference_conditions(self, last_inference_tables, rule_set, rule):
    last_inference_conditions = []
    
    is_a_i = { sql_from.i for sql_from in self.sql_froms if sql_from.table.name == "is_a" }
    
    for nfrom, sql_from in enumerate(self.sql_froms):
      needed = True

      if not rule_set.table_2_inferrable.get(sql_from.table, None): needed = False
      
      # Not needed for list when a is_a-list/restriction is present (because if list/restriction is new, it implies is_a is new)
      if needed:
        if sql_from.table.list or (sql_from.table.name in _RESTRICTION_TABLES):
          for sql_where in self.sql_wheres:
            if (sql_where.operator == "=") and isinstance(sql_where.x1, SQLColRef) and isinstance(sql_where.x2, SQLColRef):
              for a,b in [(sql_where.x1, sql_where.x2), (sql_where.x2, sql_where.x1)]:
                if (a.i == sql_from.i) and (a.column == "s") and (b.i in is_a_i) and (b.column == "o"):
                  needed = False
                  break
                
      # Not needed for list having several froms (redundant)
      if needed:
        if sql_from.table.list:
          for other_from in self.sql_froms[:nfrom]:
            if other_from.table == sql_from.table:
              for sql_where in self.sql_wheres:
                if (sql_where.operator == "=") and isinstance(sql_where.x1, SQLColRef) and isinstance(sql_where.x2, SQLColRef):
                  for a,b in [(sql_where.x1, sql_where.x2), (sql_where.x2, sql_where.x1)]:
                    if (a.i == sql_from.i) and (a.column == "s") and (b.i == other_from.i) and (b.column == "s"):
                      needed = False
                      break
                    
      if needed:
        last_inference_tables.append(sql_from.table)
        last_inference_condition = "q%s.rowid>?" % sql_from.i
        last_inference_conditions.append(last_inference_condition)
        
    s = "%s" % self.sql_select
    if self.sql_froms:
      s += "\nFROM %s" % self.ordered_sql_from()
      
    if (not "CROSS JOIN" in s) and (not "flat_lists_37" in s) and len(last_inference_conditions) == 2:
      if self.sql_wheres: s0 = s + "\nWHERE " + (" AND ".join(str(i) for i in self.sql_wheres)) + "\nAND  "
      else:               s0 = s + "\nWHERE"
      
      last_inference_tables0 = list(last_inference_tables)
      last_inference_tables2 = []
      l = []
      conditions = []
      for i, last_inference_condition in enumerate(last_inference_conditions):
        l.append("%s %s" % (s0, " AND ".join(conditions + [last_inference_condition])))
        conditions.append(last_inference_condition.replace(">", "<="))
        last_inference_tables2.extend(last_inference_tables0[:i + 1])
      last_inference_tables.__init__(last_inference_tables2)
    
      s = """\n  UNION ALL\n""".join(l)
      
    elif last_inference_conditions:
      if self.sql_wheres:
        s += "\nWHERE " + (" AND ".join(str(i) for i in self.sql_wheres)) + "\nAND   (%s)" % " OR ".join(last_inference_conditions)
      else:
        s += "\nWHERE %s" % " OR ".join(last_inference_conditions)
    else:
      if self.sql_wheres:
        s += "\nWHERE " + (" AND ".join(str(i) for i in self.sql_wheres))
    if self.sql_not_is_as: s += ("".join("\nAND   %s" % i for i in self.sql_not_is_as))
    return s

  def explanation_select(self):
      is_a_i = { sql_from.i for sql_from in self.sql_froms if sql_from.table.name == "is_a" }
      
      ref_2_var = {}
      vars_in_is_a_o = set()
      for var in self.vars.values():
        for ref in var.refs:
          ref_2_var[ref] = var
          if (ref.i in is_a_i) and (ref.column == "o"):
            vars_in_is_a_o.add(var)
            
      for sql_where in self.sql_wheres:
        if (sql_where.operator == "=") and  (sql_where.x1 in ref_2_var) and (sql_where.x2 in ref_2_var):
          var1 = ref_2_var[sql_where.x1]
          var2 = ref_2_var[sql_where.x2]
          
      rowids = []
      for sql_from in self.sql_froms:
        needed = True
        if sql_from.table.name != "is_a":
          for var in vars_in_is_a_o:
            for ref in var.refs:
              if (ref.i == sql_from.i) and (ref.column == "s"):
                needed = False
                break
        if needed:
          rowids.append("'%s:'||q%s.rowid" % (sql_from.table.name, sql_from.i))
          
      return ("||','||".join(rowids)).replace(",'||'", ",") or "''"

class SQLSelect(SQLBase):
  def __init__(self, xs = None):
    self.xs = xs or []
    self.var_xs = []
    self.select_only_vars = False
  def __str__(self):
    if self.select_only_vars: return "SELECT %s" % (",".join(str(x) for x in self.var_xs))
    else:                     return "SELECT %s" % (",".join(str(x) for x in self.xs))

class SQLFrom(SQLBase):
  def __init__(self, table, i, row, index = None, depend = None):
    self.table    = table
    self.i        = i
    self.index    = index
    self.depend   = depend
    
  def __str__(self):
    if self.index is False: return "%s q%s NOT INDEXED" % (self.table.name, self.i)
    if self.index: return "%s q%s INDEXED BY %s" % (self.table.name, self.i, self.index)
    return "%s q%s" % (self.table.name, self.i)
  
  def clone(self): return SQLFrom(self.table, self.i, self.index, self.depend)
  
class SQLColRef(SQLBase):
  def __init__(self, i, column):
    self.i       = i
    self.column  = column
  def __str__(self): return "q%s.%s" % (self.i, self.column)
  
  def clone(self): return SQLColRef(self.i, self.column)
  
class SQLWhere(SQLBase):
  def __init__(self, x1, x2, operator = None):
    self.x1       = x1
    self.x2       = x2
    self.operator = operator or "="
  def __str__(self): return "%s%s%s" % (self.x1, self.operator, self.x2)
  
  def clone(self):
    return SQLWhere(
      (isinstance(self.x1, SQLColRef) and self.x1.clone()) or self.x1,
      (isinstance(self.x2, SQLColRef) and self.x2.clone()) or self.x2,
      self.operator)
  
class SQLNotIsA(SQLBase):
  def __init__(self, x1, x2):
    self.x1       = x1
    self.x2       = x2
  def __str__(self): return "NOT EXISTS (SELECT 1 FROM is_a q WHERE q.s=%s AND q.o=%s)" % (self.x1, self.x2)
  
  def clone(self):
    return SQLNotIsA(self.x1.clone(), self.x2.clone())
  
#######################   REST OF THE CLASSES   #########################   
  
class Variable(object):
  def __init__(self, name, ref = None, is_data = False):
    self.name         = name
    self.is_data      = is_data
    self.in_condition = False
    self.i_2_ref      = {}
    if ref: self.refs = [ref]; self.i_2_ref[ref.i] = ref
    else:   self.refs = []
    
  def __str__(self):
    if self.refs: return str(self.refs[0])
    return self.name
  def __repr__(self):
    if self.refs: return "<Variable %s = %s>" % (self.name, str(self))
    else:         return "<Variable %s>" % (self.name)
    
  def add_ref(self, ref):
    self.refs.append(ref)
    self.i_2_ref[ref.i] = ref
#i
    
class IfRule(Rule):
  sql0_explain = sql1_explain = None
  def full_repr(self):
    return """    %%%%%% %s %s "%s":\n%s;\n    %% dependss = %s\n    %% creates = %s\n""" % (self.type, self.__class__.__name__, self.name, self.sql1 or "", self.dependss, self.creates)
  
  def copy(self):
    clone = super().copy()
    clone.last_inferences = {}
    return clone
  
  def load(self, rule_set, options, type, *datas):
    self.dependss             = []
    self.creates              = set()
    self.table_dependss       = []
    self.table_creates        = set()
    self.clause_list          = None
    self.last_inferences      = {}
    
    for option in options:
      if   option.value == "HIGHEST_PRIORITY":   self.priority  = -100
      elif option.value == "HIGH_PRIORITY":   self.priority  = -50
      elif option.value == "LOW_PRIORITY":    self.priority  =  50
      elif option.value == "LOWEST_PRIORITY": self.priority  =  100
      elif option.value == "RECURSIVE":       self.recursive = True
      
    if   type == "INFER":
      ifs, asserts = datas
      self.sql = SQLInsertRequest()
      
    elif type == "RAISE":
      ifs, error_name = datas
      self.sql = SQLSelectRequest()
      self.error_class = getattr(owlready2, error_name.value[1:-1])
      
    else: raise ValueError("Unknown type of rule: '%s'!" % type)
    
    
    self.complexity = 0
    infer_or = False
    for if_rows in ifs:
      first_if = len(self.sql.sql_ifs) == 0
      sql_if = SQLIf()
      self.sql.sql_ifs.append(sql_if)
      self.dependss.append(set())
      self.table_dependss.append(set())
      
      if type == "INFER":
        row_2_sql_insert = {}
        for row in asserts:
          if   isinstance(row, NewNode): pass
          elif isinstance(row, AdditionalCondition): pass
          else:
            if first_if:
              if row.list_id:
                if row.table_name == "flat_lists_30": infer_or = True
                sql_insert = SQLInsert(rule_set.tables.get(row.table_name), rule_set.get_list(row.list_id))
                if isinstance(row, ClauseListRow):
                  sql_insert.has_clause = True
              else:
                sql_insert = SQLInsert(rule_set.tables[row.table_name])
              self.sql.sql_inserts.append(sql_insert)
              row_2_sql_insert[row] = sql_insert
              
            for x in row.xs:
              if x.name == "VAR":
                var = sql_if.get_var(x.value)
                sql_if.sql_select.xs.append(var)
                if first_if: sql_insert.xs.append(var)
                if not var in sql_if.sql_select.var_xs: sql_if.sql_select.var_xs.append(var)
              else:
                sql_if.sql_select.xs.append(x.parsed_value)
                if first_if:sql_insert.xs.append(x.parsed_value)
                
            self.creates.update(row.depends)
            
        if first_if:
          for row in asserts:
            if isinstance(row, ClauseListRow) and row.pattern:
              row_2_sql_insert[row].pattern     = row_2_sql_insert[row.pattern]
              row_2_sql_insert[row].pattern_var = row.pattern_var.value
              
      i_2_alternative = { None : [[]] }
      
      def get_alternative_for_x(x):
        if isinstance(x, SQLColRef):
          if x.i in i_2_alternative: return x.i
        if isinstance(x, Variable):
          if x.refs and (x.refs[0].i in i_2_alternative): return x.refs[0].i
        
      def add_sql_where(sql_where):
        alternative_on_x1 = get_alternative_for_x(sql_where.x1)
        alternative_on_x2 = get_alternative_for_x(sql_where.x2)
        if alternative_on_x1 and alternative_on_x2:
          raise NotImplementedError
        
        if (not alternative_on_x1) and (not alternative_on_x2):
          i_2_alternative[None][0].append(sql_where)
          
        else:
          sql_where2 = sql_where.clone()
          i = alternative_on_x1 or alternative_on_x2
          if alternative_on_x1:
            if isinstance(sql_where2.x1, Variable):
              sql_where2.x1 = sql_where2.x1.refs[0].clone()
            x = sql_where2.x1
          else:
            if isinstance(sql_where2.x2, Variable):
              sql_where2.x2 = sql_where2.x2.refs[0].clone()
            x = sql_where2.x2
          if   x.column == "o1": x.column = "o2"
          elif x.column == "o2": x.column = "o1"
          else:
            i_2_alternative[None][0].append(sql_where)
            return
          i_2_alternative[i][0].append(sql_where)
          i_2_alternative[i][1].append(sql_where2)
          
      # def add_sql_where(sql_where):
      #   alternative_on_x1 = isinstance(sql_where.x1, SQLColRef) and (sql_where.x1.i in i_2_alternative)
      #   alternative_on_x2 = isinstance(sql_where.x2, SQLColRef) and (sql_where.x2.i in i_2_alternative)
      #   if alternative_on_x1 and alternative_on_x2:
      #     raise NotImplementedError
      
      #   if (not alternative_on_x1) and (not alternative_on_x2):
      #     i_2_alternative[None][0].append(sql_where)
          
      #   else:
      #     sql_where2 = sql_where.clone()
      #     if alternative_on_x1: x = sql_where2.x1
      #     else:                 x = sql_where2.x2
      #     if   x.column == "o1": x.column = "o2"
      #     elif x.column == "o2": x.column = "o1"
      #     else:
      #       i_2_alternative[None][0].append(sql_where)
      #       return
      #     i_2_alternative[x.i][0].append(sql_where)
      #     i_2_alternative[x.i][1].append(sql_where2)
          
      spc_vars = []
      for i, row in enumerate(if_rows):
        if isinstance(row, AdditionalCondition):
          if   row.xs[0].name == "VAR":    x1 = sql_if.get_var(row.xs[0].value); x1.in_condition = True
          else:                            x1 = row.xs[0].storid or row.xs[0].parsed_value
          if   row.xs[2].name == "VAR":    x2 = sql_if.get_var(row.xs[2].value); x2.in_condition = True
          elif row.xs[2].name != "SPCVAR": x2 = row.xs[2].storid or row.xs[2].parsed_value
          else:
            if row.xs[2].value == "?_initial_blank_limit":
              x2 = "?"
              spc_vars.append("_initial_blank_limit")
          add_sql_where(SQLWhere(x1, x2, row.xs[1].value))
          
        elif isinstance(row, NotIsARow):
          var1 = sql_if.get_var(row.xs[0].value)
          var2 = sql_if.get_var(row.xs[1].value)
          sql_not_is_a = SQLNotIsA(var1.refs[0], var2.refs[0])
          sql_if.sql_not_is_as.append(sql_not_is_a)
          
        else:
          table_name = row.table_name
          if table_name == "direct_is_a": table_name = "is_a"
          
          i += 1
          sql_from = SQLFrom(rule_set.tables[table_name], i, row)
          sql_if.sql_froms.append(sql_from)
          
          if isinstance(row, LinkedListRow) and not row.ordered:
            i_2_alternative[i] = [[], []]
            
          self.complexity += 1
          
          if row.depends:
            self.dependss[-1].update(row.depends)
            
          if isinstance(row, ClauseListRow):
            self.clause_list = rule_set.get_list(row.list_id)
            
          for x, column in zip(row.xs, sql_from.table.columns):
            if   x is None: pass # Ignore
            
            elif x.name == "VAR":
              var = sql_if.get_var(x.value)
              var.add_ref(SQLColRef(i, column))
              if (len(var.refs) > 1) and (var.name != "?..."):
                add_sql_where(SQLWhere(SQLColRef(i, column), var.refs[0]))
              var.in_condition = True
              
            else:
              if x.storid or x.parsed_value:
                add_sql_where(SQLWhere(SQLColRef(i, column), x.storid or x.parsed_value, getattr(x, "operator", None)))
                
      sql_if.sql_select.var_xs = [var for var in sql_if.sql_select.var_xs if var.in_condition]
      
      alternatives = all_combinations(list(i_2_alternative.values()))
      sql_if.sql_wheres = alternatives[0]
      
      if len(alternatives) > 1:
        spc_vars = spc_vars * len(alternatives)
        for alternative in alternatives[1:]:
          sql_if2 = sql_if.clone()
          sql_if2.sql_wheres = alternative
          self.sql.sql_ifs.append(sql_if2)
          
          
    if type == "INFER":
      if infer_or: self.priority += 10
      if (len(self.sql.sql_inserts) > 1) or [row for row in asserts if isinstance(row, ListRow)]:
        self.__class__ = IfMultipleInferRule
        self.priority += 1
        self.complexity += 1000
        if len(ifs) > 1: raise NotImplementedError
        if self.sql.sql_ifs:
          self.new_vars = { self.sql.sql_ifs[0].vars[row.xs[0].value] for row in asserts if isinstance(row, NewNode) }
        else:
          self.new_vars = set()
          
        fixed_vars = set(self.new_vars)
        for sql_insert in self.sql.sql_inserts:
          for x in sql_insert.xs:
            if isinstance(x, Variable) and (not x.in_condition) and (not x in fixed_vars):
              sql_insert.has_non_condition_var = True
              fixed_vars.add(x)
              
      else:
        self.__class__ = IfSingleInferRule
        
        
    elif type == "RAISE":
      self.__class__ = IfRaiseRule
      for sql_if in self.sql.sql_ifs: sql_if.sql_select.xs.append(1)
      
    if self.clause_list:
      for sql_if in self.sql.sql_ifs:
        for sql_from in sql_if.sql_froms:
          if sql_from.table.list is self.clause_list:
            var_s = sql_if.get_var("?_clause_s_%s" % sql_from.i, SQLColRef(sql_from.i, "s"))
            var_o = sql_if.get_var("?_clause_o_%s" % sql_from.i, SQLColRef(sql_from.i, "o"))
            self.sql.sql_ifs[0].sql_select.var_xs.append(var_s)
            self.sql.sql_ifs[0].sql_select.var_xs.append(var_o)
            
    # Optimization hacks
    
    for sql_if in self.sql.sql_ifs:
      i_2_sql_from = { sql_from.i : sql_from for sql_from in sql_if.sql_froms }
      rels = QueryRelations()
      for sql_where in sql_if.sql_wheres:
        if (sql_where.operator == "=") and isinstance(sql_where.x1, SQLColRef) and isinstance(sql_where.x2, SQLColRef):
          rels.add_relation(
            Member(i_2_sql_from[sql_where.x1.i].table.name, sql_where.x1.i, sql_where.x1.column),
            Member(i_2_sql_from[sql_where.x2.i].table.name, sql_where.x2.i, sql_where.x2.column),
          )
      sql_if.rels = rels
      
      if len(sql_if.sql_froms) == 3:
        matches = rels.find_pattern("linked_lists.o1 = is_a_1.o, linked_lists.o2 = is_a_2.o, is_a_1.s = is_a_2.s")
        if matches:
          #sql_if.find_sql_from_by_matching(matches, "is_a_1").index = False
          sql_if.priotize_sql_from_by_matching(matches, ["is_a_1", "linked_lists", "is_a_2"], -1)
          
      has_or = has_and = has_disjoint = has_some = has_only = False
      for sql_from in reversed(sql_if.sql_froms):
        if   sql_from.table.list:
          if   sql_from.table.list.rel == owl_unionof:        has_or       = sql_from
          elif sql_from.table.list.rel == owl_intersectionof: has_and      = sql_from
          elif sql_from.table.list.rel == owl_members:        has_disjoint = sql_from
        elif sql_from.table.name       == "some":             has_some     = sql_from
        elif sql_from.table.name       == "only":             has_only     = sql_from
        
      # Favor 'and' lists rather than 'or' lists
      #if has_or and has_and:
      if has_or and (has_and or has_disjoint):
        #has_or.index = False
        matches = rels.find_pattern("flat_lists_30_1.s = is_a.o")
        if matches:
          sql_if.priotize_sql_from_by_matching(matches, ["flat_lists_30_1", "is_a"], -1)
          
        
      # Favor 'disjoint' lists rather than 'or' lists
      #if has_or and has_disjoint:
      #  has_or.index = False
      
      # Favor 'some' rather than 'only'
      #if has_some and has_only:
      #  has_some.index = False
      
      matches = rels.find_pattern("prop_is_a_1.o=types.s, prop_is_a_2.o=types.s, some_1.prop=prop_is_a_1.s, some_2.prop=prop_is_a_2.s")
      if matches:
        sql_if.priotize_sql_from_by_matching(matches, ["types", "prop_is_a_1", "some_1", "prop_is_a_2", "some_2"],  -5)
        
      
      matches = rels.find_pattern("concrete.s = is_a.s")
      if matches:
        sql_if.priotize_sql_from_by_matching(matches, ["concrete", "is_a"],  -5)
      
      matches = rels.find_pattern("some.prop = prop_is_a.s, only.prop = prop_is_a.o, is_a_1.o = some.s, is_a_2.o = only.s")
      if matches:
        sql_if.priotize_sql_from_by_matching(matches, ["some", "prop_is_a", "only"], -2)
        sql_if.priotize_sql_from_by_matching(matches, ["is_a_1", "is_a_2"],  2)
        
      else:
        matches = rels.find_pattern("some_1.prop = prop_is_a.s, some_1.value = is_a.s, some_2.prop = prop_is_a.o, some_2.value = is_a.o")
        if matches:
          sql_if.priotize_sql_from_by_matching(matches, ["some_1", "prop_is_a", "is_a", "some_2"], -2)
        
        else:
          matches = rels.find_pattern("some_1.prop = prop_is_a.s, some_2.prop = prop_is_a.o")
          if matches:
            sql_if.priotize_sql_from_by_matching(matches, ["some_2", "prop_is_a", "some_1"], -2)
            
          
            
        matches = rels.find_pattern("only_1.prop = prop_is_a.s, only_2.prop = prop_is_a.o, is_a.s = only_1.value, is_a.o = linked_lists_31_1.o1")
        matches = matches or rels.find_pattern("only_1.prop = prop_is_a.s, only_2.prop = prop_is_a.o, is_a.s = only_1.value, is_a.o = linked_lists_31_1.o2")
        if matches:
          sql_if.priotize_sql_from_by_matching(matches, ["only_1", "prop_is_a", "is_a", "linked_lists_31_1", "only_2"], -2)
            
            
            
        else:
          matches = rels.find_pattern("""only_1.prop = prop_is_a.s, only_2.prop = prop_is_a.o,
                                         is_a_1.s = only_1.value, is_a_1.o = flat_lists_37_1.o,
                                         is_a_2.s = only_2.value, is_a_2.o = flat_lists_37_2.o""")
          if matches:
            sql_if.priotize_sql_from_by_matching(matches, ["only_1", "prop_is_a", "is_a_1", "flat_lists_37_1", "flat_lists_37_2", "is_a_2", "only_2"], -2)
            
          else:
            matches = rels.find_pattern("""only_1.prop = prop_is_a.s, only_2.prop = prop_is_a.o, 
                                           is_a_1.o = only_1.s, is_a_2.o = only_2.s, is_a_1.s = is_a_2.s""")
            if matches:
              sql_if.priotize_sql_from_by_matching(matches, ["only_2", "prop_is_a", "only_1"], -2)
              sql_if.priotize_sql_from_by_matching(matches, ["is_a_1", "is_a_2"], 2)
              
            else:
              matches = rels.find_pattern("only_1.prop = prop_is_a.o, only_1.value = is_a.s, only_2.prop = prop_is_a.s, only_2.value = is_a.o")
              if matches:
                sql_if.priotize_sql_from_by_matching(matches, ["only_1", "prop_is_a", "is_a", "only_2"], -2)
                
              else:
                matches = rels.find_pattern("only_1.prop = prop_is_a.s, only_2.prop = prop_is_a.o")
                if matches:
                  sql_if.priotize_sql_from_by_matching(matches, ["only_2", "prop_is_a", "only_1"], -2)
                  
        
        
    # if self.sql0.count("all_objs") == 1:
    #   insert, select = self.sql0.split("\n", 1)
    #   self.sql0 = "%s\n%s\nUNION ALL\n%s" % (insert, select.replace("all_objs", "objs"), select.replace("all_objs", "inferred_objs"))
    #   insert, select = self.sql.split("\n", 1)
    #   self.sql = "%s\n%s\nUNION ALL\n%s" % (insert, select.replace("all_objs", "objs"), select.replace("all_objs", "inferred_objs"))
    #   self.last_inference_tables.extend(self.last_inference_tables)
    
    self.dependss = list(set(depends) for depends in set(frozenset(depends) for depends in self.dependss))
    
  def prepare(self, rule_set):
    super().prepare(rule_set)
    self.sql0 = str(self.sql)
    self.sql1 = self.sql.with_last_inference_conditions(rule_set, self)
    self.last_inference_tables = self.sql.last_inference_tables
    
    
class IfRaiseRule(IfRule):
  def execute(self, model, cursor):
    if model.debug:
      self.total_matches += len(cursor.execute(self.sql0[self.sql0.find("SELECT"):]).fetchall())
      
    if not self.last_inferences:
      r = cursor.execute(self.sql0).fetchone()
    else:
      r = cursor.execute(self.sql1, tuple(self.last_inferences[table] for table in self.last_inference_tables)).fetchone()
      
    if r: raise self.error_class
    return 0, None
  

# class TestRule(Rule):
#   dependss = [{SOME, ONLY, owl_unionof, rdfs_subclassof}]
#   creates  = []
  
#   def load(self, rule_set, options, type, *datas):
#     super().load(rule_set, options, type, *datas)
#     self.last_inferences = {}
    
#   def prepare(self, rule_set):
#     rule_set.model.world.graph.db.execute("""create table restriction_candidates(s integer)""")
#     rule_set.model.world.graph.db.execute("""create unique index restriction_candidates_s on restriction_candidates(s);""")
#     rule_set.model.world.graph.db.execute("""create table restriction_pairs(s integer, o1 integer, o2 integer)""")
#     rule_set.model.world.graph.db.execute("""create unique index restriction_pairs_o1o2s on restriction_pairs(o1, o2, s);""")
    
#   def execute(self, model, cursor):
#     if not self.last_inferences:
#       last_some = last_only = last_or = 0
#     else:
#       last_some = self.last_inferences[model.rule_set.tables["some"]]
#       last_only = self.last_inferences[model.rule_set.tables["only"]]
#       last_or   = self.last_inferences[model.rule_set.tables["flat_lists_30"]]
      
#     cursor.execute("""
# insert or ignore into restriction_candidates
#   select q1.s from some q1 WHERE q1.rowid>?
# """, (last_some,))
    
#     cursor.execute("""
# insert or ignore into restriction_candidates
#   select q1.s from only q1 WHERE q1.rowid>?
# """, (last_only,))
    
#     cursor.execute("""
# insert or ignore into restriction_candidates
#   select q1.s from flat_lists_30 q1 WHERE q1.rowid>?
# """, (last_or,))
    
#     return 0, None


class IfSingleInferRule(IfRule):
  def prepare(self, rule_set):
    super().prepare(rule_set)
    self.table = self.sql.sql_inserts[0].table
    
  def execute(self, model, cursor):
    if model.debug:
      if not self.last_inferences:
        sql = """WITH matches_found AS (%s) SELECT COUNT() FROM matches_found""" % self.sql0[self.sql0.find("SELECT"):]
        self.total_matches += cursor.execute(sql).fetchone()[0]
      else:
        sql = """WITH matches_found AS (%s) SELECT COUNT() FROM matches_found""" % self.sql1[self.sql1.find("SELECT"):]
        self.total_matches += cursor.execute(sql, tuple(self.last_inferences[table] for table in self.last_inference_tables)).fetchone()[0]
        
    if model.explain and ((self.table.name == "is_a") or (self.table.name == "flat_lists_37")):
      if not self.last_inferences:
        if not self.sql0_explain: self.sql0_explain = self._build_explain_sql(self.sql0)
        cursor.execute(self.sql0_explain)
      else:
        if not self.sql1_explain: self.sql1_explain = self._build_explain_sql(self.sql1)
        cursor.execute(self.sql1_explain, tuple(self.last_inferences[table] for table in self.last_inference_tables))

    if not self.last_inferences:
      cursor.execute(self.sql0)
    else:
      cursor.execute(self.sql1, tuple(self.last_inferences[table] for table in self.last_inference_tables))

    return cursor.rowcount, None
  
  def _build_explain_sql(self, base_sql):
    sql = ""
    current_if = 0
    for select in base_sql.split("SELECT")[1:]:
      select_part, end = select.split("FROM", 1)
      select_part = select_part.split(",")[:-1] # Remove l (=level)
      
      sql_if = self.sql.sql_ifs[current_if]
      current_if += 1
      if current_if >= len(self.sql.sql_ifs): current_if = 0
      
      rowids = sql_if.explanation_select()
      select = """SELECT '%s',%s,'%s',%s FROM %s""" % (self.table.name, "," .join(select_part), self.name, rowids, end)
      sql += select

    return """INSERT INTO explanations %s""" % sql
    
  

class IfMultipleInferRule(IfRule):
  def copy(self):
    clone = super().copy()
    clone.already_done = set()
    clone.search_time = 0.0
    return clone
  
  def prepare(self, rule_set):
    super().prepare(rule_set)
    self.already_done = set()

    if not self.sql.sql_ifs[0].sql_froms: # empty SQL request
      self.sql0 = self.sql1 = None
    
    self.sql_select_vars = self.sql.sql_ifs[0].sql_select.var_xs
    self.clause_rest_var = self.sql.sql_ifs[0].vars.get("?...")
    
    self.sql_inserts = self.sql.sql_inserts
    self.inserts = []
    self.clause_pattern = self.clause_pattern_var = None
    for sql_insert in self.sql_inserts:
      if sql_insert.has_clause:
        if sql_insert.pattern:
          self.clause_pattern = sql_insert.pattern
          for var in self.sql_select_vars:
            if var.name == sql_insert.pattern_var:
              self.clause_pattern_var = var
              break
          else: raise ValueError("Cannot find pattern var '%s'!" % sql_insert.pattern_var)
        self.clause_sql_froms_vars = []
        sql_if = self.sql.sql_ifs[0]
        for sql_from in sql_if.sql_froms:
          if sql_from.table.list is sql_insert.list:
            self.clause_sql_froms_vars.append((sql_from, sql_if.vars["?_clause_s_%s" % sql_from.i], sql_if.vars["?_clause_o_%s" % sql_from.i]))
            
  def execute(self, model, cursor):
    if self.sql0:
      if model.debug: t0 = time.time()
      
      if model.explain:
        if not self.last_inferences:
          if not self.sql0_explain: self.sql0_explain = self._build_explain_sql(self.sql0)
          r = cursor.execute(self.sql0_explain).fetchall()
        else:
          if not self.sql1_explain: self.sql1_explain = self._build_explain_sql(self.sql1)
          r = cursor.execute(self.sql1_explain, tuple(self.last_inferences[table] for table in self.last_inference_tables)).fetchall()
      else:
        if not self.last_inferences:
          r = cursor.execute(self.sql0).fetchall()
        else:
          r = cursor.execute(self.sql1, tuple(self.last_inferences[table] for table in self.last_inference_tables)).fetchall()
          
      if model.debug: self.search_time += time.time() - t0
      
    else:
      r = [()] # Assertion with an empty 'if' clause
      
    if model.debug: self.total_matches += len(r)
    
    nb_hit = nb_rows = 0
    added_nb_inferences = defaultdict(int)
    for var_values in r:
      if var_values in self.already_done: continue
      self.already_done.add(var_values)
      
      self._execute_one_select_result(model, cursor, added_nb_inferences, var_values)
      nb_rows2 = sum(added_nb_inferences.values())
      if nb_rows2 != nb_rows:
        nb_rows = nb_rows2
        nb_hit += 1

    return nb_hit, added_nb_inferences
  
  def _execute_one_select_result(self, model, cursor, added_nb_inferences, var_values):
    var_2_value = dict(zip(self.sql_select_vars, var_values))
    
    if self.clause_list:
      clause_rest = []
      for sql_from, var_s, var_o in self.clause_sql_froms_vars:
        s = var_2_value[var_s]
        o = var_2_value[var_o]
        if s != o:
          clause_rest.extend(x[0] for x in
                             cursor.execute("""SELECT o FROM %s WHERE s=?""" % sql_from.table.name, (s,))
                             if x[0] != o)
          
      if self.clause_pattern:
        pattern_var_2_value = var_2_value.copy()
        clause_rest2 = []
        for x in clause_rest:
          pattern_var_2_value[self.clause_pattern_var] = x
          if not self._execute_one_sql_insert(model, cursor, added_nb_inferences, pattern_var_2_value, None, self.clause_pattern):
            return False
          clause_rest2.append(pattern_var_2_value.pop(self.clause_pattern.xs[0]))
        clause_rest = clause_rest2
        
      var_2_value[self.clause_rest_var] = clause_rest

    # if self.name == "some_only_and_or_2":
    #   d = set()
    #   for (var, v) in var_2_value.items():
    #     if isinstance(v, list):
    #       v2 = [ str(model._get_constructs()[i]) for i in v ]
    #     else:
    #       v2 = str(model._get_constructs()[v])
    #     d.add("%s=%s" % (var.name, v2))
    #   print(d)
    
    for var in self.new_vars: var_2_value[var] = model.new_blank_node()
    
    for sql_insert_i, sql_insert in enumerate(self.sql_inserts):
      if not self._execute_one_sql_insert(model, cursor, added_nb_inferences, var_2_value, sql_insert_i, sql_insert):
        return False
      
  def _execute_one_sql_insert(self, model, cursor, added_nb_inferences, var_2_value, sql_insert_i, sql_insert):
    if sql_insert.list:
      s = var_2_value.get(sql_insert.xs[0], None)
      
      elements = []
      for x in sql_insert.xs[1:]:
        if isinstance(x, Variable):
          x = var_2_value[x]
          if isinstance(x, list): elements.extend(x) # clause rest
          else:                   elements.append(x)
        else:
          elements.append(x)
      elements = frozenset(elements)
      
      
      if (not sql_insert_i is None) and (sql_insert.list.rel == owl_unionof):
        next_sql_insert = self.sql_inserts[sql_insert_i + 1]
        if next_sql_insert.table and (next_sql_insert.table.name == "is_a"):
          child = var_2_value.get(next_sql_insert.xs[0])
          if child in elements:
            # if len(elements) > 1:
            #   elements2 = []
            #   for x in sql_insert.xs[1:]:
            #     if isinstance(x, Variable):
            #       x = var_2_value[x]
            #       elements2.append(x)
            #     else:
            #       elements2.append(x)
            #   print("!!!!", child, elements2)
            return False
          
          
      old = added_nb_inferences.copy()
      
      var_2_value[sql_insert.xs[0]] = sql_insert.list.add(model, cursor, added_nb_inferences, elements, s)
      
      if model.explain and (sql_insert.list.rel == owl_members):
        if self.sql0: sources = var_2_value[self.sql_select_vars[-1]]
        else:         sources = ""
        cursor.execute("""INSERT INTO explanations VALUES (?,?,?,?,?)""",
                       ("flat_lists_37",
                        s,
                        ",".join(str(e) for e in elements),
                        self.name, sources))
        
    else:
      # reusable_s = None
      # if (self.name == "some_func") and sql_insert.table and (sql_insert.table.name == "only"):
      #   #print("!!!", self.name, sql_insert.table, sql_insert.xs, var_2_value)
      #   #print(sql_insert.xs[0], sql_insert.xs[0].__dict__)
      #   for sql_insert2 in self.sql_inserts:
      #     if sql_insert2.table and (sql_insert2.table.name == "is_a") and (sql_insert2.xs[1] == sql_insert.xs[0]) and isinstance(sql_insert2.xs[0], Variable):
      #       reusable_s = var_2_value[sql_insert2.xs[0]]
      #       #print(reusable_s)
      #       r = ( cursor.execute("""SELECT 1 FROM linked_lists_31 WHERE s=?""", (reusable_s,)).fetchone()
      #          or cursor.execute("""SELECT 1 FROM linked_lists_30 WHERE s=?""", (reusable_s,)).fetchone() )
      #       if r:
      #         reusable_s = None
      #       break
      #
      #sql_insert.table.add(model, cursor, added_nb_inferences, var_2_value, sql_insert, reusable_s)
      
      if not sql_insert.table.add(model, cursor, added_nb_inferences, var_2_value, sql_insert): return False
      
      if model.explain and (sql_insert.table.name == "is_a"):
        if self.sql0: sources = var_2_value[self.sql_select_vars[-1]]
        else:         sources = ""
        cursor.execute("""INSERT INTO explanations VALUES (?,?,?,?,?)""",
                       (sql_insert.table.name,
                        var_2_value.get(sql_insert.xs[0]) or sql_insert.xs[0],
                        var_2_value.get(sql_insert.xs[1]) or sql_insert.xs[1],
                        self.name, sources))
    return True
          
  def _build_explain_sql(self, base_sql):
    if self.sql_select_vars[-1].name != "?_sources": self.sql_select_vars.append(Variable("?_sources"))
    
    sql = ""
    current_if = 0
    for select in base_sql.split("SELECT")[1:]:
      select_part, end = select.split("FROM", 1)
      
      sql_if = self.sql.sql_ifs[current_if]
      current_if += 1
      if current_if >= len(self.sql.sql_ifs): current_if = 0
      
      rowids = sql_if.explanation_select()
      select = """SELECT %s,%s FROM %s""" % (select_part, rowids, end)
      sql += select
    return sql
        
################## OWL PROPERTIES ####################

owl_functional_property = default_world._abbreviate("http://www.w3.org/2002/07/owl#FunctionalProperty")
owl_transitive_property = default_world._abbreviate("http://www.w3.org/2002/07/owl#TransitiveProperty")

OWL_TYPES = { owl_class, owl_object_property, owl_data_property, owl_functional_property, owl_transitive_property }

class Stage(object):
  def __init__(self, name, preprocesses = None, completions = None, initial_completions = None):
    self.name                = name
    self.preprocesses        = preprocesses or []
    self.completions         = completions  or []
    self.initial_completions = initial_completions or self.completions
    
  def tailor_for(self, model, has_prop, additional_creates):
    db                  = model.world.graph.db
    completions         = []
    removed_completions = {}
    
    def rule_dependss_matched(rule, additional_creates2 = frozenset()):
      for depends in rule.dependss:
        for depend in depends:
          present = (depend in additional_creates) or (depend in additional_creates2) or has_prop.get(depend, None)
          if present is None:
            present = has_prop[depend] = bool(db.execute("""SELECT 1 FROM quads WHERE p=? LIMIT 1""", (depend,)).fetchone())
          if not present:
            removed_completions[rule] = depend
            break
        else:
          return True
      return False
    
    for rule in self.completions:
      if rule_dependss_matched(rule):
        completions.append(rule)
        removed_completions.pop(rule, None)
        
    initial_completions = list(completions)
    completions_set     = set (completions)
    creates = { create for rule in completions for create in rule.creates }
    for rule in self.preprocesses:
      if rule_dependss_matched(rule): creates.update(rule.creates)
    while True:
      new_rule_found = False
      for rule in self.completions:
        if rule in completions_set: continue
        if rule_dependss_matched(rule, creates):
          completions.append(rule)
          completions_set.add(rule)
          removed_completions.pop(rule, None)
          creates.update(rule.creates)
          new_rule_found = True
      if not new_rule_found: break
      
    if model.debug:
      for rule, depend in removed_completions.items(): print("Enlève la règle %s : manque %s" % (rule.name, depend))
      print()
      
    d = { rule : rule.copy() for rule in completions }
    completions = list(d.values())
    initial_completions = [d[rule] for rule in initial_completions]
    
    clone   = Stage(self.name, [rule.copy() for rule in self.preprocesses], completions, initial_completions)
    creates = { create for rule in completions for create in rule.creates }
    
    clone.depend_2_completions = defaultdict(set)
    for create in creates | { rdf_type, rdfs_subclassof, rdfs_subpropertyof }:
      for rule in completions:
        for depends in rule.dependss:
          if create in depends:
            clone.depend_2_completions[create].add(rule)
            break
    
    return clone, creates
    

class RuleSet(object):
  def __init__(self, init = True):
    if not init: return

    self.stages              = []
    self.name_2_rule         = {}
    self.tables              = {}
    self.lists               = {}
    self.model               = None
    
    Table(self, "inferred_objs",  ["s", "p", "o"], search_name = "all_objs")
    Table(self, "objs",           ["s", "p", "o"])
    Table(self, "all_objs",       ["s", "p", "o"])
    Table(self, "types",          ["s", "o"])
    Table(self, "is_a",           ["s", "o", "l"])
    Table(self, "prop_is_a",      ["s", "o"]) # XXX en faire une étape à part ?
    Table(self, "datas",          ["s", "p", "o"])
    ObjectRestrictionTable(self, "some" ,          ["s", "prop", "value"], is_a_thing = True)
    ObjectRestrictionTable(self, "only" ,          ["s", "prop", "value"], is_a_thing = True)
    #ObjectRestrictionTable(self, "max" ,           ["s", "card", "prop", "value"], is_a_thing = True)
    #ObjectRestrictionTable(self, "min" ,           ["s", "card", "prop", "value"], is_a_thing = True)
    ObjectRestrictionTable(self, "exactly" ,       ["s", "card", "prop", "value"], is_a_thing = True)
    Table(self, "data_value",     ["s", "prop", "value", "datatype"], is_a_thing = True)
    Table(self, "infer_descendants",["s"])
    Table(self, "infer_ancestors",  ["s"])
    Table(self, "concrete",["s"])
    Table(self, "flat_lists_292",["s", "o"])
    
    self.table_2_inferrable = {
      self.tables["objs"]      : False,
      self.tables["datas"]     : False,
      self.tables["types"]     : True,
      self.tables["is_a"]      : True,
      self.tables["prop_is_a"] : True,
      self.tables["infer_descendants"] : True,
      self.tables["infer_ancestors"]   : True,
      self.tables["concrete"] : True,
    }
      
    self.create_2_tables = defaultdict(lambda : [self.tables["inferred_objs"]])
    self.create_2_tables[rdf_type] = [self.tables["types"]]
    self.create_2_tables[rdfs_subclassof] = [self.tables["is_a"]]
    self.create_2_tables[rdfs_subpropertyof] = [self.tables["prop_is_a"]]
    self.create_2_tables[SOME]    = [self.tables["some"]]
    self.create_2_tables[VALUE]   = [self.tables["some"]]
    self.create_2_tables[ONLY]    = [self.tables["only"]]
    #self.create_2_tables[MAX]     = [self.tables["max"]]
    #self.create_2_tables[MIN]     = [self.tables["min"]]
    self.create_2_tables[EXACTLY] = [self.tables["exactly"]]
    self.create_2_tables[infer_descendants] = [self.tables["infer_descendants"]]
    self.create_2_tables[infer_ancestors] = [self.tables["infer_ancestors"]]
    self.create_2_tables[owlready_concrete] = [self.tables["concrete"]]
    #for iri, table_name in iri_2_table_name.items():
    #  self.create_2_tables[default_world._abbreviate(iri[1:-1])].append(self.tables[table_name])
    
  def clone(self, stages, model):
    clone = RuleSet(False)

    clone.stages              = stages
    clone.name_2_rule         = {}
    for stage in stages:
      for rule in stage.preprocesses: clone.name_2_rule[rule.name] = rule
      for rule in stage.completions:  clone.name_2_rule[rule.name] = rule
    clone.tables              = self.tables
    clone.lists               = self.lists
    clone.table_2_inferrable  = self.table_2_inferrable.copy()
    clone.create_2_tables     = self.create_2_tables
    clone.model               = model
    
    clone.created_tables = {
      clone.tables["inferred_objs"], clone.tables["objs"], clone.tables["all_objs"],
      clone.tables["types"], clone.tables["is_a"], clone.tables["prop_is_a"],
      clone.tables["datas"],
      } | { clone.tables[name] for name in _RESTRICTION_TABLES }
    
    return clone
  
  def get_list(self, storid):
    table_list = self.lists.get(storid)
    if table_list is None:
      table_list = self.lists[storid] = List(storid)
      self.create_2_tables[storid] = []
    return table_list
  
  def __repr__(self): return "<RuleSet, %s rules: %s>" % (len(self.rules), ", ".join(rule.name for rule in self.rules))
  
  def dump(self):
    print()
    print("    %%%%%% RULE SET:\n")
    for stage in self.stages:
      print("    %%%%%% STAGE %s:\n" % stage.name)
      for rule in stage.preprocesses: print(rule.full_repr())
      print()
      for rule in stage.completions: print(rule.full_repr())
      print()
      
  def load(self, rules_txt):
    import owlready2.rply as rply
    
    lexer, parser = get_parsers()
    try: parsed = parser.parse(lexer.lex(rules_txt))
    except rply.LexingError  as e: raise ValueError("Cannot parse rule files, lexing error at %s near '%s'!" % (e.source_pos, rules_txt[e.source_pos:e.source_pos + 40]))
    except rply.ParsingError as e: raise ValueError("Cannot parse rule files, parsing error at %s near '%s'!" % (e.source_pos, rules_txt[e.source_pos:e.source_pos + 40]))
    
    #rule = TestRule("test_rule", "COMPLETION")
    #rule.load(self, [], "INFER")
    #self.name_2_rule[rule.name] = rule
    #self.stages[-1].completions .append(rule)
    
    for type, decl, options, name, *data in parsed:
      name = name.value[1:-1]
      if   type == "STAGE":
        stage = Stage(name)
        self.stages.append(stage)
        continue
      
      elif type == "BUILTIN":
        RuleClass = globals()["Builtin%s" % data[0].value[1:-1]]
        rule = RuleClass(name, decl.value)
        rule.load(self, options, type, *data[1:])
        
      elif (type == "INFER") or (type == "RAISE"):
        rule = IfRule(name, decl.value)
        rule.load(self, options, type, *data)
        
      if rule.name in self.name_2_rule: raise ValueError("Duplicated preprocess/completion rule name '%s'!", rule.name)
      self.name_2_rule[rule.name] = rule
      if   decl.value == "PREPROCESS": self.stages[-1].preprocesses.append(rule)
      elif decl.value == "COMPLETION": self.stages[-1].completions .append(rule)
      
  def tailor_for(self, model):
    has_prop = { rdf_type : True, rdfs_subclassof : True, rdfs_subpropertyof : True }

    stages = []
    additional_creates = set()
    for stage in self.stages:
      stage, stage_creates = stage.tailor_for(model, has_prop, additional_creates)
      additional_creates.update(stage_creates)
      stages.append(stage)
      
    clone = self.clone(stages, model)
    clone.model = model
    
    additional_creates.add(owl_members) # XXX Faster with this, for some obscure reason
    
    for create in additional_creates:
      for table in clone.create_2_tables[create]:
        clone.table_2_inferrable[table] = True
        
    for rule in clone.name_2_rule.values(): rule.prepare(clone)
    
    return clone
    



RULE_SETS = {}
def get_rule_set(filename):
  rule_set = RULE_SETS.get(filename)
  if not rule_set:
    f = open(os.path.join(os.path.dirname(__file__), filename))
    rule_set = RULE_SETS[filename] = RuleSet()
    rule_set.load(f.read())
    f.close()
  return rule_set


if __name__ == "__main__":
  import sys
  import owlready2.rply as rply

  onto = get_ontology("http://test.org/test.owl")
  with onto:
    class p(ObjectProperty): pass
    class A(Thing): pass
    #class B(Thing): is_a = [p.some(A), p.only(A), p.max(1, A)]
    class B(Thing): is_a = [p.some(A), p.only(A)]
    AllDisjoint([A, B])
    class C(Thing): equivalent_to = [A&B, A|B, Not(A)]
    class R(Thing): pass
    
  from semantic2sql.reasoned_model import *
  rm = ReasonedModel(default_world, "rules.txt", temporary = True)
  rule_set = rm.rule_set
  
  if   "--priority" in sys.argv:
    for stage in rule_set.stages:
      print("%s :" % stage.name)
      for rule in sorted(stage.completions, key = lambda rule: rule.priority):
        print("  %s : %s" % (rule.priority, rule.name))
      print()
      
  elif len(sys.argv) > 1:
    for arg in sys.argv[1:]:
      print(rule_set.name_2_rule[arg].full_repr())
      print()
        
  else:
    rule_set.dump()
