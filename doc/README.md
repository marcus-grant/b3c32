# Documentation

Contract and design documents for b3c32.
The conformance document is normative;
where an implementation and it conflict, the document wins.

## Python development

Python commands run from repo root via `uv run --directory python`.
With `UV_PROJECT=python` exported, plain uv run works instead,
with tab-completable root-relative paths.

## Documents

- [conformance](./conformance.md) the normative contract:
  - The scheme, where every expected value comes from,
  - Also, what an implementation must prove
- [plan/](./plan/README.md) planning documents: fixes, roadmap, unplanned
- [publish.md](./publish.md) how a release reaches PyPI
