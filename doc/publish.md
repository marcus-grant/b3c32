# Publishing

How a b3c32 release reaches PyPI. The python implementation is the only
published artifact; the contract artifacts at the repo root are consumed
from git.

## Trusted publishers

Publication uses PyPI trusted publishers rather than API tokens. GitHub
vouches for the workflow run over OIDC, so no long-lived credential
exists in the repo or in GitHub secrets.

Both registries are registered against the same repository and workflow:

- Project name: b3c32
- Owner: marcus-grant
- Repository: b3c32
- Workflow: publish.yml
- Environment: pypi on pypi.org, testpypi on test.pypi.org

The two GitHub environments of those names must exist under repository
settings for the jobs to run. They carry no protection rules today; a
required reviewer on pypi would gate real publishes behind manual
approval, which is worth adding when releases become routine.

## The workflow

`.github/workflows/publish.yml` builds once and publishes conditionally.
A manual dispatch from the Actions tab publishes to TestPyPI. A pushed
tag matching v* publishes to PyPI. The build job runs for both, so the
same artifact is what reaches either registry.

The workflow does not run the test suite. The full gate is manual and
runs before every commit, so a tagged commit has already passed it.

## Releasing

Version numbers on PyPI can never be reused. A deleted release burns its
number permanently, so the dry run is not optional.

1. Bump version in `python/pyproject.toml` on the release commit. The
   tag must point at a commit whose version matches the tag, or the
   published artifact carries the wrong number.
2. Merge to main. The merge commit is what gets tagged, as with v0.0.1.
3. Dispatch the workflow manually from the Actions tab. This publishes
   to TestPyPI.
4. Install the published artifact into a scratch environment and call
   `verify_conformance`. This proves consumers get a working package,
   which the suite against the source tree does not.
5. Tag the merge commit and push the tag. This publishes to PyPI.

## Checking a release

The wheel should contain the four package modules and nothing else: no
tests, no caches, no vector files. Inspect it with `unzip -l` on the
built artifact under `python/dist/` before trusting a first publish
after any packaging change.