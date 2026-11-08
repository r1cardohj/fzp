# Releasing fzp

The project publishes with
[PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/); GitHub's
short-lived OIDC identity replaces a stored PyPI API token.

## One-time PyPI setup

Sign in to PyPI with the account that will own `fzp`, then open:

<https://pypi.org/manage/account/publishing/>

Add a **pending publisher** with exactly these values:

| Field | Value |
| --- | --- |
| PyPI project name | `fzp` |
| Owner | `r1cardohj` |
| Repository name | `fzp` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

The environment name is required because the publishing job uses the `pypi`
GitHub environment. Do not leave it blank.

## Publish a version

1. Update `version` in `pyproject.toml` and `__version__` in
   `src/fzp/__init__.py` when releasing a version after `0.1.0`.
2. Commit the version change on `main` and wait for CI to pass.
3. Create and push a tag matching the package version:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. Watch the **Release** workflow:

   ```bash
   gh run watch
   ```

The workflow runs CI, builds both an sdist and a wheel, checks their metadata,
and publishes them through `pypa/gh-action-pypi-publish`. A PyPI version is
immutable: if a release fails, fix the problem, bump the version, and push a
new tag rather than trying to replace an existing file.

After publication, verify <https://pypi.org/project/fzp/> and test an isolated
installation with `uv tool install fzp`.
