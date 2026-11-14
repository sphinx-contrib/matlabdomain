# Simulink file checks

Tools that keep the Simulink reader (`sphinxcontrib/mat_simulink/`) and the
formats page (`docs/developer-guide/simulink-file-formats.rst`) current.
The fixtures and their oracle are written by
`tests/simulink/make_fixtures.m`; the unit tests are
`tests/test_mat_simulink.py` and `tests/test_simulink_index.py`. The
Simulink files of the documentation's sample project (`docs/src/simulink/`)
are written by `tests/simulink/make_docs_sample.m`, in R2024a.

| File | Purpose |
|---|---|
| `survey.py` | Where each fixture keeps each fact (layout, parts, probe texts, mask forms), and what changes from one release to the next. |
| `corpus.py` | Reads every `.slx` and `.mdl` below some folders: kinds, layouts, mask forms, times, errors. |
| `fuzz.py` | Seeded fuzzer of the readers: mutates the fixtures and the sample `.mlapp` and checks that only the documented failure escapes (see below). |
| `naming_probe.m` | MATLAB probe of how Simulink loads files by name (namespace, `private/` and class folders, `.slx` vs `.mdl` vs `.m`, name length). Its results are the rules of `mat_naming.form_model_name`. |
| `simulink_namespace_probe.m`, `simulink_namespace_call_probe.m` | What works for Simulink files in `+namespace` folders (loading, `sim`, Model and Subsystem Reference blocks, library links, the name as an expression). Its results are the "Simulink files in namespace folders" section of `docs/user-guide/simulink.rst`. |

## For each new MATLAB release

Run the MATLAB steps in the new release, from the repository root:

```matlab
make_fixtures("sources", "tests/simulink/fixtures")
make_fixtures("export", "tests/simulink/fixtures")   % if the release changed the format
make_fixtures("oracle", "tests/simulink/fixtures")
naming_probe(fullfile(tempdir, "naming-probe"))
addpath("test_slow/simulink")
simulink_namespace_probe()        % writes below tempdir
simulink_namespace_call_probe()
```

Then, in the project's environment (on Windows use `.venv\Scripts\python`):

```bash
python test_slow/simulink/survey.py
python test_slow/simulink/corpus.py <matlabroot>/toolbox test_slow/repos
python -m pytest tests/test_mat_simulink.py tests/test_simulink_index.py
```

- A change in the survey is a new row of the formats page ("What changes
  per release"); add the release to `fixtureReleases` in
  `make_fixtures.m` when the reader needs it.
- A change in the naming probe is a new row of `MATLAB_VERSION_RULES` in
  `sphinxcontrib/mat_naming.py`.
- `corpus.py` exits 1 if the reader crashed; any other error is a file it
  cannot read, which should stay rare (an empty file, a Git LFS pointer, a
  file over the size limits).

## Fuzzing the readers

```bash
python test_slow/simulink/fuzz.py --seed 1 --cases 3000
```

`fuzz.py` (standard library only; run it in the project's environment)
mutates the files of `tests/simulink/fixtures/` (`.slx`, `.mdl`) and
`tests/test_data/Application.mlapp`: bit flips, truncation, rewritten,
dropped or duplicated zip members, entity declarations, deep nesting and odd
encodings in the XML declaration. It calls `mat_simulink.classify` and
`read_diagram`, or `MatObject.parse_mlappfile`, and prints how many cases
ended in each outcome. The same `--seed` gives the same cases. It exits 1 if
anything but the documented failure escapes (a `SimulinkFileError`; for
`.mlapp` also the errors of the zip and XML modules that `mat_types._parse`
turns into a `mat.parse_error`) or a case takes more than 10 s; the files
of the escapes are kept in `--keep`. Run it with a few seeds after a change
to the readers; 3,000 cases take about 3 s. An escape becomes a regression
test in `tests/`.
