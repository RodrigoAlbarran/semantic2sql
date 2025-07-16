########### First test class of the script ###########
########### Test(BaseTest) class #####################
class Test(BaseTest):
  ## Not equivalent 
   def test_and_10(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class D(Thing): is_a = [A1 & B1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, A)
    assert issubclass(D, B)

    def test_some_3(self):
        with self.onto:
            class p(ObjectProperty): pass
            class A(Thing): pass
            class A1(A): is_a = [p.some(Nothing)]
            class B(Thing): is_a = [p.some(A1)]
            class B1(B): pass
        
        rm = self.sync_reasoner()
    
        self.assert_is_a(A1.storid, Nothing.storid)
        self.assert_is_a(B1.storid, Nothing.storid)
        assert issubclass(A1, Nothing)
        assert issubclass(B1, Nothing)
    
  def test_some_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): is_a = [p.some(Nothing)]
      class B(Thing): is_a = [p.some(A1) & A]
      class B1(B): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(B1, Nothing)
    
  def test_some_5(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): is_a = [p.some(A1 & B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, Nothing)

   def test_some_only_7(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class H(Thing): is_a = [p.some(A1), p.only(B1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(H, Nothing)

   def test_and_some_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class B(Thing): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): is_a = [p.some(A & B) & C]
      class E(Thing): is_a = [p.some(A & B) | C]
      
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, Nothing)
    assert issubclass(E, C)

  def test_or_2(self):
    with self.onto:
      class C(Thing): pass
      class A(C): pass
      class B(C): pass
      class D(Thing): is_a = [A | B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, C)

  def test_or_3(self):
    with self.onto:
      class D(Thing): pass
      class A(D): pass
      class B(D): pass
      class C(D): pass
      class E(Thing): is_a = [A | B | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(E, D)

  def test_disjoint_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      AllDisjoint([A, B, C])
      
      class D(A1, B1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(D, Nothing)
    
  def test_disjoint_or_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1, B1 | C]
      
    rm = self.sync_reasoner()

    assert issubclass(M, C)

   def test_disjoint_or_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [(A1 & B1) | C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, C)
    
  def test_disjoint_or_5(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1 & (B1 | C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, C)
    
  def test_disjoint_and_1(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      
      class M(Thing): is_a = [A1 & B1]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_disjoint_and_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      
      class M(Thing): is_a = [A1 & B1 & C]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)     
  
   def test_not_0(self):
    with self.onto:
      class A(Thing): pass
      class M(Thing): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
  def test_not_1(self):
    with self.onto:
      class A(Thing): pass
      class M(A): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_not_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class C(Thing): is_a = [Not(A)]
      class M(C, A1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)

  def test_not_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class M(Thing): is_a = [Not(A1), Not(Not(A1))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)  

  def test_long_is_a_1(self):
    with self.onto:
      parents = (Thing,)
      classes = []
      for i in range(200):
        C = types.new_class("C%s" % i, parents)
        classes.append(C)
        parents = (C,)
      
    rm = self.sync_reasoner()

  def test_concrete_1(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass

      class M(Thing):
        is_a = [p.some(A)]

      m = M()
      
    rm = self.sync_reasoner()
    
    self.assert_concrete(m.storid)
    self.assert_concrete(M.storid)
    self.assert_concrete(A.storid)
    self.assert_not_concrete(A1.storid)
    self.assert_not_concrete(B.storid)
    self.assert_not_concrete(B1.storid)    

  def test_individual_1(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      AllDisjoint([A, B])
      class C(A, B): pass
      c = C()
      
    rm = self.sync_reasoner(consistent = False)
    
  def test_individual_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      a = A("a")
      A.is_a.append(OneOf([a]))
      class A1(A): pass
      class A2(A): pass
      AllDisjoint([A1, A2])
      A1()
      A2()
      
    rm = self.sync_reasoner(consistent = False)
    
  def test_individual_3(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      a = A("a")
      A.is_a.append(OneOf([a]))
      class A1(A): pass
      class A2(A): pass
      AllDisjoint([A1, A2])
      A1()
      
    rm = self.sync_reasoner()
    
  def test_individual_4(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      a1 = A("a1")
      a2 = A("a2")
      A.is_a.append(OneOf([a1, a2]))
      class A_1(A): pass
      class A_2(A): pass
      class A_3(A): pass
      AllDisjoint([A_1, A_2, A_3])
      A_1()
      A_2()
      A_3()
      
    rm = self.sync_reasoner()

  ####### Multiple inheritance tests ###########   

def test_disjoint_only_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class M(Thing): is_a = [p.only(A1), p.only(B1)]
      
      class R(Thing): equivalent_to = [p.only(Nothing)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_only_or_1(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class M(Thing): is_a = [p.only(A1), p.only(B1 | C)]
      
      class R(Thing): equivalent_to = [p.only(C)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)
    
  def test_disjoint_only_or_2(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      AllDisjoint([A, B])
      class C(Thing): pass
      class D(Thing): pass
      class M(Thing): is_a = [p.only(A1 | C), p.only(B1 | D)]
      
      class R(Thing): equivalent_to = [p.only(C | D)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, R)

    
  def test_not_0(self):
    with self.onto:
      class A(Thing): pass
      class M(Thing): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
  def test_not_1(self):
    with self.onto:
      class A(Thing): pass
      class M(A): is_a = [Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_not_2(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class C(Thing): is_a = [Not(A)]
      class M(C, A1): pass
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
   
  def test_not_3(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class Q (Thing): pass
      class R (Q): equivalent_to = [Not(A )]
      class R1(Q): equivalent_to = [Not(A1)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(R, R1)
    
  def test_not_4(self):
    with self.onto:
      class A(Thing): pass
      class A1(A): pass
      class M(Thing): is_a = [Not(A1), Not(Not(A1))]
      
    rm = self.sync_reasoner()
    
    assert issubclass(M, Nothing)
    
  def test_not_5(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(B): pass
      
      class R(Thing): equivalent_to = [(A & B) | Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_not_6(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class C(B): pass
      AllDisjoint([A, B])
      
      class R(Thing): equivalent_to = [Not(A)]
      
    rm = self.sync_reasoner()
    
    assert issubclass(C, R)
    
  def test_not_7(self):
    with self.onto:
      class A(Thing): pass
      class NA(Thing): equivalent_to = [Not(A)]
      class B(Thing): pass
      
      A .is_a.append(B)
      NA.is_a.append(B)
      
    rm = self.sync_reasoner()
    
    assert issubclass(Thing, B)
    
    
    
  def test_long_is_a_1(self):
    with self.onto:
      parents = (Thing,)
      classes = []
      for i in range(200):
        C = types.new_class("C%s" % i, parents)
        classes.append(C)
        parents = (C,)
      
    rm = self.sync_reasoner()
    
  def test_long_and_1(self):
    with self.onto:
      class A(Thing): pass
      class B(Thing): pass
      class AB(A, B): pass
      
      parents = (AB,)
      classes = []
      for i in range(200):
        Cn = types.new_class("C%s" % i, parents)
        classes.append(Cn)
        parents = (Cn,)
        
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(classes[-1], R)
    
  def test_long_and_2(self):
    with self.onto:
      class A(Thing): pass
      parents = (A,)
      classesA = []
      for i in range(200):
        An = types.new_class("A%s" % i, parents)
        classesA.append(An)
        parents = (An,)
        
      class B(Thing): pass
      parents = (B,)
      classesB = []
      for i in range(200):
        Bn = types.new_class("B%s" % i, parents)
        classesB.append(Bn)
        parents = (Bn,)
        
      class AB(classesA[-1], classesB[-1]): pass
      
      class R(Thing): equivalent_to = [A & B]
      
    rm = self.sync_reasoner()
    
    assert issubclass(AB, R)
    
  def test_long_and_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(500):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.some(C))
      
      class R(Thing): equivalent_to = [And(ands)]
      class A(Thing):
        is_a = [p.some(C) for C in classes]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    assert self.nb_inferences == 1
    
  def test_long_and_4(self):
    with self.onto:
      class p(Thing >> Thing): pass
      classes = []
      for i in range(500):
        classes.append(types.new_class("C%s" % i, (Thing,)))
        
      ands = []
      for C in classes: ands.append(p.only(C))
      
      class R(Thing): equivalent_to = [And(ands)]
      class A(Thing):
        is_a = [p.only(C) for C in classes]
        
    rm = self.sync_reasoner()
    
    assert issubclass(A, R)
    assert self.nb_inferences == 1
    


  def test_depth(self):
    with self.onto:
      class p(ObjectProperty): pass
      class A(Thing): pass
      class A2(Thing): pass

      class B(Thing): is_a = [p.some(A)]
      class C(Thing): is_a = [p.some(p.some(A))]
      class D(Thing): is_a = [p.some(B)]
      class R(Thing): equivalent_to = [p.some(A2)]
      class E(Thing): is_a = [p.some(p.some(R))]
      #class F(Thing): pass
      #E.is_a.append(p.some(F))
      #class G(Thing): pass
      #F.equivalent_to.append(p.some(G))
      
    rm = self.sync_reasoner()
    
    assert rm._restriction_depth(B.is_a[-1].storid) == 1
    assert rm._restriction_depth(C.is_a[-1].storid) == 2
    assert rm._restriction_depth(D.is_a[-1].storid) == 1
    assert rm._restriction_depth(E.is_a[-1].storid) == 3
    



  def test_eq_1(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class b(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      class C(Thing): pass
      
      B.is_a.append(b.some(C))
      
      class E1(Thing):
        equivalent_to = [p.some(A) & p.some(B) & p.some(b.some(C))]
        
      class E2(Thing):
        equivalent_to = [p.some(A) & p.some(B)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    
  def test_eq_2(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class E1(Thing):
        equivalent_to = [p.some(A1) & p.some(B1)]
        
      class E2(Thing):
        equivalent_to = [p.some(A1) & p.some(B1)]
        
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    
  def test_eq_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass
      
      class E1(Thing):
        equivalent_to = [A1 & B1 & A1]
      
      class E2(Thing):
        equivalent_to = [A1 & B1]
      
      class E3(Thing):
        equivalent_to = [p.some(A1) & B1 & p.some(A1)]
        
      class E4(Thing):
        equivalent_to = [p.some(A1) & p.some(A1)]
                
    rm = self.sync_reasoner()
    
    assert issubclass(E1, E2)
    assert issubclass(E2, E1)
    


  def test_concrete_1(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass

      class M(Thing):
        is_a = [p.some(A)]

      m = M()
      
    rm = self.sync_reasoner()
    
    self.assert_concrete(m.storid)
    self.assert_concrete(M.storid)
    self.assert_concrete(A.storid)
    self.assert_not_concrete(A1.storid)
    self.assert_not_concrete(B.storid)
    self.assert_not_concrete(B1.storid)
    
  def test_concrete_2(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B): pass

      class M(Thing):
        equivalent_to = [A & B1]
        
      m = M()
      
    rm = self.sync_reasoner()
    
    self.assert_concrete(m.storid)
    self.assert_concrete(M.storid)
    self.assert_concrete(A.storid)
    self.assert_not_concrete(A1.storid)
    self.assert_concrete(B.storid)
    self.assert_concrete(B1.storid)
    
  def test_concrete_3(self):
    with self.onto:
      class p(Thing >> Thing): pass
      class A(Thing): pass
      class A1(A): pass
      class B(Thing): pass
      class B1(B):
        is_a = [p.some(Nothing)]
        
      class M(Thing):
        equivalent_to = [A | B1]
        
      m = M()
      
    rm = self.sync_reasoner()
    
    self.assert_concrete(m.storid)
    self.assert_concrete(M.storid)
    self.assert_concrete(A.storid)
    self.assert_not_concrete(A1.storid)
    self.assert_not_concrete(B.storid)
    self.assert_not_concrete(B1.storid)
  

######################################################

########### Second test class of the script ###########
########### Test(BaseTest) class #####################

class Exp(BaseTest):

  def test_yyy(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(6):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
    rm = self.sync_reasoner()




  def test_xxx1(self): # Fonctionne mais lent...
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [#random.p1.some(random.C3),
                         random.p2.only(random.C1 & random.C2 & random.C3 & random.p1.some(random.C1)),
      ]
      random.C3.is_a =  [random.C1]
      random.C4.is_a =  [random.C1,
                         random.C2,
                        (random.p1.some(random.C1) & random.C1) | (random.C3),
                         random.p2.some(random.C1),
      ]
      
    rm = self.sync_reasoner()


  def test_xxx2(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(8):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C3 & random.C2)]
      random.C3.is_a =  [random.C1]
      random.C4.is_a =  [random.C2]
      random.C6.is_a =  [random.p1.some(random.C1 & random.C2)]
      random.C7.is_a =  [random.C1,
                         (random.C3 & random.C1 & random.C2) | (random.C3 & random.p2.some(random.C3) & random.C1 & random.C2) | random.C3, random.p1.some(random.C6),
                         random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()
    
  def test_xxx3(self):
    with self.onto:
      for i in range(2):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(3):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      # random.p1
      # random.p2
      # random.p3
      # random.p4.is_a =  [random.p5]
      # random.p5.is_a =  [random.p2]
      # random.C1.is_a =  [Thing, random.p5.only(random.C1), random.p5.only(random.C1), random.p1.some(random.C1), random.p1.some(random.C1)]
      # random.C2.is_a =  [random.C1, random.p1.some(random.C3)]
      # random.C3.is_a =  [random.C2, random.p1.some(random.C3), random.p1.some(random.C1) | random.C3 | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p5.only(random.C1) & random.C1) | random.C2, random.p4.some(random.p5.only(random.C1))]
      # random.C4.is_a =  [random.C2]
      # random.C5.is_a =  [random.C1, random.p4.some(random.p5.only(random.C1))]
      # random.C6.is_a =  [random.C1]
      
      random.C1.is_a =  [Thing,
                         random.p2.only(random.C1),
                         random.p1.some(random.C1)]
      random.C2.is_a =  [random.C1]
      #random.C3.is_a =  [random.C1,
      #                   random.p1.some(random.C1) | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p2.only(random.C1) & random.C1) | random.C2,
      #                   random.p2.some(random.p2.only(random.C1))]
      random.C3.is_a =  [random.C2,
                         random.p1.some(random.C3),
                         random.p1.some(random.C1) | random.C3 | random.p1.some(random.C3) | (random.p1.some(random.C1) & random.p2.only(random.C1) & random.C1) | random.C2,
                         random.p2.some(random.p2.only(random.C1))]

    rm = self.sync_reasoner()

  def test_xxx4(self):
    with self.onto:
      for i in range(5):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(6):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      #random.C1.is_a =  [Thing, random.p1.only(random.C1 | random.C3 | random.C2)]
      #random.C2.is_a =  [random.C1]
      #random.C3.is_a =  [random.C1, random.C1 | random.C3 | random.C2, random.p1.only(random.C1 | random.C3 | random.C2), random.p1.some(random.p1.some(random.C4))]
      #random.C4.is_a =  [random.C3, random.p1.some(random.C4), random.p1.some(random.C4)]
      #random.C5.is_a =  [random.C3, random.p1.some(random.p1.some(random.C4))]

      random.C1.is_a =  [random.p1.only(random.C1 | random.C3 | random.C2)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C1,
                         random.C1 | random.C3 | random.C2,
                         random.p1.some(random.p1.some(random.C4)),
      ]
      random.C4.is_a =  [random.C3,
                         random.p1.some(random.C4)]
      

    rm = self.sync_reasoner()
    print(rm.max_restriction_depth)

  def test_xxx5(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(2):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
    
      random.C1.is_a =  [
        random.p1.only(random.C2),
      ]
      random.C2.is_a =  [
        random.C1,
        random.p1.some(random.C2),
        random.p1.only(random.C2) | random.p1.some(random.p1.only(random.C2)) | random.p1.some(random.C1),
      ]
      
    rm = self.sync_reasoner()


  def test_xxx6(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(5):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C3 & random.C2 & random.C1)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C3 | random.C2,
                         random.p1.some(random.C2)]
      
      
    rm = self.sync_reasoner()
    print(rm._restriction_depth())
    
    
  def test_xxx7complet(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(5):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  [random.p1.only(random.C5 & random.C2 & random.C3)]
      random.C2.is_a =  [random.C1]
      random.C3.is_a =  [random.C2]
      random.C4.is_a =  [random.C2]
      random.C5.is_a =  [random.C2,
                         random.C3 | random.C4,
                         random.p1.some(random.C2)]
      
    rm = self.sync_reasoner()
    
  def test_xxx7(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      random = self.onto
      
      random.C1.is_a =  []
      random.C2.is_a =  [random.C1, random.p1.only(random.C2 & random.C3 & random.C4)]
      random.C3.is_a =  []
      random.C4.is_a =  [random.C2 | random.C3,   random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()
    
    
  def test_xxx7simp(self):
    with self.onto:
      for i in range(1):
        C = types.new_class("p%s" % (i+1), (ObjectProperty,))
      for i in range(4):
        C = types.new_class("C%s" % (i+1), (Thing,))
        
      class C(Thing): pass
      
      random = self.onto
      
      C.is_a = [random.C2, random.C3, random.C4]
      #C.is_a = [random.C2 & random.C3 & random.C4]
      
      random.C1.is_a =  []
      random.C2.is_a =  [random.C1, random.p1.only(C)]
      random.C3.is_a =  []
      random.C4.is_a =  [random.C2 | random.C3,   random.p1.some(random.C1)]
      
    rm = self.sync_reasoner()

    
  def test_test1(self):
    with self.onto:
      class p(ObjectProperty): pass
      
      class A(Thing): pass
      class B(Thing): pass
      
      class Z(Thing): pass
      
      class X(Thing):
        is_a = [
          p.only(A) | Z,
          p.only(B),
          ]
        
      class R1(Thing): equivalent_to = [(p.only(A) & p.only(B)) | Z]
      #class XXX(Thing): is_a = [p.only(A) & p.only(B)]
        
      class R2(Thing): equivalent_to = [p.only(A & B) | Z]
        
    self.onto.save("/tmp/t.owl")
    rm = self.sync_reasoner()
    print(X.is_a)

    
  def test_test2(self):
    with self.onto:
      class p(ObjectProperty): pass
      
      class A(Thing): pass
      class B(Thing): pass
      
      class Z(Thing): pass
      
      class X(Thing):
        is_a = [
          p.only(A | Z),
          p.only(B),
          ]
        
      class R1(Thing):
        equivalent_to = [p.only((A & B) | Z)]
        
    self.onto.save("/tmp/t.owl")
    rm = self.sync_reasoner()
    print(X.is_a)

######################################################

#####Simple Test Class ###############################
class SimpleTest(BaseTest):
    def test_simple(self):
        with self.onto:
            class A(Thing): pass
            class B(A): pass
        
        rm = self.sync_reasoner()
        self.assert_is_a(B.storid, A.storid)
######################################################