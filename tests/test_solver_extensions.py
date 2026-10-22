"""Exact references, degeneracies, and local numerical solver limitations."""

import unittest

import sympy as sp

from mathechan.calculus import solve_equations
from mathechan.numeric_solve import solve_numerically, solve_polynomial_numerically
from mathechan.numeric_systems import solve_system_numerically
from mathechan.symbolic_systems import reduce_conditions, solve_parameter_branches


class SymbolicSystemExtensionTests(unittest.TestCase):
    def setUp(self):
        self.x, self.y, self.a, self.b, self.c = sp.symbols("x y a b c")

    def test_nonlinear_finite_system_is_verified_exactly(self):
        x, y = self.x, self.y
        outcome = solve_equations([x*x+y*y-1, x-y], [x, y])
        expected = sp.FiniteSet(sp.Tuple(-sp.sqrt(2)/2, -sp.sqrt(2)/2), sp.Tuple(sp.sqrt(2)/2, sp.sqrt(2)/2))
        self.assertEqual(outcome.value, expected)
        self.assertEqual(outcome.details["verification"], "verified")
        self.assertFalse(outcome.details["completeness"])

    def test_nonlinear_family_is_not_presented_as_an_isolated_point(self):
        outcome = solve_equations([self.x*self.y], [self.x, self.y])
        self.assertEqual(outcome.status, "conditional")
        self.assertEqual(outcome.details["solution_kind"], "infinite_family")
        self.assertTrue(outcome.warnings)

    def test_parameters_preserve_degenerate_branches(self):
        outcome = solve_equations([self.a*self.x**2+self.y, self.x*self.y], [self.x,self.y])
        self.assertEqual(outcome.status, "unresolved")
        self.assertTrue(outcome.value.has(sp.ConditionSet))
        self.assertIs(outcome.value.condition.subs({self.a:0,self.x:3,self.y:0}), sp.true)

    def test_linear_and_quadratic_parameter_partitions_are_explicit(self):
        linear = solve_equations(self.a*self.x-self.b, self.x)
        self.assertEqual(len(linear.details["branches"]), 3)
        self.assertTrue(linear.details["branches_cover_coefficient_cases"])
        quadratic = solve_parameter_branches(self.a*self.x**2+self.b*self.x+self.c,self.x)
        self.assertEqual(len(quadratic.details["branches"]), 4)
        self.assertTrue(quadratic.value.has(sp.ConditionSet))
        self.assertIn("EmptySet", [branch["solution"] for branch in quadratic.details["branches"]])

    def test_real_domain_filters_nonreal_points_and_bounds_are_checked(self):
        outcome = solve_equations([self.x**2+1,self.y-self.x],[self.x,self.y],"Reals")
        self.assertIs(outcome.value, sp.S.EmptySet)
        self.assertRaises(ValueError, solve_equations, [self.x**9+self.y], [self.x,self.y])


class NumericalSolverExtensionTests(unittest.TestCase):
    def setUp(self):
        self.x, self.y = sp.symbols("x y")

    def test_exact_algebraic_and_complex_coefficients_are_supported(self):
        result = solve_polynomial_numerically(self.x**2-sp.sqrt(2),self.x,precision=50)
        self.assertEqual(len(result.value),2)
        self.assertEqual(result.status,"approximate")
        positive = max(result.value)
        self.assertLess(abs(positive-sp.root(2,4).evalf(70)),sp.Rational(1,10)**49)
        complex_result = solve_polynomial_numerically(self.x+sp.I,self.x)
        self.assertEqual(len(complex_result.value),1)
        self.assertTrue(next(iter(complex_result.value)).has(sp.Float))

    def test_float_coefficients_preserve_original_stored_binary_values(self):
        coefficient = sp.Float("0.1",15)
        result=solve_polynomial_numerically(self.x-coefficient,self.x,precision=50)
        actual=next(iter(result.value))
        self.assertLess(abs(actual-sp.Rational(coefficient)),sp.Rational(1,10)**49)
        self.assertGreater(abs(actual-sp.Rational(1,10)),sp.Rational(1,10)**18)
        self.assertEqual(result.details["input_float_min_precision_bits"],coefficient._prec)
        self.assertIn("stored_binary",result.details["coefficient_model"])
        self.assertTrue(any("información" in item for item in result.warnings))

    def test_numeric_polynomial_system_uses_exact_candidates(self):
        x,y=self.x,self.y
        result=solve_system_numerically([x*x+y*y-1,x-y],[x,y],precision=40)
        self.assertEqual(len(result.value),2)
        self.assertEqual(result.status,"approximate")
        self.assertTrue(result.details["exact_candidates"])
        self.assertFalse(result.details["completeness"])
        for point in result.value:
            self.assertLess(abs(point[0]-point[1]),sp.Rational(1,10)**39)
        self.assertTrue(all(check["passed"] for row in result.details["residuals"] for check in row["equations"]))

    def test_nonisolated_numeric_system_is_not_discretized(self):
        result=solve_system_numerically([self.x*self.y],[self.x,self.y])
        self.assertEqual(result.status,"unresolved")
        self.assertTrue(any("no se discretiza" in item for item in result.warnings))

    def test_seeded_transcendental_solution_is_local_and_verified_by_residual(self):
        result=solve_numerically(sp.cos(self.x)-self.x,self.x,precision=40,initial=(1,))
        self.assertEqual(result.status,"approximate")
        self.assertFalse(result.details["completeness"])
        self.assertTrue(result.details["local_solution"])
        value=next(iter(result.value))
        self.assertLess(abs(sp.N(sp.cos(value)-value,50)),sp.Rational(1,10)**38)
        self.assertTrue(any("local" in item for item in result.warnings))
        self.assertRaises(ValueError,solve_numerically,sp.cos(self.x)-self.x,self.x)

    def test_seeded_complex_and_transcendental_systems(self):
        complex_result=solve_numerically(self.x**2+1,self.x,initial=(sp.I,))
        self.assertLess(abs(next(iter(complex_result.value))-sp.I),sp.Rational(1,10)**28)
        result=solve_system_numerically([sp.sin(self.x)+self.y-1,self.x**2+self.y**2-1],
                                       [self.x,self.y],initial=(sp.Rational(1,2),sp.Rational(1,2)))
        self.assertEqual(len(result.value),1)
        self.assertTrue(result.details["local_solution"])
        self.assertFalse(result.details["completeness"])

    def test_numeric_conditions_and_original_exclusions_are_checked(self):
        result=solve_system_numerically([self.x**2-1,self.y-self.x],[self.x,self.y],requirements=(self.x>0,))
        self.assertEqual(len(result.value),1)
        self.assertGreater(next(iter(result.value))[0],0)
        self.assertRaises(ValueError,solve_numerically,sp.sin(self.x),self.x,
                          initial=(0,),restrictions=(self.x,))
        self.assertRaises(ValueError,solve_numerically,self.x**2+1,self.x,
                          domain="Reals",initial=(sp.I,))

    def test_seed_dimension_invalid_data_and_parameter_systems(self):
        self.assertRaises(ValueError,solve_system_numerically,[self.x+self.y],[self.x,self.y],initial=(1,2))
        self.assertRaises(ValueError,solve_numerically,sp.sin(self.x),self.x,initial=(sp.oo,))
        self.assertRaises(ValueError,solve_numerically,sp.sin(self.x),self.x,initial=("1",))
        a=sp.Symbol('a')
        result=solve_system_numerically([a*self.x+self.y,self.x*self.y],[self.x,self.y])
        self.assertEqual(result.status,"unresolved")
        self.assertTrue(result.value.has(sp.ConditionSet))

    def test_local_numerical_equality_hypothesis_is_not_falsely_rejected(self):
        result=solve_numerically(self.x**2-2,self.x,initial=(1,),
                                 requirements=(sp.Eq(self.x**2,2),))
        self.assertIn(result.status,{"conditional","approximate"})
        self.assertEqual(len(result.value),1)


class ReduceExtensionTests(unittest.TestCase):
    def setUp(self):
        self.x=sp.Symbol('x')

    def test_real_boolean_polynomial_conditions_return_sets(self):
        result=reduce_conditions(sp.And(self.x**2<4,self.x>0),self.x)
        self.assertEqual(result.value,sp.Interval.open(0,2))
        self.assertTrue(result.details['completeness'])
        union=reduce_conditions(sp.Or(self.x<0,self.x>1),self.x)
        self.assertEqual(union.value,sp.Union(sp.Interval.open(-sp.oo,0),sp.Interval.open(1,sp.oo)))
        identity=reduce_conditions(sp.Eq(self.x,self.x,evaluate=False),self.x)
        self.assertIs(identity.value,sp.S.Reals)

    def test_complex_equalities_and_exclusions_preserve_domain(self):
        result=reduce_conditions(sp.Eq(self.x**2+1,0),self.x,'Complexes')
        self.assertEqual(result.value,sp.FiniteSet(-sp.I,sp.I))
        excluded=reduce_conditions(sp.Ne(self.x,0),self.x,'Complexes')
        self.assertFalse(excluded.value.contains(0))
        self.assertTrue(excluded.value.contains(sp.I))

    def test_parameters_and_undecidable_domains_remain_conditioned(self):
        a=sp.Symbol('a')
        result=reduce_conditions(self.x>a,self.x)
        self.assertEqual(result.status,'unresolved')
        self.assertTrue(result.value.has(sp.ConditionSet))
        complex_order=reduce_conditions(self.x>0,self.x,'Complexes')
        self.assertEqual(complex_order.status,'unresolved')
        self.assertRaises(ValueError,reduce_conditions,self.x+1,self.x)


if __name__ == '__main__':
    unittest.main()
