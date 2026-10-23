"""Analytic Euclidean identities expressed in non-Cartesian coordinates."""

import unittest

import sympy as sp

from mathechan.coordinate_calculus import chart_conditions, coordinate_operator


class CoordinateCalculusTests(unittest.TestCase):
    def setUp(self):
        self.r, self.t, self.p, self.z = sp.symbols("r theta phi z")

    def result(self, operation, expr, chart="Spherical", mode="Components"):
        variables = (self.r, self.t, self.p) if chart == "Spherical" else (self.r, self.p, self.z)
        return coordinate_operator(operation, expr, variables, chart, mode)

    def test_spherical_radial_gradient_and_divergence(self):
        r = self.r
        self.assertEqual(self.result("Grad", r**2).value, sp.ImmutableMatrix([2*r, 0, 0]))
        self.assertEqual(self.result("Div", [r, sp.S.Zero, sp.S.Zero]).value, 3)

    def test_cylindrical_rotating_field(self):
        self.assertEqual(self.result("Curl", [sp.S.Zero, self.r, sp.S.Zero], "Cylindrical").value,
                         sp.ImmutableMatrix([0, 0, 2]))

    def test_hessian_quadratic_is_identity_in_both_charts(self):
        for chart, scalar in (("Spherical", self.r**2/2),
                              ("Cylindrical", (self.r**2+self.z**2)/2)):
            self.assertEqual(self.result("Hessian", scalar, chart).value, sp.eye(3))

    def test_hessian_radial_distance(self):
        self.assertEqual(self.result("Hessian", self.r).value,
                         sp.diag(0, 1/self.r, 1/self.r))

    def test_hessian_cartesian_coordinate_is_zero(self):
        for chart, scalar in (("Spherical", self.r*sp.sin(self.t)*sp.cos(self.p)),
                              ("Cylindrical", self.r*sp.cos(self.p))):
            self.assertEqual(self.result("Hessian", scalar, chart).value, sp.zeros(3))

    def test_constant_cartesian_vector_has_zero_covariant_gradient(self):
        for chart, vector in (("Spherical", [sp.sin(self.t)*sp.cos(self.p),
                                             sp.cos(self.t)*sp.cos(self.p), -sp.sin(self.p)]),
                              ("Cylindrical", [sp.cos(self.p), -sp.sin(self.p), sp.S.Zero])):
            self.assertEqual(self.result("Grad", vector, chart).value, sp.zeros(3))
            self.assertEqual(self.result("Jacobian", vector, chart, "Orthonormal").value, sp.zeros(3))

    def test_coordinate_map_jacobian_and_volume(self):
        r, t, p = self.r, self.t, self.p
        mapping = [r*sp.sin(t)*sp.cos(p), r*sp.sin(t)*sp.sin(p), r*sp.cos(t)]
        value = self.result("Jacobian", mapping).value
        self.assertEqual(value, sp.ImmutableMatrix(mapping).jacobian([r, t, p]))
        self.assertEqual(sp.trigsimp(value.det()), r**2*sp.sin(t))

    def test_component_jacobian_can_be_rectangular(self):
        value = self.result("Jacobian", [self.r, self.t]).value
        self.assertEqual(value, sp.ImmutableMatrix([[1, 0, 0], [0, 1, 0]]))

    def test_radial_refinement_before_differentiation(self):
        value = self.result("Grad", sp.Abs(self.r)).value
        self.assertEqual(value, sp.ImmutableMatrix([1, 0, 0]))

    def test_vector_gradient_matches_geometric_hessian(self):
        for chart, scalar in (("Spherical", self.r**3*sp.cos(self.t)),
                              ("Cylindrical", self.r**2*sp.sin(self.p)*self.z)):
            gradient = self.result("Grad", scalar, chart).value
            hessian = self.result("Hessian", scalar, chart).value
            self.assertEqual(self.result("Grad", gradient, chart).value, hessian)

    def test_curl_of_gradient_is_zero_in_both_charts(self):
        for chart, scalar in (("Spherical", self.r**2*sp.cos(self.t)*sp.sin(self.p)),
                              ("Cylindrical", self.r**2*sp.sin(self.p)*self.z)):
            gradient = self.result("Grad", scalar, chart).value
            self.assertEqual(self.result("Curl", gradient, chart).value, sp.zeros(3, 1))

    def test_spherical_angular_refinement(self):
        scalar = sp.sqrt(sp.sin(self.t)**2)
        self.assertEqual(self.result("Grad", scalar).value,
                         sp.ImmutableMatrix([0, sp.cos(self.t)/self.r, 0]))

    def test_singular_or_nonreal_chart_declarations_reject(self):
        for radial in (sp.Symbol("r", negative=True), sp.Symbol("r", imaginary=True)):
            with self.assertRaises(ValueError):
                chart_conditions((radial, self.t, self.p), "Spherical")
        with self.assertRaises(ValueError):
            chart_conditions((self.r, sp.Symbol("theta", negative=True), self.p), "Spherical")

    def test_input_budget_includes_parameters(self):
        expression = sum(sp.symbols("a:9"))
        with self.assertRaises(ValueError):
            self.result("Grad", expression)

    def test_undefined_functions_preserve_formal_derivatives(self):
        value = self.result("Grad", sp.Function("f")(self.r))
        self.assertEqual(value.status, "unresolved")
        self.assertTrue(value.value.has(sp.Derivative))

    def test_chart_requirements_and_details_are_serializable(self):
        import json
        value = self.result("Hessian", self.r)
        json.dumps(value.details)
        requirements = chart_conditions((self.r, self.t, self.p), "Spherical")
        self.assertIn(self.r > 0, requirements)
        self.assertIn(self.t < sp.pi, requirements)
        self.assertEqual(value.details["domain_analysis"], "partial")
        self.assertEqual(value.status, "conditional")
        self.assertEqual(value.details["scale_factors"], ["1", "r", "r*sin(theta)"])
        self.assertEqual(self.result("Jacobian", [self.r, self.t]).details["basis"],
                         "component_functions_by_coordinate")

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            coordinate_operator("Grad", self.r, (self.r, self.t), "Spherical")
        with self.assertRaises(ValueError):
            self.result("Div", [self.r, self.t])
        with self.assertRaises(ValueError):
            self.result("Jacobian", [self.r, self.t], mode="Orthonormal")
        with self.assertRaises(ValueError):
            self.result("Hessian", [self.r, self.t, self.p])
        with self.assertRaises(ValueError):
            coordinate_operator("Grad", self.r, (self.r, self.t, self.p), "Unknown")


if __name__ == "__main__":
    unittest.main()
