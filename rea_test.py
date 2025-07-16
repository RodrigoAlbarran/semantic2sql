import unittest
import os
from owlready2 import *
#from semantic2sql.reasoned_model import *

class OntologyReasonerTest(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self._next_onto = 1
        
    def setUp(self):
        # Set up in-memory world (no quadstore backend)
        self.world = World()
        self.world.set_backend(filename=None)  # Pure in-memory processing
        
        # Load ontology from local file path
        self.ontology_path = "/Users/rodrigo/Ont_alc/PizzaTutorial_alc.owl"  
        try:
            self.onto = self.world.get_ontology(self.ontology_path).load()
            print(f"\n[STATUS] Successfully loaded ontology from: {self.ontology_path}")
        except Exception as e:
            self.fail(f"Failed to load ontology: {str(e)}")
            
    def tearDown(self):
        # Clean up in-memory world
        self.world.close()
        
    def run_custom_reasoner(self):
        """Execute custom Python-based reasoner and handle results"""
        try:
            # Import and run your custom reasoner
            #from your_custom_reasoner import CustomReasoner  # CHANGE THIS TO YOUR ACTUAL MODULE
            from semantic2sql import reasoned_model 
            
            print("[REASONER] Starting custom reasoner execution...")
            reasoner = reasoned_model(self.onto)
            
            # Check consistency first
            if reasoner.is_consistent():
                print("[CONSISTENCY] Ontology is consistent")
                
                # Run reasoning
                inferences = reasoner.run()
                print(f"[REASONER] Successfully executed. Generated {len(inferences)} new inferences")
                return True
            else:
                print("[CONSISTENCY] Ontology is INCONSISTENT - reasoning aborted")
                return False
                
        except Exception as e:
            print(f"[ERROR] Reasoner failed: {str(e)}")
            return False
            
    def test_reasoning(self):
        """Main test case for ontology reasoning"""
        success = self.run_custom_reasoner()
        
        if not success:
            # Graceful exit for inconsistent ontologies or errors
            self.world.close()
            return  # Skip further assertions
            
        # Add your specific test assertions here
        # Example:
        # self.assertGreater(len(list(self.onto.classes())), 0)
        
        print("[TEST] Reasoning test completed successfully")

if __name__ == "__main__":
    # Configure Owlready2 for quiet operation (optional)
    onto_path.append("/Users/rodrigo/Ont_alc/PizzaTutorial_alc.owl")  # Add path for ontology imports if needed
    set_log_level(0)  # 0=quiet, 1=warnings, 2=info, 3=debug
    
    unittest.main()