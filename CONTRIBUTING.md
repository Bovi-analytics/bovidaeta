# Contributing to bovidaeta

Thanks for your interest in improving bovidaeta! Bug reports, questions,
new event types and code changes are all welcome.

bovidaeta is maintained by the [Bovi-Analytics lab](https://bovi-analytics.org/)
at Cornell University. Every pull request is reviewed by at least one lab
member before it's merged. We're a small team, so a review can take a few
weeks; thanks for your patience.

## Contact

For anything that doesn't fit in a GitHub issue, including concerns about
how people treat each other in this project, contact the maintainers:

- Bart de Zoete (main maintainer): bd482@cornell.edu
- Miel Hostens (principal investigator): miel.hostens@cornell.edu

## Questions and bug reports

Open an [issue](https://github.com/Bovi-Analytics/bovidaeta/issues). For a
bug, include the bovidaeta version (`python -c "import bovidaeta; print(bovidaeta.__version__)"`),
your Python version, and a small example that shows the problem. Please
don't attach real farm data: the simulator
(`python -m bovidaeta.simulation`) can usually reproduce the issue.

## Development setup

We use [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/Bovi-Analytics/bovidaeta.git
cd bovidaeta
uv sync                 # creates .venv with the package and dev tools
uv run pytest           # run the tests
```

bovidaeta supports Python 3.10 and newer, so avoid syntax and standard
library features that are newer than that (for example `datetime.UTC`; use
`datetime.timezone.utc` instead).

## Making a change

1. Fork the repo (or create a branch, if you have access) and make your
   change.
2. Add or update tests in `tests/`, and update the docs (README files,
   docstrings) if behaviour changes.
3. Make sure `uv run pytest` passes.
4. Open a pull request against `main`.

<!-- TODO(release-ci): once version bumps are automated, describe the PR
     title convention here, e.g. Conventional Commits:
       feat: add HoofTrimming event type      -> minor release
       fix: handle missing birth_date         -> patch release
       docs: / test: / chore:                 -> no release
-->

### Changing the data format

The models (`cow.py`, `herd.py`, `event.py`, `event_metadata.py`,
`enums.py`) and the table definitions in `schemas/` describe data that is
already stored on farms and in Databricks. Changes there affect everyone
reading that data, so new event types and metadata fields need sign-off
from the lab. Open an issue to discuss the change before you write the code.

bovidaeta stores what was observed or recorded on the farm, and leaves out
values that can be derived from other events, such as days in milk or
lactation number.

When changing the format:

- prefer adding optional fields over renaming or removing existing ones;
- keep `schemas/sqlite.sql` and `schemas/delta.sql` in line with the models;
- describe in the PR how existing data is affected.

## License

bovidaeta is licensed under the Apache License 2.0 (see [LICENSE](LICENSE)).
As section 5 of that license says, any contribution you submit for
inclusion is licensed under the same terms.
