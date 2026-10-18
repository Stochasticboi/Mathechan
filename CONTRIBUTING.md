# Contribuir / Contributing

## Español

Mathechan es un proyecto personal en desarrollo. Antes de ampliar una función,
revise [los objetivos](docs/es/objetivos.md) y [el lenguaje](docs/es/lenguaje.md).
Las propuestas pueden discutirse en una issue y presentarse en un pull request.

- Mantenga cada cambio acotado y explique el problema que resuelve.
- Use identificadores en inglés y código legible con dependencias justificadas.
- Para cálculos, indique supuestos, dominios, resultado de referencia y tolerancias.
- Añada pruebas cuando verifiquen un comportamiento significativo.
- Conserve la notación científica y explique las transformaciones necesarias.
- Cite fuentes primarias y respete las licencias del material incorporado.
- No incluya credenciales, documentos personales ni código propietario ajeno.

Antes de enviar un cambio, ejecute desde la raíz:

```console
python -m unittest discover -s tests -v
```

Describa el resultado observado y las limitaciones pendientes. Una prueba
aprobada no sustituye la revisión matemática o física del procedimiento.

## English

Mathechan is a personal project under development. Before extending a feature,
read [the objectives](docs/en/objectives.md) and [the language](docs/en/language.md).
Proposals can be discussed in an issue and submitted through a pull request.

- Keep each change focused and explain the problem it solves.
- Use English identifiers, readable code, and justified dependencies.
- For calculations, specify assumptions, domains, reference results, and tolerances.
- Add tests where they check meaningful behavior.
- Preserve scientific notation and explain necessary transformations.
- Cite primary sources and respect the licenses of incorporated material.
- Do not include credentials, personal documents, or proprietary third-party code.

Run the test command above from the repository root before submitting a change.
Describe the observed result and remaining limitations. Passing tests does not
replace mathematical or physical review of a method.