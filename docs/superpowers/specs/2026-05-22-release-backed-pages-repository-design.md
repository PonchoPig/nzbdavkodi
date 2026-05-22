# Release-Backed GitHub Pages Repository Design

## Goal

Reset the Kodi repository publishing flow so users install the repository from:

```text
https://ponchopig.github.io/nzbdavkodi
```

The Pages site links to a CI-generated `repository.nzbdav` zip. The installed Kodi repository then offers `plugin.video.nzbdav` from the latest stable GitHub Release asset, not from a zip checked into `main`.

## Non-Goals

- Preserve update compatibility for users who installed older repository addons pointing at raw GitHub `main` URLs.
- Keep generated repository metadata or zip artifacts checked into `main`.
- Publish beta, alpha, release-candidate, or other prerelease addon builds to normal Kodi users.

Existing users of the old repository must reinstall from the new GitHub Pages URL.

## Architecture

GitHub Releases are the source of addon binaries. GitHub Pages is the generated Kodi install and update surface.

`main` contains source, scripts, docs, and workflows only. Generated outputs such as `repo/zips/`, root `repository.nzbdav-*.zip`, and root addon zip files are removed from version control and ignored.

The generated Pages artifact contains:

- `index.html` with a link to the generated repository addon zip.
- `.nojekyll`.
- `repository.nzbdav-<repo-version>.zip`, where `<repo-version>` is the repository addon's own version.
- Kodi repository metadata files such as `addons.xml` and `addons.xml.md5`.
- Repository addon browsing files only: `repository.nzbdav/addon.xml`, `repository.nzbdav/icon.png`, and `repository.nzbdav/index.html` if needed for Kodi directory browsing.

The Pages artifact intentionally does not contain:

- `plugin.video.nzbdav-*.zip`.
- Historical addon zip releases.
- Legacy root metadata compatibility shims for old raw-GitHub installs.
- `releases-repo/` or other duplicate repository variants.

## Stable Release Selection

The Pages workflow selects the latest stable addon release from GitHub Releases.

A release is stable only when both conditions are true:

- GitHub marks it as `isPrerelease == false`.
- Its tag/version has no prerelease suffix or marker, including SemVer prerelease metadata and common labels such as `alpha`, `beta`, and `rc`.

Examples:

- `v1.4.0` is stable.
- `v1.4.0-beta.1` is not stable.
- `v1.4.0-rc.1` is not stable.
- `v1.4.0+build.5` is stable if GitHub does not mark it prerelease.

When multiple stable releases exist, the workflow chooses the highest SemVer version. If no stable release exists, Pages deployment fails with a clear error.

Stable release selection must live in a small testable script, not inline workflow shell. Use a script such as:

```text
scripts/select_stable_release.py
```

The script accepts GitHub Releases JSON, rejects unstable candidates, sorts stable candidates by SemVer, and emits the selected release tag and addon zip asset name or URL. It fails clearly when no stable release exists or when the selected release does not contain exactly one `plugin.video.nzbdav-*.zip` asset.

## Release Workflow

The release workflow remains tag-driven.

On `v*` tag push, it:

1. Checks out the tag.
2. Installs test dependencies.
3. Runs the test suite.
4. Extracts the version from the tag.
5. Verifies `repo/plugin.video.nzbdav/addon.xml` matches the tag version.
6. Builds `plugin.video.nzbdav-<version>.zip`.
7. Uploads that zip to the GitHub Release.

It does not generate Kodi repository metadata and does not publish GitHub Pages directly.

## Pages Workflow

The Pages workflow owns repository publishing.

It runs after a successful Release workflow, on manual dispatch, and on relevant source or workflow changes.

It:

1. Queries GitHub Releases.
2. Calls the stable release selection script using the stable release rules above.
3. Downloads that release's `plugin.video.nzbdav-<version>.zip`.
4. Generates `addons.xml` and `addons.xml.md5`.
5. Builds `repository.nzbdav-<repo-version>.zip`.
6. Writes a Kodi-browsable `index.html`.
7. Uploads the generated directory as the GitHub Pages artifact.
8. Deploys the artifact to GitHub Pages.

The workflow downloads only the selected stable addon release for normal publishing. It does not preserve old raw-GitHub compatibility paths.

After generating the Pages artifact, the workflow runs a local smoke check before upload. The check verifies:

- `index.html` links to an existing `repository.nzbdav-*.zip`.
- `addons.xml.md5` matches `addons.xml`.
- The repository zip contains `repository.nzbdav/addon.xml`.
- The generated `plugin.video.nzbdav` entry points to a GitHub Release asset URL.
- No `plugin.video.nzbdav-*.zip` exists anywhere in the Pages artifact.

## Kodi Repository Descriptor

`repo/repository.nzbdav/addon.xml` becomes the canonical repository addon descriptor.

Its repository URLs point at the GitHub Pages site:

```xml
<info compressed="false">https://ponchopig.github.io/nzbdavkodi/addons.xml</info>
<checksum>https://ponchopig.github.io/nzbdavkodi/addons.xml.md5</checksum>
<datadir zip="true">https://ponchopig.github.io/nzbdavkodi/</datadir>
```

The separate release-backed repository variant is unnecessary after the reset unless retained temporarily for cleanup.

Remove `repo/repository.nzbdav.releases` during the reset unless implementation discovers a concrete reason to keep it. Keeping both repository variants would make the install path and future release maintenance easier to confuse.

The repository addon keeps its own manually managed version. Bump that version only when repository-addon behavior changes, such as URL changes, metadata layout changes, or other installed-repository behavior changes. Normal `plugin.video.nzbdav` releases do not automatically bump the repository addon version.

## Generated Addon Metadata

Generated `addons.xml` includes:

- The repository addon entry from `repo/repository.nzbdav/addon.xml`.
- The selected stable `plugin.video.nzbdav` addon entry read from the downloaded release zip.

The `plugin.video.nzbdav` metadata path points at the selected GitHub Release asset:

```text
https://github.com/PonchoPig/nzbdavkodi/releases/download/v<version>/plugin.video.nzbdav-<version>.zip
```

The addon zip is not copied into or served from GitHub Pages.

## Cleanup

Remove generated artifacts from git:

- `repo/zips/`
- root `repository.nzbdav-*.zip`
- root `plugin.video.nzbdav-*.zip`, if present
- `repo/repository.nzbdav.releases/`, unless a concrete implementation need is found.

Update `.gitignore` so regenerated repository output, Pages output, and zip artifacts remain untracked.

Update install and release documentation in the same implementation pass:

- README install instructions should point users at `https://ponchopig.github.io/nzbdavkodi`.
- Release docs/checklists should explain that GitHub Releases host addon zips and GitHub Pages hosts generated repository metadata.
- Remove instructions that require committing `repo/zips/` artifacts.
- Keep `just repo` only if it remains useful as a local preview/build command, and document that its outputs are not committed.

## Tests

Add or update tests for:

- Stable release selection accepting normal SemVer releases.
- Stable release selection rejecting GitHub prereleases.
- Stable release selection rejecting suffixes such as `-alpha`, `-beta`, and `-rc`.
- Stable release selection choosing the highest SemVer stable release.
- Stable release selection failing when no stable release exists.
- Stable release selection failing when the chosen release has zero or multiple matching addon zip assets.
- Generated `plugin.video.nzbdav` metadata pointing at GitHub Release assets.
- Repository addon descriptor pointing at `https://ponchopig.github.io/nzbdavkodi/`.
- Repository generation working without checked-in `repo/zips/`.
- Pages artifact smoke checks for the generated repository zip, checksum, release asset URL, and absence of copied addon zips.

## Success Criteria

- `main` no longer tracks generated Kodi repository zip or metadata artifacts.
- `https://ponchopig.github.io/nzbdavkodi` links to the CI-generated repository addon zip.
- Installing that repository addon in Kodi exposes the latest stable `plugin.video.nzbdav` GitHub Release.
- Beta, alpha, release-candidate, and GitHub prerelease builds are not selected for the normal repository.
- Stable release selection is implemented in a unit-tested script rather than fragile inline workflow shell.
- The Pages artifact is minimal and does not include addon zip binaries.
- `repo/repository.nzbdav.releases` is removed unless implementation proves it is still needed.
- Install docs and release docs match the new release-backed Pages flow.
- `just lint` and `just test` pass before committing or pushing changes.
