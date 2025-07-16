from owlready2 import *
import sys, os, unittest, tempfile, atexit, types
from collections import defaultdict
from semantic2sql.rule import *
from semantic2sql.reasoned_model import *
#from semantic2sql.ont2bd import *

# sys.setrecursionlimit(10**6)

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

class ReasonedModelWithSave(ReasonedModel):
    def __init__(self, world, rule_set=None, temporary=True, debug=False, explain=False, save_path="/Users/rodrigo/Ont"):
        super().__init__(world, rule_set, temporary, debug, explain)
        self.save_path = save_path
        
    def _save_database(self):
        """Save the current database state to a file before destruction"""
        if not self.save_path:
            return
            
        try:
            # Create a connection to the new database file
            backup_db = sqlite3.connect(self.save_path)
            
            # Use SQLite's backup functionality to copy the database
            with backup_db:
                self.db.backup(backup_db)
                
            print(f"\nDatabase saved to {self.save_path}")
        except Exception as e:
            print(f"\nFailed to save database: {str(e)}")

    def destroy(self):
        """Override destroy to save before dropping tables"""
        self._save_database()  # Save before destruction
        super().destroy()

class BaseTest(unittest.TestCase):
    def __init__(self, args):
        unittest.TestCase.__init__(self, args)
        self._next_onto = 1
        
    def setUp(self):
        # Clear any existing world
        self.world = World()
        if KEEP:
            try: os.unlink("/tmp/test_quadstore.sqlite3")
            except: pass
            self.world.set_backend(filename = "/tmp/test_quadstore.sqlite3")
            
        # Load your ontology
        self.onto = self.world.get_ontology("/Users/rodrigo/Ont/PizzaTutorial.owl").load()

        # Initialize the reasoned model tables
        temp_rm = ReasonedModelWithSave(self.world, rule_set=RULES_FILE, temporary=True)
        temp_rm.prepare()
        temp_rm.destroy()

    def tearDown(self):
        if KEEP: 
            self.world.save()
            
        if EXPLAIN:
            import semantic2sql.html_explain
            explanation = semantic2sql.html_explain.HTMLExplanation(self.rm)
            explanation.show()
            
    def sync_reasoner(self, consistent=True, save_path=None):
        print("Initializing ReasonedModel...")
        rm = self.rm = ReasonedModelWithSave(
            self.world, 
            rule_set=RULES_FILE, 
            temporary=not KEEP, 
            debug=DEBUG, 
            explain=EXPLAIN,
            save_path=save_path  # Pass the save path
        )
        print("ReasonedModel initialized, running reasoner...")
        
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

    # [Keep all the assert methods from the original class]
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

#def reasoned_model_with_save(world, rule_set=None, temporary=True, debug=False, explain=False, save_path=):
 #   """Factory function to create a ReasonedModelWithSave instance"""
  #  return ReasonedModelWithSave(world, rule_set=rule_set, temporary=temporary, debug=debug, explain=explain, save_path=save_path)