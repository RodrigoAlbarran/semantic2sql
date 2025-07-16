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

import sys, time, random, itertools
from collections import defaultdict
import owlready2
from owlready2.reasoning import _apply_reasoning_results, _INFERRENCES_ONTOLOGY
from semantic2sql.rule import *


_NORMALIZED_PROPS = {rdfs_subclassof, SOME, VALUE, ONLY, EXACTLY, MIN, MAX, owl_onproperty, owl_onclass, owl_ondatarange, owl_withrestrictions}


class ReasonedModel(object):
  def __init__(self, world, rule_set = None, temporary = True, debug = False, explain = False):
    self.world                  = world
    self.db                     = world.graph.db
    self.temporary              = "TEMPORARY" if temporary else ""
    self._candidate_completions = set()
    self.sql_destroy            = ""
    self.debug                  = debug
    self.explain                = explain
    self._extra_dumps           = {}
    self.extract_result_time    = 0
    self.new_parents            = None
    self.new_equivs             = None
    self.entity_2_type          = None
    self.optimize_limits        = defaultdict(lambda : 1)
    
    if rule_set is None:            self.rule_set = get_rule_set("rules.txt").tailor_for(self)
    elif isinstance(rule_set, str): self.rule_set = get_rule_set(rule_set).tailor_for(self)
    else:                           self.rule_set = rule_set.tailor_for(self)

    self._list_cache = {}
    for l in self.rule_set.lists.values(): self._list_cache[l] = {}
    
  def _increment_extra(self, name, v = 1):
    self._extra_dumps[name] = self._extra_dumps.get(name, 0) + v
    
  def new_blank_node(self):
    self.current_blank += 1
    return -self.current_blank
  
  def prepare(self):
    self.current_blank = self.world.graph.execute("SELECT current_blank FROM store").fetchone()[0]
    
    if self.temporary: self.cursor.execute("""PRAGMA temp_store = MEMORY""")
    
    self.cursor.executescript("""
CREATE $TEMP$ TABLE inferred_objs(s INTEGER NOT NULL, p INTEGER NOT NULL, o INTEGER NOT NULL);
CREATE UNIQUE INDEX inferred_objs_spo ON inferred_objs(s,p,o);
CREATE INDEX inferred_objs_op ON inferred_objs(o,p);

CREATE $TEMP$ TABLE types(s INTEGER NOT NULL, o INTEGER NOT NULL);
CREATE $TEMP$ TABLE is_a(s INTEGER NOT NULL, o INTEGER NOT NULL, l INTEGER NOT NULL);
CREATE $TEMP$ TABLE prop_is_a(s INTEGER NOT NULL, o INTEGER NOT NULL);
CREATE $TEMP$ TABLE some      (s INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL);
CREATE $TEMP$ TABLE data_value(s INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL, datatype INTEGER NOT NULL);
CREATE $TEMP$ TABLE only      (s INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL);
CREATE $TEMP$ TABLE max       (s INTEGER NOT NULL, card INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL);
CREATE $TEMP$ TABLE min       (s INTEGER NOT NULL, card INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL);
CREATE $TEMP$ TABLE exactly   (s INTEGER NOT NULL, card INTEGER NOT NULL, prop INTEGER NOT NULL, value INTEGER NOT NULL);

CREATE $TEMP$ VIEW restriction AS SELECT s,prop,value FROM some UNION ALL SELECT s,prop,value FROM only UNION ALL SELECT s,prop,NULL FROM data_value;

CREATE $TEMP$ TABLE infer_descendants(s INTEGER NOT NULL);
CREATE UNIQUE INDEX infer_descendants_s ON infer_descendants (s);

CREATE $TEMP$ TABLE infer_ancestors(s INTEGER NOT NULL);
CREATE UNIQUE INDEX infer_ancestors_s ON infer_ancestors (s);

CREATE $TEMP$ TABLE concrete(s INTEGER NOT NULL);
CREATE UNIQUE INDEX concrete_s ON concrete (s);

CREATE $TEMP$ VIEW all_objs(rowid,s,p,o) AS SELECT 1,s,p,o FROM objs UNION ALL SELECT rowid,s,p,o FROM inferred_objs;
""".replace("$TEMP$", self.temporary))

    
    self.sql_destroy += """
DROP TABLE inferred_objs;
DROP TABLE types;
DROP TABLE is_a;
DROP TABLE prop_is_a;
DROP TABLE some;
DROP TABLE data_value;
DROP TABLE only;
DROP TABLE max;
DROP TABLE min;
DROP TABLE exactly;
DROP VIEW all_objs;
"""

    # Imports
    self.cursor.execute("""INSERT INTO types SELECT s,o FROM objs WHERE p=? AND o IN (?,?,?,?,?,?)""", (rdf_type, owl_named_individual, owl_class, owl_object_property, owl_data_property, owl_functional_property, owl_transitive_property))
    
    self.cursor.execute("""INSERT INTO is_a SELECT q1.s,q1.o,1 FROM objs q1, objs q2 WHERE q1.p=? AND q2.s=q1.s AND q2.p=? AND q2.o=? AND q1.o!=?""", (rdf_type, rdf_type, owl_named_individual, owl_named_individual))
    self.cursor.execute("""INSERT INTO is_a SELECT s,o,1 FROM objs WHERE p=?""", (rdfs_subclassof,))
    
    self.cursor.execute("""INSERT INTO prop_is_a SELECT s,o FROM objs WHERE p=?""", (rdfs_subpropertyof,))
    
    self.cursor.execute("""CREATE UNIQUE INDEX types_so ON types(s,o)""")
    self.cursor.execute("""CREATE INDEX types_o ON types(o)""")
    
    self.cursor.execute("""CREATE UNIQUE INDEX is_a_so ON is_a(s,o)""")
    self.cursor.execute("""CREATE INDEX is_a_o ON is_a(o)""")
    self.cursor.execute("""CREATE INDEX is_a_l ON is_a(l)""")
    
    self.cursor.execute("""CREATE UNIQUE INDEX prop_is_a_so ON prop_is_a(s,o)""")
    self.cursor.execute("""CREATE INDEX prop_is_a_o ON prop_is_a(o)""")
    
    if self.explain:
      self.cursor.execute("""CREATE %s TABLE explanations(t TEXT NOT NULL, s INTEGER NOT NULL, o INTEGER NOT NULL, rule TEXT NOT NULL, sources TEXT NOT NULL)""" % self.temporary)
      self.cursor.execute("""INSERT INTO explanations SELECT 'is_a', s, o, 'assertion', '' FROM is_a""")
      self.sql_destroy += """\nDROP TABLE explanations;\n"""
      
  def _optimize(self):
  
    pass
  
  def _check_optimize_table(self, table, nb):
    if nb >= self.optimize_limits[table]:
      self.optimize_limits[table] = 2 * nb
      self.cursor.execute("""ANALYZE %s""" % table.name)
      
    
  def destroy(self):
    self.cursor.executescript(self.sql_destroy)
    self.sql_destroy = ""
    
  def _restriction_depth(self, s = None, with_is_a = True):
    if s is None:
      if with_is_a:
        r = self.cursor.execute("""
WITH depth(n) AS (
SELECT (
WITH RECURSIVE interm(s) AS (
SELECT restriction.s
  UNION
SELECT r.value FROM interm, restriction r, is_a WHERE is_a.o=interm.s AND is_a.s=r.s AND r.value IN (SELECT s FROM restriction)
)
SELECT COUNT(*) FROM interm
)
FROM restriction)
SELECT MAX(n) FROM depth;
""").fetchone()
      else:
        r = self.cursor.execute("""
WITH depth(n) AS (
SELECT (
WITH RECURSIVE interm(s) AS (
SELECT restriction.s
  UNION
SELECT r.value FROM interm, restriction r WHERE r.s=interm.s AND r.value IN (SELECT s FROM restriction)
)
SELECT COUNT(*) FROM interm
)
FROM restriction)
SELECT MAX(n) FROM depth;
""").fetchone()
      
    else:

      r = self.cursor.execute("""
WITH RECURSIVE interm(s) AS (
SELECT ?
  UNION
SELECT r.value FROM interm, restriction r WHERE interm.s=r.s
)
SELECT COUNT() FROM interm WHERE s IN (SELECT s FROM restriction);
""", (s,)).fetchone()
      
    return r[0]
  
  def check_restriction_depth(self, depth):
    if depth <= self.max_restriction_depth: return True
    last_is_a_inference = self.last_inferences[self.rule_set.tables["is_a"]]
    if self.max_restriction_depth_last_update < last_is_a_inference: # Need update
      self.max_restriction_depth = self._restriction_depth(with_is_a = 0)
      self.max_restriction_depth_last_update = last_is_a_inference
      #print("\n!!! max_restriction_depth => ", self.max_restriction_depth)
      if depth <= self.max_restriction_depth: return True
    return False
    
      
  def merge_equivalent_concepts(self):
    #t = time.time()
    
    ps = ",".join(str(x) for x in [owl_equivalentclass, owl_equivalentindividual])
    equivs = self.cursor.execute("""
SELECT s,o FROM objs WHERE p IN (%s) AND s>0 AND o<0
  UNION ALL
SELECT o,s FROM objs WHERE p IN (%s) AND o>0 AND s<0 
""" % (ps, ps)).fetchall()
    if not equivs: return
    
    self.cursor.execute("""CREATE INDEX tmpquads_s ON tmpquads(s) WHERE s<0""")
    self.cursor.execute("""CREATE INDEX tmpquads_o ON tmpquads(o) WHERE o<0""")
    
    alreadys = set()
    repl = []
    for s,o in equivs:
      if (s in alreadys) or (o in alreadys): continue
      alreadys.add(s)
      alreadys.add(o)
      repl.append((s, o))
      
    self.cursor.executemany("""UPDATE tmpquads SET s=? WHERE s<0 AND s=?""", repl)
    self.cursor.executemany("""UPDATE tmpquads SET o=? WHERE o<0 AND o=?""", repl)
    
    removed = [(o,) for (s, o) in repl]
    self.cursor.executemany("""DELETE FROM is_a WHERE s=?""", removed)
    self.cursor.executemany("""DELETE FROM is_a WHERE o=?""", removed)
    self.cursor.executemany("""DELETE FROM types WHERE s=?""", removed)
    
    for table_name in ("is_a", "types"): # Reset due to removals
      self.last_inferences[self.rule_set.tables[table_name]] = self.cursor.execute("""SELECT MAX(rowid) FROM %s""" % table_name).fetchone()[0]
      
    #print("\n", time.time() - t, "s", file = sys.stderr)
    
    if self.debug: self.check_last_inferences()
    
  def normalize_constructs(self):
    debug = 0
    nb    = 0
    nbs   = {}
    flat_lists = [l for l in self.rule_set.lists.values() if l.flat]
    
    def int_p(po): return int(po[0]), po[1]
    
    cursor = self.cursor
    world  = self.world
    merges = {}
    
    cursor.execute("""CREATE TEMPORARY TABLE tmpquads (s INTEGER, p INTEGER, o INTEGER)""")
    cursor.execute("""INSERT INTO tmpquads SELECT s,p,o FROM quads WHERE s < 0 AND p IN (%s)""" % ",".join(str(p) for p in _NORMALIZED_PROPS))
    l = []
    
    REMOVE_SINGLE_LIST_RELS = { owl_intersectionof, owl_unionof }
    
    for flat_list in flat_lists:
      for rel in flat_list.flat.rels:
        r = cursor.execute("""SELECT s,p,o FROM quads WHERE p=?""", (rel,)).fetchall()
        if flat_list.flat.single_element:
          l.extend(list(r))
        else:
          for s,p,o in r:
            rdf_list = list(set(world._parse_list_as_rdf(o)))
            if   (len(rdf_list) == 1) and (flat_list.rel in REMOVE_SINGLE_LIST_RELS):
              cursor.execute("""INSERT INTO is_a SELECT q1.s,?,1 FROM is_a q1 WHERE q1.o=?""", (rdf_list[0][0], s))
              cursor.execute("""DELETE FROM is_a WHERE o=?""", (s,))
            elif len(rdf_list) >  1:
              l.extend((s, flat_list.rel, i) for (i,d) in rdf_list)
              
    cursor.executemany("""INSERT INTO tmpquads VALUES (?,?,?)""", l)
    
    self.merge_equivalent_concepts()
    
    if debug:
      print("\nNORMALIZE STEP 0 :")
      for s,p,o in cursor.execute("""SELECT s,p,o FROM tmpquads""").fetchall(): print("   ", s, p, o)
      print()
    
    cursor.execute("""CREATE TEMPORARY TABLE tmpnorm (def TEXT, s TEXT, s0 INTEGER, nb INTEGER)""")
    
    class Insertions(object):
      def __init__(self, iteration):
        self.iteration  = iteration
        self.insertions = []
        self.merges     = []
        
      def extract(self):
        cursor.execute("""DELETE FROM tmpnorm""")
        
        cursor.execute("""INSERT INTO tmpnorm
WITH sorted_tmpquads(s,p,o) AS (
SELECT * FROM tmpquads ORDER BY p,o
),
     interm(s,def) AS (
SELECT s, group_concat(p || ' ' || o) FROM sorted_tmpquads GROUP BY s
)
SELECT def, group_concat(s), MAX(s), COUNT() FROM interm GROUP BY def
""")

      def dump1(self):
        print("\nNORMALIZE STEP %s :" % self.iteration)
        for po, s, nb in cursor.execute("""SELECT def, s, nb FROM tmpnorm""").fetchall(): print("   ", po, " | ", s, " | ", nb)
        print()
        
      def dump2(self):
        for s,p,o in cursor.execute("""SELECT s,p,o FROM tmpquads""").fetchall(): print("   ", s, p, o)
        print()
        
      def insert(self):
        cursor.execute("""DROP INDEX IF EXISTS tmpquads_s""")
        cursor.execute("""DROP INDEX IF EXISTS tmpquads_o""")
        cursor.execute("""DELETE FROM tmpquads""")
        cursor.executemany("INSERT OR IGNORE INTO tmpquads VALUES (?,?,?)", self.insertions)
        
        cursor.execute("""CREATE INDEX tmpquads_s ON tmpquads(s)""")
        cursor.execute("""CREATE INDEX tmpquads_o ON tmpquads(o)""")
        
        nb = cursor.rowcount
        if debug: print("NORMALIZE MERGES", self.merges)
        for s0, s in self.merges:
          renames = []
          removes = []
          for s2 in s.split(","):
            s2 = int(s2)
            if s2 == s0: continue
            removes.append((s2,))
            renames.append((s0, s2))
          cursor.executemany("""DELETE FROM tmpquads WHERE s=?""", removes)
          cursor.executemany("""UPDATE OR REPLACE tmpquads SET o=? WHERE o=?""", renames)
          cursor.executemany("""UPDATE OR REPLACE is_a SET o=? WHERE o=?""", renames) # Optimizable
          cursor.executemany("""UPDATE OR REPLACE is_a SET s=? WHERE s=?""", renames)
          cursor.executemany("""DELETE FROM types WHERE s=?""", removes)
        return nb
      
    iteration = 1
    while True:
      insertions = Insertions(iteration)
      insertions.extract()
      if debug: insertions.dump1()
      
      if not cursor.execute("""SELECT 1 FROM tmpnorm WHERE nb > 1 LIMIT 1""").fetchone(): break
      
      for po, s0 in cursor.execute("""SELECT def, s0 FROM tmpnorm WHERE nb = 1"""):
        for po1 in po.split(","):
          insertions.insertions.append((s0, *int_p(po1.split(" "))))
          
      for po, s, s0 in cursor.execute("""SELECT def, s, s0 FROM tmpnorm WHERE nb > 1""").fetchall():
        for po1 in po.split(","):
          insertions.insertions.append((s0, *int_p(po1.split(" "))))
        insertions.merges.append((s0, s))
        
      insertions.insert()
      
      if debug: insertions.dump2()
      iteration += 1
      
      
    p_2_restriction_i = {
      ONLY : -1,
      SOME : -1,
      VALUE : -1,
      HAS_SELF : -1,
      MAX : -2,
      MIN : -2,
      EXACTLY : -2,
      owl_onproperty : 2,
      owl_onclass : 3,
      owl_ondatarange : 3,
    }
    
    somes       = []
    data_values = []
    onlys       = []
    maxs        = []
    mins        = []
    exactly    = []
    for po, s0 in self.cursor.execute("""SELECT def, s0 FROM tmpnorm"""):
      po = [int_p(i.split(" ")) for i in po.split(",")]
      if po[0][0] in p_2_restriction_i:
        restriction = [s0, 0, 0, 0]
        type = None
        for p, o in po:
          i = p_2_restriction_i[p]
          if   i == -1: restriction[3] = o; type = p
          elif i == -2: restriction[1] = int(o); type = p
          else:         restriction[i] = int(o)
        if   type == SOME:    del restriction[1]; somes.append(restriction)
        elif type == ONLY:    del restriction[1]; onlys.append(restriction)
        elif type == MAX:     maxs   .append(restriction)
        elif type == MIN:     mins   .append(restriction)
        elif type == EXACTLY: exactly.append(restriction)
        elif type == VALUE:
          del restriction[1]
          if self.world._get_by_storid(restriction[1])._owl_type == owl_data_property:
            data_values.append(restriction + ["XXX"])
          else:
            somes.append(restriction)
            
    for table, values in [("some", somes), ("data_value", data_values), ("only", onlys), ("max", maxs), ("min", mins), ("exactly", exactly)]:
      if values:
        cursor.executemany("INSERT OR IGNORE INTO %s VALUES (%s)" % (table, ",".join("?" for i in values[0])), values)
        nb += cursor.rowcount
        #nbs[self.rule_set.tables[table]] = cursor.rowcount
    
    self.cursor.executescript("""
CREATE UNIQUE INDEX some_s       ON some(s);
CREATE UNIQUE INDEX data_value_s ON data_value(s);
CREATE UNIQUE INDEX only_s       ON only(s);
CREATE UNIQUE INDEX max_s        ON max(s);
CREATE UNIQUE INDEX min_s        ON min(s);
CREATE UNIQUE INDEX exactly_s    ON exactly(s);

CREATE INDEX some_v       ON some      (value, prop);
CREATE INDEX data_value_v ON data_value(value, prop);
CREATE INDEX only_v       ON only      (value, prop);
CREATE INDEX max_v        ON max       (value, prop);
CREATE INDEX min_v        ON min       (value, prop);
CREATE INDEX exactly_v    ON exactly   (value, prop);
""")

    flat_list_rels = set()
    for flat_list in flat_lists:
      table_name = flat_list.flat.table.name
      cursor.execute("""CREATE %s TABLE %s(s INTEGER NOT NULL, o INTEGER NOT NULL)""" % (self.temporary, table_name))
      cursor.execute("""CREATE UNIQUE INDEX %s_so ON %s(s,o)""" % (table_name, table_name))
      
      self.sql_destroy += """DROP TABLE flat_lists_%s;\n""" % flat_list.rel
      
      cursor.execute("""INSERT OR IGNORE INTO %s SELECT s,o FROM tmpquads WHERE p=?""" % table_name, (flat_list.rel,))
      nb += cursor.rowcount
      nbs[flat_list.flat.table] = cursor.rowcount
      
      cursor.execute("""CREATE INDEX %s_os ON %s(o,s)""" % (table_name, table_name))

      flat_list_rels.add(flat_list.rel)
      
    if self.explain:
      self.cursor.execute("""INSERT INTO explanations SELECT 'flat_lists_37', s, group_concat(o), 'assertion', '' FROM flat_lists_37 GROUP BY s""")
      
    cursor.execute("""DROP TABLE tmpnorm""")
    cursor.execute("""DROP TABLE tmpquads""")
    
    if owl_unionof in flat_list_rels:
      if owl_intersectionof in flat_list_rels:
        cursor.execute("""CREATE %s VIEW flat_lists_292 AS SELECT * FROM flat_lists_30 UNION ALL SELECT * FROM flat_lists_31""" % self.temporary)
      else:
        cursor.execute("""CREATE %s VIEW flat_lists_292 AS SELECT * FROM flat_lists_30""" % self.temporary)
    elif owl_intersectionof in flat_list_rels:
      cursor.execute("""CREATE %s VIEW flat_lists_292 AS SELECT * FROM flat_lists_31""" % self.temporary)
    else:
      cursor.execute("""CREATE %s TABLE flat_lists_292(s INTEGER, o INTEGER)""" % self.temporary)
      
    # Reset due to insertion / removal
    self.last_inferences[self.rule_set.tables["is_a"]] = self.cursor.execute("""SELECT MAX(rowid) FROM is_a""").fetchone()[0]
    
    return nb, nbs

  
  
  def _get_constructs(self, include_linked = 1):
    from owlready2.class_construct import _restriction_type_2_label

    cursor = self.cursor
    class Entity(object):
      def __init__(self, s, name = None):
        self.s  = s
        self.has_superclass = False
        self.is_new = False
        self.constructs = []
        self.name = name
        
      def __str__(self):
        if self.name and not self.constructs: return self.name
        l = []
        if self.name: l.append(self.name)
        for construct in self.constructs: l.append(str(construct))
        return "%s" % ",".join(l)
      
      def check(self):
        r = cursor.execute("""SELECT 1 FROM objs WHERE s=? LIMIT 1""", (self.s,)).fetchone()
        if not r: self.is_new = True
        
    class Construct(object):
      def __init__(self, xs):
        self.xs = xs
    class AndConstruct(Construct):
      def __str__(self):
        #if len(self.xs) >= 2: return "(%s)" % (" and ".join(str(x) for x in self.xs))
        #return "(%s and)" % ("".join(str(x) for x in self.xs))
        if len(self.xs) >= 2:
            return "(%s)" % (" and ".join(repr(x) for x in self.xs))
        return "(%s and)" % ("".join(repr(x) for x in self.xs))
    class OrConstruct(Construct):
      def __str__(self):
        #if len(self.xs) >= 2: return "(%s)" % (" or ".join(str(x) for x in self.xs))
        #return "(%s or)" % ("".join(str(x) for x in self.xs))
          if hasattr(self, '_building_str'):
              return "(...)"
          self._building_str = True
          try:
              if len(self.xs) >= 2:
                  return "(%s)" % (" or ".join(str(x) for x in self.xs))
              return "(%s or)" % ("".join(str(x) for x in self.xs))
          finally:
              del self._building_str
    class DisjointConstruct(Construct):
      def __str__(self):
        if len(self.xs) >= 2: return "(%s)" % (" disjoint ".join(str(x) for x in self.xs))
        return "(%s disjoint)" % ("".join(str(x) for x in self.xs))
    class NotConstruct(Construct):
      def __str__(self):
        return "(not %s)" % (",".join(str(x) for x in self.xs))
    class RestrictionConstruct(Construct):
      def __str__(self):
        #if self.xs[0] in (SOME, ONLY):
        #  return "(%s %s %s)" % (self.xs[2], _restriction_type_2_label[self.xs[0]], self.xs[3])
        #else:
        #  return "(%s %s %s %s)" % (self.xs[2], _restriction_type_2_label[self.xs[0]], self.xs[1], self.xs[3])
          if hasattr(self, '_building_str'):
              return "(...)"
          self._building_str = True
          try:
              if self.xs[0] in (SOME, ONLY):
                  return "(%s %s %s)" % (self.xs[2], _restriction_type_2_label[self.xs[0]], self.xs[3])
              else:
                  return "(%s %s %s %s)" % (self.xs[2], _restriction_type_2_label[self.xs[0]], self.xs[1], self.xs[3])
          finally:
              del self._building_str

    s_2_entity = {}
    def get_entity(s):
      entity = s_2_entity.get(s)
      if not entity:
        if s > 0: name = self.world._unabbreviate(s).rsplit("#", 1)[-1]
        else:     name = None
        entity = s_2_entity[s] = Entity(s, name)
      return entity
    
    for table, construct_class in [("flat_lists_30", OrConstruct), ("flat_lists_31", AndConstruct), ("flat_lists_37", DisjointConstruct), ("flat_lists_87", NotConstruct)]:
      for s, os in self.cursor.execute("""SELECT s, group_concat(o) FROM %s GROUP BY s""" % table):
        entity = get_entity(s)
        entity.constructs.append(construct_class([get_entity(int(o)) for o in os.split(",")]))
    
    for table, p, has_card in [("some", SOME, False), ("only", ONLY, False), ("max", MAX, True), ("min", MIN, True), ("exactly", EXACTLY, True)]:
      for r in self.cursor.execute("""SELECT * FROM %s""" % table):
        if has_card: s, card, prop, value = r
        else:        s,       prop, value = r; card = 0
        entity = get_entity(s)
        entity.constructs.append(RestrictionConstruct([p, card, get_entity(prop), get_entity(value)]))
        
    for entity in s_2_entity.values():
      entity.check()
      
    return s_2_entity
  
  def dump_constructs(self):
    s_2_construct = self._get_constructs()
    
    print(len(s_2_construct), "constructs :")
    for s in reversed(sorted(s_2_construct)):
      construct = s_2_construct[s]
      r = str(construct)
      #if r.startswith("("): r = r[1:-1]
      s = "  %s : %s" % (s, r)
      if construct.has_superclass: s = "%s (has superclass)" % s
      
      if construct.is_new: print(s)
      else:                print("\x1B[2m%s\x1B[0m" % s)
      
    
  def dump_inferences(self):
    s_2_construct = self._get_constructs(include_linked = True)
    
    for table in self.rule_set.tables.values():
      if table.name == "objs": continue
      if table.name == "datas": continue
      if table.name == "all_objs": continue
      print()
      print("\x1B[1mTABLE '%s':\x1B[0m" % table.name)
      for row in self.cursor.execute("""SELECT * FROM %s""" % table.name).fetchall():
        orig_row = list(row)
        row      = list(row)
        
        for i in range(len(row)):
          if   row[i] is None: pass
          elif not isinstance(row[i], int): pass
          else:
            if   (table.name == "is_a") and (i == 2): pass 
            elif table.name.startswith("clause_") and (i == 2): pass # clause nb
            elif row[i] > 0:
              row[i] = self.world._unabbreviate(row[i]).split("#")[-1]
            else:
              construct = s_2_construct.get(row[i], "???")
              if construct:
                row[i] = "%s\x1B[2m:%s\x1B[0m" % (row[i], str(construct).replace("onto.", ""))
              else:
                row[i] = "%s" % (row[i])

        if self.explain and (table.name == "is_a"):
          rules = []
          rule_2_nb = defaultdict(int)

          for rule, in self.cursor.execute("""SELECT rule FROM explanations WHERE s=? AND o=?""", (orig_row[0], orig_row[1])):
            if not rule in rule_2_nb: rules.append(rule)
            rule_2_nb[rule] += 1
          l = []
          for rule in rules:
            if rule_2_nb[rule] == 1: l.append(rule)
            else:                    l.append("%s x%s" % (rule, rule_2_nb[rule]))
          row.append("   \x1B[2m%s : %s\x1B[0m" % (sum(rule_2_nb.values()), ", ".join(l)))
          
        print("   ", *row)
    print()
  ############  
  def execute_stage(self, stage):
    if self.debug:
      print()
      print("Enter stage '%s':" % stage.name)
    self.current_stage = stage
    
    self._optimize()
    
    self._candidate_completions = set(stage.initial_completions) # Need to define it before running preprocesses, because preprocesses may add candidates!
    
    for rule in stage.preprocesses:
      rule.nb_execution  = 0
      rule.total_time    = 0.0
      rule.total_matches = 0
      rule.total_hits    = 0
      self.execute_rule(rule)
      
    if self.debug:
      print()
    
    for rule in stage.completions:
      rule.nb_execution  = 0
      rule.total_time    = 0.0
      rule.total_matches = 0
      rule.total_hits    = 0
      
    while self._candidate_completions:
      l = list(self._candidate_completions)
      l.sort(key = lambda rule: (rule.priority, rule.nb_execution, rule.complexity, rule.name))
      rule = l[0]
      self._candidate_completions.remove(rule)
      self.execute_rule(rule)
      
    if self.debug:
      print()
  ############

  def run(self, x = None, debug = 1):
    locked = self.world.graph.has_write_lock()
    if locked: self.world.graph.release_write_lock() # Not needed during reasoning
    try:
      self.cursor = self.db.cursor()
      self.prepare()
  
      
      self.last_inferences = {}
      for table in self.rule_set.tables.values():
        if not self.rule_set.table_2_inferrable.get(table, None): continue
        try: nb = self.cursor.execute("""SELECT MAX(rowid) FROM %s""" % table.name).fetchone()[0] or 0
        except sqlite3.OperationalError: nb = 0
        self.last_inferences[table] = nb
        self.optimize_limits[table] = nb + 1
      if self.debug: self.check_last_inferences()
      
      self.max_restriction_depth = 1
      self.max_restriction_depth_last_update = 0
      
      for stage in self.rule_set.stages:
        if stage is self.rule_set.stages[-1]: self._optimize()
        self.execute_stage(stage)
        
      t = time.time()
      self.new_parents, self.new_equivs, self.entity_2_type = self.extract_inferences()
      self.extract_result_time = time.time() - t
      
    finally:
      if locked: self.world.graph.acquire_write_lock() # re-lock when applying results
      
    if   isinstance(x, Ontology):  ontology = x
    if CURRENT_NAMESPACES.get():   ontology = CURRENT_NAMESPACES.get()[-1].ontology
    else:                          ontology = self.world.get_ontology(_INFERRENCES_ONTOLOGY)
    
    _apply_reasoning_results(self.world, ontology, debug, self.new_parents, self.new_equivs, self.entity_2_type)
    
 
    
  """ def execute_stage(self, stage):
    if self.debug:
      print()
      print("Enter stage '%s':" % stage.name)
    self.current_stage = stage
    
    self._optimize()
    
    self._candidate_completions = set(stage.initial_completions) # Need to define it before running preprocesses, because preprocesses may add candidates!
    
    for rule in stage.preprocesses:
      rule.nb_execution  = 0
      rule.total_time    = 0.0
      rule.total_matches = 0
      rule.total_hits    = 0
      self.execute_rule(rule)
      
    if self.debug:
      print()
    
    for rule in stage.completions:
      rule.nb_execution  = 0
      rule.total_time    = 0.0
      rule.total_matches = 0
      rule.total_hits    = 0
      
    while self._candidate_completions:
      l = list(self._candidate_completions)
      l.sort(key = lambda rule: (rule.priority, rule.nb_execution, rule.complexity, rule.name))
      rule = l[0]
      self._candidate_completions.remove(rule)
      self.execute_rule(rule)
      
    if self.debug:
      print() """
    
  def execute_rule(self, rule):
    if self.debug:
      self.check_last_inferences()
      #print("Execute rule %s:" % rule)
      print("Execute rule %s..." % rule, end = "", flush = True)
      
    current_matches = rule.total_matches
    
    rule.nb_execution += 1
    t0 = time.time()
    
    if rule.recursive:
      nb_new_triples = old_n = 0
      first = True
      while True:
        n, added_nb_inferences = rule.execute(self, self.cursor)
        assert added_nb_inferences is None
        if n == 0: break
        nb_new_triples += n
        
        self._check_optimize_table(rule.table, self.last_inferences[rule.table] + nb_new_triples)
        
        if first:
          rule.last_inferences.update(self.last_inferences)
          first = False
        rule.last_inferences[rule.table] += old_n
        old_n = n
        
      if nb_new_triples:
        self.compute_completion_candidates(rule, nb_new_triples, added_nb_inferences)
        self._candidate_completions.discard(rule)
        
    else:
      #nb_new_triples, added_nb_inferences = rule.execute(self, self.cursor)
      result = rule.execute(self, self.cursor)
      if result is None:
          nb_new_triples, added_nb_inferences = 0, 0  # or whatever default values make sense
      else:
          nb_new_triples, added_nb_inferences = result
      
      if nb_new_triples:
        self.compute_completion_candidates(rule, nb_new_triples, added_nb_inferences)
      
    t = time.time() - t0
    rule.total_time += t
    rule.total_hits += nb_new_triples
    
    if self.debug:
      if nb_new_triples: 
        print("\x1B[1m %0.4fs," % t, "produced %s matches and %s hits\x1B[0m" % (rule.total_matches - current_matches, nb_new_triples))
      else:
        print("\x1B[2m %0.4fs," % t, "produced %s matches and 0 hit\x1B[0m" % (rule.total_matches - current_matches))
      self.check_last_inferences()
      
  def compute_completion_candidates(self, rule, nb_new_triples, added_nb_inferences):
    for create in rule.creates:
      for other in self.current_stage.depend_2_completions[create]:
        if not other in self._candidate_completions:
          self._candidate_completions.add(other)
          other.last_inferences.update(self.last_inferences)
            
    if added_nb_inferences:
      for table, nb in added_nb_inferences.items():
        if table in self.last_inferences:
          self.last_inferences[table] += nb
          
          self._check_optimize_table(table, self.last_inferences[table])
            
    else:
      if rule.table in self.last_inferences:
        self.last_inferences[rule.table] += nb_new_triples
        self._check_optimize_table(rule.table, self.last_inferences[rule.table])
          
    
  def _trigger_create(self, create):
    for rule in self.current_stage.depend_2_completions[create]:
      if not rule in self._candidate_completions:
        self._candidate_completions.add(rule)
        rule.last_inferences.update(self.last_inferences)
   
    
  def check_last_inferences(self):
    default_world.save()
    
    for table in self.rule_set.tables.values():
      if table in self.last_inferences:
        try:    nb = self.cursor.execute("""SELECT MAX(rowid) FROM %s""" % table.name).fetchone()[0] or 0
        except: nb = 0
        if self.last_inferences[table] != nb:
          raise RuntimeError("Inference count lost for table %s! count is %s, real is %s." % (table, self.last_inferences[table], nb))
    

    

  def extract_inferences(self):
    # Infer equivalence from double inheritance
    self.cursor.execute("""CREATE TABLE equiv (s INTEGER NOT NULL, o INTEGER NOT NULL)""")
    self.sql_destroy += """DROP TABLE equiv;"""

    self.cursor.execute("""
INSERT OR IGNORE INTO equiv
SELECT DISTINCT q1.s, q2.s
FROM is_a q1, is_a q2
WHERE q1.s=q2.o AND q2.s=q1.o AND q1.s!=q2.s AND q1.s>0 AND q2.s>0
""")

    
    new_parents   = defaultdict(list)
    new_equivs    = defaultdict(list)
    entity_2_type = {}
    for s, o in self.cursor.execute("""
WITH trivial(s,o) AS (
SELECT q1.s,q2.o
FROM is_a q1, is_a q2
WHERE q1.l=1 AND q2.s=q1.o AND q1.s > 0 AND q2.s > 0 AND q2.o > 0 AND q1.s != q1.o AND q2.s != q2.o
UNION ALL
SELECT s,o FROM objs WHERE p IN (?,?)
UNION ALL
SELECT * FROM equiv
)
SELECT s,o
FROM is_a
WHERE s > 0 AND o > 0 AND s != o AND s != ?
EXCEPT
SELECT * FROM trivial
""", (rdfs_subclassof, rdf_type, owl_nothing)):
      new_parents[s].append(o)
      
    for s, o in self.cursor.execute("""SELECT s,o FROM equiv WHERE s < o"""):
      new_equivs[s].append(o)
      new_equivs[o].append(s)
      
      
    o_2_type = { owl_class : "class", owl_object_property : "property", owl_data_property : "property", owl_named_individual : "individual" }
    entities = set(new_parents)
    entities.update(new_equivs)
    for s in entities:
      entity_2_type[s] = o_2_type[(self.cursor.execute("""SELECT o FROM types WHERE s=? LIMIT 1""", (s,)).fetchone() or (owl_class,))[0]]
      
    return new_parents, new_equivs, entity_2_type
  
  
  def print_rule_usage(self):
    for stage in self.rule_set.stages:
      print("Stage '%s':" % stage.name, file = sys.stderr)
      for rule_type, rules in [("Preprocess", stage.preprocesses), ("Completion", stage.completions)]:
        if not rules: continue
        print("  %s rules:" % rule_type, file = sys.stderr)
        for rule in sorted(rules, key = lambda rule: -rule.total_time):
          if self.debug: matches = "%s matches and " % rule.total_matches
          else:          matches = ""
          if rule_type == "Preprocess": nb_execution = ""
          else:                         nb_execution = "%s executions, " % rule.nb_execution
          if rule.total_hits: start = "\x1B[1m"
          else:               start = "\x1B[2m"
          if self.debug and hasattr(rule, "search_time"): search_time = " (%0.4fs for SQL)" % rule.search_time
          else:                                           search_time = ""
          print("%s    %s: %0.4fs%s, %sproduced %s%s hits\x1B[0m" %
                (start, rule.name, rule.total_time, search_time, nb_execution, matches, rule.total_hits), file = sys.stderr)
        print()
        
    print("Extraction des resultats: %0.4fs" % self.extract_result_time, file = sys.stderr)
    print("  New is-a ", len(dict(self.new_parents or {})), file = sys.stderr)
    print("  New equiv", len(dict(self.new_equivs or {})), file = sys.stderr)
      
    print("Extra:")
    print("  max_restriction_depth = %s" % self.max_restriction_depth)
    if self._extra_dumps:
      for k,v in self._extra_dumps.items():
        print("  %s = %s" % (k, v))
         
