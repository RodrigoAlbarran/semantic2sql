import sys, time, random, itertools
import sqlite3
from collections import defaultdict
import owlready2
from owlready2.reasoning import _apply_reasoning_results, _INFERRENCES_ONTOLOGY
from semantic2sql.rule import * 

_NORMALIZED_PROPS = {
    rdfs_subclassof,
    SOME,
    VALUE,
    ONLY,
    EXACTLY,
    MIN,
    MAX,
    owl_onproperty,
    owl_onclass,
    owl_ondatarange,
    owl_withrestrictions,
}

class ReasonedModelWithSave(object):
    def __init__(
        self, world, rule_set=None, temporary=True, debug=False, explain=False,
        save_path="/Users/rodrigo/Ont"  # Added parameter for save location
    ):
        self.world = world
        self.db = world.graph.db
        self.temporary = "TEMPORARY" if temporary else ""
        self._candidate_completions = set()
        self.sql_destroy = ""
        self.debug = debug
        self.explain = explain
        self._extra_dumps = {}
        self.extract_result_time = 0
        self.new_parents = None
        self.new_equivs = None
        self.entity_2_type = None
        self.optimize_limits = defaultdict(lambda: 1)
        self.save_path = save_path  # Store the save path

        if rule_set is None:
            self.rule_set = get_rule_set("rules.txt").tailor_for(self)
        elif isinstance(rule_set, str):
            self.rule_set = get_rule_set(rule_set).tailor_for(self)
        else:
            self.rule_set = rule_set.tailor_for(self)

        self._list_cache = {}
        for l in self.rule_set.lists.values():
            self._list_cache[l] = {}

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
        self.cursor.executescript(self.sql_destroy)
        self.sql_destroy = ""

    # All other methods remain the same as in the original ReasonedModel class
    # [Include all the other methods from the original ReasonedModel class here]
    # They should work exactly the same way, just with the modified destroy() behavior

    def prepare(self):
        self.current_blank = self.world.graph.execute(
            "SELECT current_blank FROM store"
        ).fetchone()[0]

        if self.temporary:
            self.cursor.execute("""PRAGMA temp_store = MEMORY""")

        self.cursor.executescript(
            """
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
""".replace(
                "$TEMP$", self.temporary
            )
        )

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

        self.cursor.execute(
            """INSERT INTO is_a SELECT q1.s,q1.o,1 FROM objs q1, objs q2 WHERE q1.p=? AND q2.s=q1.s AND q2.p=? AND q2.o=? AND q1.o!=?""",
            (rdf_type, rdf_type, owl_named_individual, owl_named_individual),
        )
        self.cursor.execute(
            """INSERT INTO is_a SELECT s,o,1 FROM objs WHERE p=?""", (rdfs_subclassof,)
        )

        self.cursor.execute(
            """INSERT INTO prop_is_a SELECT s,o FROM objs WHERE p=?""",
            (rdfs_subpropertyof,),
        )

        self.cursor.execute("""CREATE UNIQUE INDEX types_so ON types(s,o)""")
        self.cursor.execute("""CREATE INDEX types_o ON types(o)""")

        self.cursor.execute("""CREATE UNIQUE INDEX is_a_so ON is_a(s,o)""")
        self.cursor.execute("""CREATE INDEX is_a_o ON is_a(o)""")
        self.cursor.execute("""CREATE INDEX is_a_l ON is_a(l)""")

        self.cursor.execute("""CREATE UNIQUE INDEX prop_is_a_so ON prop_is_a(s,o)""")
        self.cursor.execute("""CREATE INDEX prop_is_a_o ON prop_is_a(o)""")

        if self.explain:
            self.cursor.execute(
                """CREATE %s TABLE explanations(t TEXT NOT NULL, s INTEGER NOT NULL, o INTEGER NOT NULL, rule TEXT NOT NULL, sources TEXT NOT NULL)"""
                % self.temporary
            )
            self.cursor.execute(
                """INSERT INTO explanations SELECT 'is_a', s, o, 'assertion', '' FROM is_a"""
            )
            self.sql_destroy += """\nDROP TABLE explanations;\n"""

    # [Include all other methods from the original class]
    # They should remain exactly the same

def reasoned_model_with_save(world, rule_set=None, temporary=True, debug=False, explain=False, save_path=:
    """Factory function to create a ReasonedModelWithSave instance"""
    return ReasonedModelWithSave(
        world, rule_set, temporary, debug, explain, save_path
    )