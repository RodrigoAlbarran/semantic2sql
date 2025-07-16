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
from collections import defaultdict


class Member(object):
  def __init__(self, table, i, column):
    self.table  = table
    self.i      = int(i)
    self.column = column
    
  def __repr__(self): return "%s_%s.%s" % (self.table, self.i, self.column)
  
  def __eq__(self, other): return (self.table == other.table) and (self.i == other.i) and (self.column == other.column)
  
  def __hash__(self): return hash((self.table, self.i, self.column))
  
  @staticmethod
  def split_member(s):
    s, column = s.strip().split(".", 1)
    if s[-1] in "0123456789":
      table, i = s.rsplit("_", 1)
    else:
      table, i = s, 0
    return Member(table, i, column)

  
class QueryRelations(object):
  def __init__(self):
    self.rels = set()
    
  def __repr__(self):
    return ", ".join("%s = %s" % (a, b) for a, b in self.rels)
  
  def add_relation(self, a, b):
    self.rels.add(frozenset([a, b]))

  def find_pattern(self, pattern, debug = False):
    pattern_rels = [frozenset([Member.split_member(x) for x in s.split("=")]) for s in pattern.split(",")]

    pattern_table_2_i = defaultdict(set)
    for rel in pattern_rels:
      for member in rel:
        pattern_table_2_i[member.table].add(member.i)
    tables = list(pattern_table_2_i.keys())
    
    rels_table_2_i = defaultdict(set)
    for rel in self.rels:
      for member in rel:
        for table in tables:
          if member.table.startswith(table):
            rels_table_2_i[table].add(member.i)
            
    for table in tables:
      if len(rels_table_2_i[table]) < len(pattern_table_2_i[table]): return []

    if debug:
      print("RELS", self.rels)
      print("PATTERN", pattern_rels)
      
    to_matches = []
    for table, li in pattern_table_2_i.items():
      for i in li:
        constraints = []
        for rel in pattern_rels:
          rel = tuple(rel)
          for a, b in [rel, reversed(rel)]:
            if (a.table == table) and (a.i == i):
              constraints.append((a, b))
              
        to_matches.append((table, i, constraints))
    
    rel_i_2_table = { member.i : member.table for rel in self.rels for member in rel }
    
    full_matches = []
    def try_match(matches, reverse_matches, next_to_match = 0):
      to_match = to_matches[next_to_match]
      
      for candidate_i in rels_table_2_i[to_match[0]]:
        if candidate_i in matches: continue
        
        ok = True
        for constraint in to_match[2]:
          a, b = constraint
          candidate_table = rel_i_2_table[candidate_i]
          a_matched = Member(candidate_table, candidate_i, a.column)

          b_candidate_i = reverse_matches.get((b.table, b.i))
          if b_candidate_i:
            b_matched = Member(rel_i_2_table[b_candidate_i], b_candidate_i, b.column)
            if not frozenset([a_matched, b_matched]) in self.rels:
              ok = False
              break
        if not ok: continue
        
        new_matches = matches.copy()
        new_matches[candidate_i] = to_match
        
        new_reverse_matches = reverse_matches.copy()
        new_reverse_matches[to_match[0], to_match[1]] = candidate_i
        if next_to_match + 1 < len(to_matches):
          try_match(new_matches, new_reverse_matches, next_to_match + 1)
        else:
          full_matches.append(new_matches)
    try_match({}, {})
        
    r = []
    for full_match in full_matches:
      d = {}
      r.append(d)
      for matched, to_match in full_match.items():
        if to_match[1] == 0:
          d[to_match[0]] = "%s_%s" % (rel_i_2_table[matched], matched)
        else:
          d["%s_%s" % (to_match[0], to_match[1])] = "%s_%s" % (rel_i_2_table[matched], matched)
    return r
    


if __name__ == "__main__":
  rels = QueryRelations()
  rels.add_relation(Member("is_a", 1, "o"), Member("only", 2, "s"))
  rels.add_relation(Member("only", 2, "value"), Member("is_a", 3, "s"))
  
  matches = rels.find_pattern("""is_a.o = only.s""")
  for i in matches:
    print(i)
