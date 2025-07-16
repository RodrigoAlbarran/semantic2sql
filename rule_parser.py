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

from collections import defaultdict
import owlready2.rply as rply
import owlready2
from owlready2.rply import Token

lexer = parser = None

def get_parsers():
  global lexer, parser
  if lexer: return lexer, parser
  
  lg = rply.LexerGenerator()
  lg.add("{", r"\{")
  lg.add("}", r"\}")
  #lg.add(".", r"\.")
  lg.add("STAGE", r"STAGE\b")
  lg.add("RULE_DECL", r"PREPROCESS\b")
  lg.add("RULE_DECL", r"COMPLETION\b")
  lg.add("BUILTIN", r"BUILTIN\b")
  #lg.add("BUILTINTYPE", r"[a-zA-Z0-9_]*?")
  lg.add("INFER", r"INFER\b")
  lg.add("INFER", r"ASSERT\b")
  lg.add("RAISE", r"RAISE\b")
  lg.add("IF", r"IF\b")
  lg.add("IF", r"OR\b")
  lg.add("OPTION", r"HIGHEST_PRIORITY\b")
  lg.add("OPTION", r"HIGH_PRIORITY\b")
  lg.add("OPTION", r"LOW_PRIORITY\b")
  lg.add("OPTION", r"LOWEST_PRIORITY\b")
  lg.add("OPTION", r"RECURSIVE\b")
  
  lg.add("OPERATOR", r'and/or\b')
  lg.add("OPERATOR", r'and\b')
  lg.add("OPERATOR", r'or\b')
  lg.add("OPERATOR", r'not\b')
  lg.add("OPERATOR", r'inverse\b')
  lg.add("OPERATOR", r'pairwise_disjoint\b')
  lg.add("RESTR_TYPE", r'some\b')
  lg.add("RESTR_TYPE", r'only\b')
  lg.add("RESTR_TYPE", r'value\b')
  #lg.add("RESTR_TYPE", r'min\b')
  #lg.add("RESTR_TYPE", r'max\b')
  lg.add("RESTR_TYPE", r'exactly\b')
  lg.add("NEW", r'new\b')
  #lg.add("REST", r'\.\.\.')
  
  lg.add("FLOAT", r"-[0-9]*\.[0-9]+")
  lg.add("FLOAT", r"[0-9]*\.[0-9]+")
  lg.add("INT", r"-[0-9]+")
  lg.add("INT", r"[0-9]+")
  lg.add("STR", r'".*?"')
  lg.add("STR", r"'.*?'")
  lg.add("BOOL", r"true\b")
  lg.add("BOOL", r"True\b")
  lg.add("BOOL", r"false\b")
  lg.add("BOOL", r"False\b")
  lg.add("VAR", r"\?[a-zA-Z0-9][a-zA-Z0-9_]*")
  lg.add("VAR", r"\?\.\.\.")
  lg.add("IRI", r'<[a-zA-Z0-9_:/.#-]+>')
#  lg.add("IRI", r'is_a_1\b')
#  lg.add("IRI", r'is_a_2\b')
#  lg.add("IRI", r'is_a_3\b')
#  lg.add("IRI", r'is_a_4\b')
#  lg.add("IRI", r'is_a_5\b')
#  lg.add("IRI", r'is_a_6\b')
  lg.add("IRI", r'is_a\(!?<?>?=?[0-9]+\)')
  lg.add("IRI", r'is_a\b')
  lg.add("IRI", r'NOT_is_a\b')
  lg.add("IRI", r'type\b')
  lg.add("IRI", r'subclass_of\b')
  lg.add("IRI", r'subproperty_of\b')
  lg.add("IRI", r'equivalent_class\b')
  lg.add("IRI", r'equivalent_property\b')
  lg.add("IRI", r'Thing\b')
  lg.add("IRI", r'Nothing\b')
  lg.add("IRI", r'Class\b')
  lg.add("IRI", r'NamedIndividual\b')
  lg.add("IRI", r'ObjectProperty\b')
  lg.add("IRI", r'DataProperty\b')
  lg.add("IRI", r'DatatypeProperty\b')
  lg.add("IRI", r'FunctionalProperty\b')
  lg.add("IRI", r'disjoint_with\b')
  lg.add("IRI", r'disjoint_member\b')
  lg.add("IRI", r'is_a_construct\b')
  lg.add("IRI", r'domain\b')
  lg.add("IRI", r'range\b')
  lg.add("IRI", r'=')
  lg.add("IRI", r'!=')
  lg.add("IRI", r'>')
  lg.add("IRI", r'<')
  lg.add("IRI", r'>=')
  lg.add("IRI", r'<=')
  lg.add("IRI", r'operands\b')
  lg.add("IRI", r'itself\b')
  lg.add("FLAG", r'infer_descendants\b')
  lg.add("FLAG", r'infer_ancestors\b')
  lg.add("FLAG", r'concrete\b')
  #lg.add("FLAG", r'exists_initially\b')
  #lg.add("IRI", r'\.\.\.')
  #lg.add("NAME", r'[a-zA-Z0-9_/.]+')
  
  lg.add("(", r'\(')
  lg.add(")", r'\)')
  
  lg.ignore(r"#.*?\n")
  lg.ignore(r"\s+")
  
  lexer = lg.build()
  pg = rply.ParserGenerator([rule.name for rule in lg.rules])
  
  @pg.production("main : ")
  def f(p): return []
  @pg.production("main : main_item main")
  def f(p):
    if p[0] is None: return p[-1]
    return [p[0]] + p[-1]
  
  @pg.production("main_item : stage")
  def f(p): return p[0]
  
  @pg.production("main_item : rule")
  def f(p): return p[0]
  
  @pg.production("stage : STAGE STR")
  def f(p): return "STAGE", None, None, p[1]
  
  @pg.production("rule : RULE_DECL options STR ifs INFER { triples }")
  def f(p):
    next_rule()
    finalize_conditionss(p[3])
    clause_vars = []
    
    for row in p[6]:
      if isinstance(row, TableRow) and (row.table_name == "is_a"):
        if len(row.xs) <= 2: raise ValueError("is_a level is missing in INFER part in rule '%s'!" % p[2])
        
    for ifs in p[3]:
      for row in ifs:
        if isinstance(row, ClauseListRow):
          for x in row.xs:
            if x.name == "VAR":
              clause_vars.append(x)
    for clause_var in clause_vars:
      for row in p[6]:
        if isinstance(row, ClauseListRow): continue
        for x in row.xs:
          if (x.name == "VAR") and (x.value == clause_var.value):
            ancestors = list(row.ancestor_rows())
            clause_ancestors = [ancestor_row for ancestor_row in ancestors if isinstance(ancestor_row, ClauseListRow)]
            if clause_ancestors:
              clause_ancestor = clause_ancestors[0]
              clause_ancestor.pattern     = ancestors[ancestors.index(clause_ancestor) - 1]
              clause_ancestor.pattern_var = x
              
    return "INFER", p[0], p[1], p[2], p[3], p[6]
  
  @pg.production("rule : RULE_DECL options STR ifs RAISE STR")
  def f(p):
    next_rule()
    finalize_conditionss(p[3])
    return "RAISE", p[0], p[1], p[2], p[3], p[5]
  
  @pg.production("rule : RULE_DECL options STR BUILTIN STR { iris }")
  def f(p):
    next_rule()
    return "BUILTIN", p[0], p[1], p[2], p[4], p[6]

  def finalize_conditionss(conditionss):
    for ifs in conditionss:
      for row in list(ifs):
        row.used_in_if()
        if isinstance(row, LinkedListRow):
          var_names = { row.xs[1].value, row.xs[2].value }
          for other in ifs:
            if isinstance(other, AdditionalCondition) and (other.xs[1].value in "<>"):
              if { other.xs[0].value, other.xs[2].value } == var_names:
                row.ordered = True
                ifs.remove(other)
                break
          
      
  
  @pg.production("ifs : ")
  def f(p): return []
  @pg.production("ifs : IF { triples } ifs")
  def f(p): return [p[2]] + p[-1]
  
  @pg.production("iris : ")
  def f(p): return []
  @pg.production("iris : IRI iris")
  def f(p): return [p[0]] + p[-1]
  
  @pg.production("options : ")
  def f(p): return []
  @pg.production("options : OPTION options")
  def f(p): return [p[0]] + p[-1]
  
  @pg.production("triples : ")
  def f(p): return []
  @pg.production("triples : triple triples")
  def f(p):
    if isinstance(p[0], list): return p[0] + p[-1]
    return [p[0]] + p[-1]
  
  @pg.production("entity : IRI")
  @pg.production("operator : OPERATOR")
  @pg.production("restr_type : RESTR_TYPE")
  @pg.production("flag : FLAG")
  def f(p):
    if p[0].value == "NOT_is_a": return "NOT_is_a"
    p[0].value        = abbrev_2_iri.get(p[0].value, p[0].value)
    iri = p[0].value[1:-1]
    if iri.startswith("http://"): p[0].storid = local_abbrevs.get(iri) or owlready2.default_world._abbreviate(iri)
    else:                         p[0].storid = 0
    p[0].parsed_value = p[0].storid
    return p[0]
  @pg.production("entity : VAR")
  def f(p):
    p[0].storid       = None
    p[0].parsed_value = p[0].value
    return p[0]
  @pg.production("entity : BOOL")
  def f(p):
    p[0].storid       = None
    p[0].parsed_value = (p[0].value == "True") or (p[0].value == "true")
    return p[0]
  @pg.production("entity : FLOAT")
  def f(p):
    p[0].storid       = None
    p[0].parsed_value = float(p[0].value)
    return p[0]
  @pg.production("entity : INT")
  def f(p):
    p[0].storid       = None
    p[0].parsed_value = int(p[0].value)
    return p[0]
  @pg.production("entity : STR")
  def f(p):
    p[0].storid       = None
    p[0].parsed_value = str(p[0].value)
    return p[0]
  @pg.production("entity : restriction")
  def f(p): return p[0]
  @pg.production("entity : operator entity")
  def f(p):
    if p[1].value == "?...": return ClauseListRow(p)
    return FlatListRow(p)
  @pg.production("entity : entity operator")
  def f(p):
    p = [p[1], p[0]]
    if p[1].value == "?...": return ClauseListRow(p)
    return FlatListRow(p)
  @pg.production("entity : entity operator entity")
  def f(p):
    if isinstance(p[2], Token) and (p[2].value == "?..."): return ClauseListRow([p[1], p[0], p[2]])
    return LinkedListRow(p)
  @pg.production("entity : ( entity )")
  def f(p): return p[1]
  
  @pg.production("restriction : entity restr_type entity")
  @pg.production("restriction : entity restr_type entity entity")
  def f(p): return RestrictionRow(p)
  
  @pg.production("triple : entity entity entity")
  def f(p):
    l = []
    if   p[1] == "NOT_is_a":
      row = NotIsARow(p)
    elif p[1].value == "=": # Var definition
      row = p[2]
      row.var_name = as_variable(p[0])
    elif p[1].value in ("!=", ">", "<", ">=", "<="):
      row = AdditionalCondition(p)
    elif abbrev_2_iri.get(p[1].value, p[1].value) in operator_2_storid:
      row = FlatListRow([p[1], p[2]])
      row.var_name = as_variable(p[0])
    else:
      row = TableRow(p)
    row.collect_rows(l)
    return l
    
  @pg.production("triple : entity flag")
  def f(p):
    l = []
    if p[-1].value == "exists_initially":
      row = AdditionalCondition([p[0], Token("IRI", ">"), Token("SPCVAR", "?_initial_blank_limit")])
    else:
      row = TableRow(p)
    row.collect_rows(l)
    return l
  
  @pg.production("triple : NEW entity")
  def f(p):
    l = []
    row = NewNode(p)
    row.collect_rows(l)
    return l
  
  parser = pg.build()
  return lexer, parser

infer_descendants = 290
infer_ancestors   = 291
andor             = 292

abbrev_2_iri = {
  "type":                "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>",
  "is_a":                "<http://www.w3.org/2000/01/rdf-schema#subClassOf>",
  "direct_is_a":         "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#direct_is_a>",
  "is_a_construct":      "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#is_a_construct>",
  "subclass_of":         "<http://www.w3.org/2000/01/rdf-schema#subClassOf>",
  "subproperty_of":      "<http://www.w3.org/2000/01/rdf-schema#subPropertyOf>",
  "equivalent_class":    "<http://www.w3.org/2002/07/owl#equivalentClass>",
  "equivalent_property": "<http://www.w3.org/2002/07/owl#equivalentProperty>",
  "disjoint_with":       "<http://www.w3.org/2002/07/owl#disjointWith>",
  "disjoint_member":     "<http://www.w3.org/2002/07/owl#members>",
  "domain":              "<http://www.w3.org/2000/01/rdf-schema#domain>",
  "range":               "<http://www.w3.org/2000/01/rdf-schema#range>",
  
  "some":                "<http://www.w3.org/2002/07/owl#someValuesFrom>",
  "only":                "<http://www.w3.org/2002/07/owl#allValuesFrom>",
  "value":               "<http://www.w3.org/2002/07/owl#hasValue>",
  #"min":                 "<http://www.w3.org/2002/07/owl#minQualifiedCardinality>",
  #"max":                 "<http://www.w3.org/2002/07/owl#maxQualifiedCardinality>",
  "exactly":             "<http://www.w3.org/2002/07/owl#qualifiedCardinality>",
  "not":                 "<http://www.w3.org/2002/07/owl#complementOf>",
  "inverse":             "<http://www.w3.org/2002/07/owl#inverseOf>",
  "and":                 "<http://www.w3.org/2002/07/owl#intersectionOf>",
  "or" :                 "<http://www.w3.org/2002/07/owl#unionOf>",
  "and/or" :             "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#andor>",
  "pairwise_disjoint"  : "<http://www.w3.org/2002/07/owl#members>",
  
  "Thing":               "<http://www.w3.org/2002/07/owl#Thing>",
  "Nothing":             "<http://www.w3.org/2002/07/owl#Nothing>",
  "Class":               "<http://www.w3.org/2002/07/owl#Class>",
  "NamedIndividual":     "<http://www.w3.org/2002/07/owl#NamedIndividual>",
  "ObjectProperty":      "<http://www.w3.org/2002/07/owl#ObjectProperty>",
  "DataProperty":        "<http://www.w3.org/2002/07/owl#DatatypeProperty>",
  "DatatypeProperty":    "<http://www.w3.org/2002/07/owl#DatatypeProperty>",
  "FunctionalProperty":  "<http://www.w3.org/2002/07/owl#FunctionalProperty>",
  
  "infer_descendants":   "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_descendants>",
  "infer_ancestors":     "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_ancestors>",
  "concrete":            "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#concrete>",
}

iri_2_table_name = {
  "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"                                    : "types",
  "<http://www.w3.org/2000/01/rdf-schema#subClassOf>"                                    : "is_a",
  "<http://www.w3.org/2000/01/rdf-schema#subPropertyOf>"                                 : "prop_is_a",
  "<http://www.w3.org/2002/07/owl#members>"                                              : "inferred_objs",
  "<http://www.w3.org/2002/07/owl#equivalentClass>"                                      : "objs",
  "<http://www.w3.org/2002/07/owl#equivalentProperty>"                                   : "objs",
  "<http://www.w3.org/2002/07/owl#disjointWith>"                                         : "objs",
  "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_descendants>" : "infer_descendants",
  "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_ancestors>" : "infer_ancestors",
  "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#concrete>" : "concrete",
}

operator_2_storid = {
  "<http://www.w3.org/2002/07/owl#unionOf>"        : owlready2.owl_unionof,
  "<http://www.w3.org/2002/07/owl#intersectionOf>" : owlready2.owl_intersectionof,
  "<http://www.w3.org/2002/07/owl#members>"        : owlready2.owl_members,
  "<http://www.w3.org/2002/07/owl#complementOf>"   : owlready2.owl_complementof,
  "<http://www.w3.org/2002/07/owl#inverseOf>"      : owlready2.owl_inverse_property,
  "<http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#andor>" : andor,
}

table_name_without_p = {
  "types",
  "is_a",
  "direct_is_a",
  "prop_is_a",
  "is_a_construct",
  "concrete",
  "infer_descendants",
  "infer_ancestors",
}

local_abbrevs = {
  "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#andor" : andor,
  "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_descendants" : infer_descendants,
  "http://www.lesfleursdunormal.fr/static/_downloads/owlready_ontology.owl#infer_ancestors" : infer_ancestors,
}

class Row(object):
  var_name   = ""
  table_name = ""
  list_id    = None
  parent_row = None
  def init_var(self, var_base):
    global _NEXT_VAR
    self.var_name = "?%s_%s" % (var_base, _NEXT_VAR)
    _NEXT_VAR += 1
    
  def get_var(self): return Token("VAR", self.var_name)

  def _repr_xs(self): return ", ".join(((isinstance(i, Token) and i.value) or repr(i)) for i in self.xs)
  def __repr__(self): return "<%s:%s  %s %s>" % (self.__class__.__name__, self.var_name, self.table_name, self._repr_xs())
  
  def collect_rows(self, l):
    for i, x in enumerate(self.xs):
      if isinstance(x, Row):
        x.collect_rows(l)
        x.parent_row = self
        self.xs[i] = x.get_var()
    l.append(self)
    
  def used_in_if(self): pass

  def ancestor_rows(self):
    a = self
    while a:
      yield a
      a = a.parent_row
  
class TableRow(Row):
  def __init__(self, p):
    if p[1].value.startswith("is_a("):
      i = p[1].value[5:-1]
      op = ""
      while i[0] in "!<>=": op += i[0]; i = i[1:]
      i = int(i)
      l = Token("INT", str(i))
      l.parsed_value = i
      l.storid = None
      if op:
        l.operator = op
        
      p[1].value = abbrev_2_iri["is_a"]
      p[1].storid = owlready2.rdfs_subclassof
      self.table_name = "is_a"
      self.xs = [p[0], *p[2:], l]
    else:
      self.table_name = iri_2_table_name.get(p[1].value, "objs")
      if self.table_name in table_name_without_p: self.xs = [p[0], *p[2:]]
      else:                                       self.xs = p
    self.depends = [p[1].storid]
    
    
class NotIsARow(Row):
  def __init__(self, p):
    self.table_name = "is_a"
    self.xs = [p[0], *p[2:]]
    self.depends = []
    
  
class RestrictionRow(Row):
  #table_name = "restrictions"
  def __init__(self, p):
    self.init_var("_restr")
    if   p[1].storid == owlready2.SOME:    self.table_name = "some"
    elif p[1].storid == owlready2.ONLY:    self.table_name = "only"
    #elif p[1].storid == owlready2.MAX:     self.table_name = "max"
    #elif p[1].storid == owlready2.MIN:     self.table_name = "min"
    elif p[1].storid == owlready2.EXACTLY: self.table_name = "exactly"
    else: raise ValueError(p)
    if len(p) == 4:
      self.xs = [p[2], p[0], p[3]]
    else:
      self.xs = [p[0], p[2]]
    self.depends = [p[1].storid]
    
  #def used_in_if(self):
  #  if self.xs[2] == 0: self.xs[2] = None
    
  def collect_rows(self, l):
    self.xs.insert(0, self.get_var())
    Row.collect_rows(self, l)
    
    
class ListRow(Row):
  pass
  
class FlatListRow(ListRow):
  def __init__(self, p):
    self.init_var("_flat")
    self.table_name = "flat_lists_%s" % operator_2_storid[p[0].value]
    self.list_id    = operator_2_storid[p[0].value]
    self.operator   =  p[0]
    self.xs         = [p[1]]
    if p[0].storid == andor:
      self.depends  = [owlready2.owl_unionof, owlready2.owl_intersectionof]
    else:
      self.depends  = [p[0].storid]
    
  def collect_rows(self, l):
    self.xs.insert(0, self.get_var())
    Row.collect_rows(self, l)
    
class LinkedListRow(ListRow):
  def __init__(self, p):
    self.init_var("_linked")
    self.table_name = "linked_lists_%s" % operator_2_storid[p[1].value]
    self.list_id    = operator_2_storid[p[1].value]
    self.operator   =  p[1]
    self.xs         = [p[0], p[2]]
    self.depends    = [p[1].storid]
    self.ordered    = False
    
  def __repr__(self): return "<%s:%s  %s %s ordered=%s>" % (self.__class__.__name__, self.var_name, self.table_name, self._repr_xs(), self.ordered)
  
  def collect_rows(self, l):
    self.xs.insert(0, self.get_var())
    Row.collect_rows(self, l)
    
class ClauseListRow(ListRow):
  def __init__(self, p):
    self.init_var("_clause")
    self.table_name  = "flat_lists_%s" % operator_2_storid[p[0].value]
    self.list_id     = operator_2_storid[p[0].value]
    self.operator    = p[0]
    self.xs          = p[1:]
    self.depends     = [p[0].storid]
    self.pattern     = None
    self.pattern_var = None
    
  def __repr__(self):
    if self.pattern_var:
      return "<%s:%s  %s %s pattern=%s pattern_var=%s>" % (self.__class__.__name__, self.var_name, self.table_name, self._repr_xs(), self.pattern, self.pattern_var.value)
    return super().__repr__()
  
  def collect_rows(self, l):
    self.xs.insert(0, self.get_var())
    Row.collect_rows(self, l)
    
  def used_in_if(self):
    if isinstance(self.xs[-1], Token) and (self.xs[-1].value == "?..."): del self.xs[-1]
    
    
class AdditionalCondition(Row):
  table_name = ""
  def __init__(self, p): self.xs = p
  

class NewNode(Row):
  table_name = ""
  def __init__(self, p): self.xs = p[1:]



def as_variable(x):
  if isinstance(x, Token) and x.name == "VAR": return x.value
  if isinstance(x, Row): return x.var_name
  raise ValueError


_NEXT_VAR = 1
def next_rule():
  global _NEXT_VAR
  _NEXT_VAR = 1
  


if __name__ == "__main__":
  import owlready2.rply as rply
  #s = open("/tmp/test.txt").read()
  s = open("./semantic2sql/rules.txt").read()
  lexer, parser = get_parsers()
  try: parseds = parser.parse(lexer.lex(s))
  except rply.LexingError  as e: raise ValueError("Cannot parse rule files, lexing error at %s near '%s'!" % (e.source_pos, s[e.source_pos:e.source_pos + 40]))
  except rply.ParsingError as e: raise ValueError("Cannot parse rule files, parsing error at %s near '%s'!" % (e.source_pos, s[e.source_pos:e.source_pos + 40]))
  
  print("\n")
  for l in parseds:
    if   l[0] == "BUILTIN":
      print(*l)
      print()
    elif l[0] == "INFER":
      print(*l[:-2])
      for ifs in l[4]:
        for row in ifs:
          if row is ifs[0]: print("  IF   ", row)
          else:             print("       ", row)
      for row in l[5]:
        if row is l[5][0]: print("  INFER", row)
        else:              print("       ", row)
      print()
    elif l[0] == "RAISE":
      print(*l)
      for ifs in l[4]:
        for row in ifs:
          if row is ifs[0]: print("  IF   ", row)
          else:             print("       ", row)
      print()
      
      
