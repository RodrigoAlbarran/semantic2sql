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

import sys, os
from collections import defaultdict
import owlready2
from semantic2sql.reasoned_model import *

class Fact(object):
  def __init__(self, explanation, s):
    self.explanation = explanation
    self.s           = s
    self.inferences  = []
    self.useful      = False
    
  def check_useful(self): pass
  
  def set_useful(self):
    if self.useful == False:
      self.useful = True
      for inference in self.inferences:
        for source in inference.sources:
          source.set_useful()
          
  def is_trivial(self): return False
  
class IsAFact(Fact):
  def __init__(self, explanation, s, o, rowid):
    Fact.__init__(self, explanation, s)
    self.o     = o
    self.rowid = rowid

  def check_useful(self):
    if (self.o > 0) and (self.o != self.s) and (self.o != owlready2.owl_thing): self.set_useful()
  
  def is_trivial(self): return (self.s == self.o) or (self.o == owlready2.owl_thing)
    
  def html(self): return """%s <b>is a</b> %s""" % (self.explanation._render(self.s), self.explanation._render(self.o))
    
class DisjointFact(Fact):
  def __init__(self, explanation, s, xs):
    Fact.__init__(self, explanation, s)
    self.xs = xs
    
  def html(self): return """%s <b>pairwise disjoint</b> """ % (", ".join(str(self.explanation._render(x)) for x in self.xs))
  
class Inference(object):
  def __init__(self, fact, rule, sources):
    self.fact    = fact
    self.rule    = rule
    self.sources = sources

    
class HTMLExplanation(object):
  def __init__(self, model, display_trivial_facts = True, only_forward = False):
    self.model = model
    self.only_forward = only_forward
    
    self.title = "Semantic2SQL Explanations"
    self.s_2_construct = self.model._get_constructs()
    
    rowid_2_s_o = {}
    s_o_2_rowid = {}
    for rowid, s, o in self.model.cursor.execute("""SELECT rowid,s,o FROM is_a""").fetchall():
      rowid_2_s_o[rowid] = (s, o)
      s_o_2_rowid[s, o]  = rowid
      
    self.facts = []
    s_2_disjoint    = {}
    s_o_2_is_a_fact = {}
    self.s_2_is_a_fact = {}
    for table, s, o, rule, sources in self.model.cursor.execute("""SELECT t,s,o,rule,sources FROM explanations""").fetchall():
      if s == owlready2.owl_nothing: continue
      if rule == "equivalence": rule = "assertion"
      
      if   table == "is_a":
        fact = s_o_2_is_a_fact.get((s, o))
        if not fact:
          fact = s_o_2_is_a_fact[s, o] = IsAFact(self, s, o, s_o_2_rowid[s, o])
          self.facts.append(fact)
          for s in [fact.s, fact.o]:
            if not s in self.s_2_is_a_fact: self.s_2_is_a_fact[s] = fact
            if s < 0:
              construct = self.s_2_construct[s]
              rel = None
              if   construct.__class__.__name__ == "AndConstruct": rel = owlready2.owl_intersectionof
              elif construct.__class__.__name__ == "OrConstruct" : rel = owlready2.owl_unionof
              if rel:
                for o, in self.model.cursor.execute("""SELECT o FROM flat_lists_%s WHERE s=?""" % rel, (s,)).fetchall():
                  if o < 0:
                    if (not o in self.s_2_is_a_fact) or (fact.rowid < self.s_2_is_a_fact[o].rowid):
                      self.s_2_is_a_fact[o] = fact
                      
      elif table == "flat_lists_37": # Disjoint
        fact = s_2_disjoint.get(s)
        if not fact:
          xs = [int(x) for x in o.split(",")]
          fact = s_2_disjoint[s] = DisjointFact(self, s, xs)
          self.facts.append(fact)
          
      sources2 = []

      if sources:
        for source in sources.split(","):
          table, rowid = source.split(":")
          if   table == "is_a":
            s, o = rowid_2_s_o[int(rowid)]
            source = s_o_2_is_a_fact.get((s, o))
            
          elif table in {"flat_lists_30", "flat_lists_31", "linked_lists_30", "linked_lists_31"}: # And/Or
            s = self.model.cursor.execute("""SELECT s FROM %s WHERE rowid=? LIMIT 1""" % table, (rowid,)).fetchone()[0]
            source = self.s_2_is_a_fact.get(s)
            
          elif table == "flat_lists_37": # Disjoint
            s = self.model.cursor.execute("""SELECT s FROM flat_lists_37 WHERE rowid=? LIMIT 1""", (rowid,)).fetchone()[0]
            source = s_2_disjoint.get(s)
            
          else: continue
          
          if source:
            if not source in sources2: sources2.append(source)
          else:
            print("MISSING SOURCE: %s:%s !" % (table, rowid))
            
      if only_forward:
        for source in sources2:
          if source.rowid > fact.rowid:
            not_forward = True
            break
        else: not_forward = False
        if not_forward: continue
        
      fact.inferences.append(Inference(fact, rule, sources2))

    for fact in self.facts: fact.check_useful()
    
    if display_trivial_facts:
      self.displayed_facts = list(self.facts)
    else:
      self.displayed_facts = [fact for fact in self.facts if not fact.is_trivial()]
      
    for fact in self.displayed_facts:
      if isinstance(fact, IsAFact):
        for s in [fact.s, fact.o]:
          if not s in self.s_2_is_a_fact: self.s_2_is_a_fact[s] = fact
    for fact in self.displayed_facts:
      if isinstance(fact, IsAFact):
        for s in [fact.s, fact.o]:
          if s < 0:
            construct = self.s_2_construct[s]
            rel = None
            if   construct.__class__.__name__ == "AndConstruct": rel = owlready2.owl_intersectionof
            elif construct.__class__.__name__ == "OrConstruct" : rel = owlready2.owl_unionof
            if rel:
              for o, in self.model.cursor.execute("""SELECT o FROM flat_lists_%s WHERE s=?""" % rel, (s,)).fetchall():
                if o < 0:
                  if (not o in self.s_2_is_a_fact) or (fact.rowid < self.s_2_is_a_fact[o].rowid):
                    self.s_2_is_a_fact[o] = fact
                  
    self.displayed_facts_set = set(self.displayed_facts)
    
    
  def _render(self, s):
    if s < 0: return self.s_2_construct[s]
    name = self.model.world._unabbreviate(s)
    if "#" in name: return name.rsplit("#", 1)[-1]
    return name.rsplit("/", 1)[-1]
  
  def _find_displayed_fact(self, fact):
    if fact in self.displayed_facts_set: return fact
    return self.s_2_is_a_fact.get(fact.s)
    
  def get_html(self):
    for i, fact in enumerate(self.displayed_facts): fact.i = i
    
    sources_i_2_facts = defaultdict(list)
    for fact in self.displayed_facts:
      for inference in fact.inferences:
        if inference.rule == "assertion": continue
        sources_i = set()
        for source in inference.sources:
          source = self._find_displayed_fact(source)
          if source and hasattr(source, "i"): sources_i.add(source.i)
        sources_i_2_facts[frozenset(sources_i)].append(fact)
        
    arrowss = []
    sources_i_facts = []
    for sources_i, facts in sources_i_2_facts.items():
      if len(facts) > 1:
        if not sources_i.isdisjoint({fact.i for fact in facts}):
          for fact in facts:
            sources_i_facts.append((sources_i, [fact]))
          continue
      sources_i_facts.append((sources_i, facts))
      
    sources_i_facts = []
    for fact in self.displayed_facts:
      for inference in fact.inferences:
        if inference.rule == "assertion": continue
        sources_i = set()
        for source in inference.sources:
          source = self._find_displayed_fact(source)
          if source and hasattr(source, "i"): sources_i.add(source.i)
        inferences_i = { fact.i }
        all_i = sources_i | inferences_i
        min_i, max_i = min(all_i), max(all_i)
        if min_i == max_i: continue # No sources
        sources_i_facts.append((sources_i, [fact]))
        
    for sources_i, facts in sources_i_facts:
        inferences_i = { fact.i for fact in facts }
        all_i = sources_i | inferences_i
        min_i, max_i = min(all_i), max(all_i)
        if max_i - min_i + 1 <= len(inferences_i): continue # No sources
        
        for arrows in arrowss:
          for i in range(min_i, max_i + 1):
            if arrows[i][0]: break
          else:
            break
        else:
          arrows = [[set(), ""] for i in range(len(self.displayed_facts))]
          arrowss.append(arrows)
          #arrowss.insert(0, arrows)
          
        for i in range(min_i, max_i + 1):
          arrows[i][0].update(facts)
          if   i in inferences_i:
            if   i == min_i:   arrows[i][1] = "╒>"
            elif i == max_i:   arrows[i][1] = "╘>"
            else:              arrows[i][1] = "╞>"
          elif i in sources_i:
            if   i == min_i:   arrows[i][1] = "┌─"
            elif i == max_i:   arrows[i][1] = "└─"
            else:              arrows[i][1] = "├─"
          else:                arrows[i][1] = "│ "

    
    fact_2_arrow_strs = {}
    for fact in self.displayed_facts:
      fact_arrowss = [
        [[fs, s] if fact in fs else [set(), ""] for fs, s in arrows]
        for arrows in arrowss
        ]
      for arrows in fact_arrowss:
        for i in range(len(arrows)):
          if i != fact.i:
            arrows[i][1] = arrows[i][1].replace("╞", "│").replace("╘", " ").replace("╒", " ").replace(">", " ")
      for arrows in fact_arrowss:
        for i in range(len(arrows) - 1):
          if arrows[i][1].startswith(" "):
            if   arrows[i + 1][1].startswith("│"):
              arrows[i + 1][1] = arrows[i + 1][1].replace("│", " ")
            elif arrows[i + 1][1].startswith("╞"):
              arrows[i + 1][1] = arrows[i + 1][1].replace("╞", "╒")
        for i in reversed(range(len(arrows) - 1)):
          if arrows[i + 1][1].startswith(" "):
            if   arrows[i][1].startswith("│"):
              arrows[i][1] = arrows[i][1].replace("│", " ")
            elif arrows[i][1].startswith("╞"):
              arrows[i][1] = arrows[i][1].replace("╞", "╘")
              
      fact_2_arrow_strs[fact] = self._extend_arrowss(fact_arrowss).split("\n")
      
    arrow_strs = self._extend_arrowss(arrowss).split("\n")

    html = """<script>
arrow_strs = %s;
fact_arrow_strs = %s;

function show_arrow(strs) {
  for (var i = 0; i < strs.length; i++) {
    var pre = document.getElementById("pre" + i);
    pre.innerHTML = strs[i]
  }
}
</script>
""" % (arrow_strs, [fact_2_arrow_strs[fact] for fact in self.displayed_facts])
    
    html += """<div>\n"""
    html += """<table cellspacing="0" cellpadding="0">\n"""
    html += """<tr><th><div onclick="show_arrow(arrow_strs);" style="font-weight: normal; margin-bottom: 0.4em; margin-left: 0.4em; margin-right: 0.4em; border-bottom: 1px solid transparent;" class="clickable">(show all)</div></th>
<th><div style="margin-bottom: 0.4em; margin-left: 0.4em; margin-right: 0.4em; border-bottom: 1px solid black;">Facts</div></th>
<th><div style="margin-bottom: 0.4em; margin-left: 0.4em; margin-right: 0.4em; border-bottom: 1px solid black;">Rules</div></th>
</tr>\n"""
    
    nb_matches = nb_inferences = 0
    for fact, arrow_str in zip(self.displayed_facts, arrow_strs):
      html += "<tr>"
      
      color = "white"
      fact_nb_matches = 0
      rule_2_nb = defaultdict(int)
      rules = []
      for inference in fact.inferences:
        if inference.rule == "assertion":
          color = "#DDDDDD"
        else:
          nb_matches += 1
          fact_nb_matches += 1
          if not inference.rule in rule_2_nb: rules.append(inference.rule)
          rule_2_nb[inference.rule] += 1
      if color == "white": nb_inferences += 1
      
      html += """<td style="background-color: %s;"><pre id="pre%s" style="margin: 0px; font-size: 140%%;">%s</pre></td>""" % (color, fact.i, arrow_str)

      extra = ""
      if (color == "white") and (not fact.useful): extra += "color: #999999;"
      html += """<td onclick="show_arrow(fact_arrow_strs[%s]); event.stopPropagation();" class="clickable" style="background-color: %s; %spadding-left: 0.4em; padding-right: 0.4em;">%s</td>""" % (fact.i, color, extra, fact.html())
      
      rules2 = []
      for rule in rules:
        if rule_2_nb[rule] == 1: rules2.append(rule)
        else:                    rules2.append("%s ×%s" % (rule, rule_2_nb[rule]))
        
      if   fact_nb_matches == 0: color = "#DDDDDD"
      elif fact_nb_matches == 1: color = "white"
      elif fact_nb_matches == 2: color = "#F0F0BB"
      elif fact_nb_matches == 3: color = "#FFDDBB"
      else:                      color = "#FFC8C8"
      if fact_nb_matches: s = "%s : %s" % (fact_nb_matches, ", ".join(rules2))
      else:               s = ""
      html += """<td style="background-color: %s; padding-left: 0.4em; padding-right: 0.4em;">%s</td>""" % (color, s)
      
      html += "</tr>\n"

    if not self.only_forward:
      #html += """<tr><td></td><td></td><td style="padding-top: 0.4em; padding-left: 0.4em; padding-right: 0.4em;">Total: %s matches, %s inferred facts (ratio: %.1f%%).</td></tr>\n""" % (nb_matches, nb_inferences, 100.0 * nb_inferences / nb_matches)
      html += """<tr><td></td><td></td>
<td><div style="margin-top: 0.6em; padding-top: 0.4em; padding-left: 0.4em; padding-right: 0.4em; border-top: 1px solid black;">
Total: %s matches, %s inferred facts (ratio: %.1f%%).
</div></td></tr>\n""" % (nb_matches, nb_inferences, 100.0 * nb_inferences / nb_matches)
      
    html += "</table></div>\n"
    return html

  def _extend_arrowss(self, arrowss):
    if not arrowss: return ""
    in_arrows = [False for arrows in arrowss]
    for j in range(len(arrowss[0])):
      in_arrow = False
      for i in range(len(arrowss)):
        arrow = arrowss[i][j]
        if   arrow[1].endswith("─"): in_arrow = True
        elif in_arrow:
          if   arrow[1] == "": arrow[1] = "──"
          elif arrow[1].endswith(" "):
            arrow[1] = arrow[1][0] + "-"
            
    s = "\n".join(
      "".join(x[1] or "  " for x in s)
      for s in zip(*arrowss)
    )
    
    s = s.replace("-─", "──")
    while True:
      s2 = s.replace("> ", "═>")
      if s2 == s: break
      s = s2
    #s = s.replace(">╞", "═╞").replace(">╒", "═╒").replace(">╘", "═╘")
    return s
  

  def get_html_with_header(self):
    html= """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html>
<head>
<title>%s</title>
<meta charset="utf-8"/>
<style>
.clickable:hover {
  text-decoration: underline;
  color: black;
}
</style>
</head>
<body>
%s
</body>
</html>""" % (self.title, self.get_html())
    return html
    
  def show(self, sleep_time = 5.0):
    import os, os.path, webbrowser, tempfile, time
    tmpdir = tempfile.TemporaryDirectory(prefix = "tmp_semantic2sql_")
    
    #for filename in ["rainbowbox.css", "rainbowbox.js", "rainbowbox_max_2_elements.js"]:
    #  f = open(os.path.join(tmpdir.name, filename), "w")
    #  f.write(open(os.path.join(os.path.dirname(__file__), "static", filename)).read())
    #  f.close()
      
    filename = os.path.join(tmpdir.name, "semantic2sql_explanations.html")
    f = open(filename, "wb")
    f.write(self.get_html_with_header().encode("utf8"))
    f.close()
    webbrowser.open_new_tab("file://%s" % filename)
    if sleep_time: time.sleep(sleep_time)
    return tmpdir
    
