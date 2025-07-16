import sys, time
from owlready2 import *
from semantic2sql.reasoned_model import *

CREATE_QUADSTORE = 1
if CREATE_QUADSTORE:
  try: os.unlink("/tmp/quadstore.sqlite3")
  except: pass
  default_world.set_backend(filename = "/tmp/quadstore.sqlite3", exclusive = True)
dump = 0

DEBUG = "--debug" in sys.argv

#onto = get_ontology("./owlready2/test/test.owl").load()
onto = get_ontology("./antibio_arcenciel/onto_antibio2.owl").load()
#default_world.set_backend(filename = "/home/jiba/tmp/go.sqlite3", exclusive = True)
#onto = get_ontology("http://purl.obolibrary.org/obo/go.owl").load()
if CREATE_QUADSTORE: default_world.save()


t = 0
t0 = time.time()
#rm = ReasonedModel(default_world, "rules_horn_shiq.txt", temporary = not(CREATE_QUADSTORE), debug = DEBUG)
#rm = ReasonedModel(default_world, "rules_elh.txt", temporary = not(CREATE_QUADSTORE), debug = DEBUG)
rm = ReasonedModel(default_world, "rules.txt", temporary = not(CREATE_QUADSTORE), debug = DEBUG)
#rm = ReasonedModel(default_world, temporary = not(CREATE_QUADSTORE), debug = DEBUG)

try:
  rm.run()
  t += (time.time() - t0)
  rm.print_rule_usage()
  print(t, "s", file = sys.stderr)
  
finally:
  if CREATE_QUADSTORE: default_world.save()
  

if dump:
  rm.dump_inferrences(True)

print()
print()

