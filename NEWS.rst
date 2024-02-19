===============
Version history
===============

0.2.6 (2024-02-19)
==================

- Fix the bug in the `sitecustomize.py` bundled with the `lpci` snap to
  get the snap build working on `snapcraft` 8.x versions. See
  https://bugs.launchpad.net/lpci/+bug/2053109.

0.2.5 (2023-12-05)
==================

- Add support for 23.10 (mantic).
- Remove support for 22.10 (kinetic).

0.2.4 (2023-09-29)
==================

- Fix ``lpci release`` to release the latest build of each architecture (or
  a single architecture selected by the new ``--architecture`` option),
  rather than only releasing the latest build regardless of architecture.

0.2.3 (2023-07-20)
==================

- Upgrade ``PyYAML`` to 6.0.1 to fix https://github.com/yaml/pyyaml/issues/601,
  which was causing errors during the installation of ``PyYAML``.

0.2.2 (2023-07-14)
==================

- Fix default value for the `root` flag in documentation.

- Fix conda-build plugin to install and run outside
  of a conda environment.

0.2.1 (2023-06-06)
==================

- Rebuild the Snap package to include updated system packages with fixes
  for the following vulnerabilities.

  * https://ubuntu.com/security/notices/USN-6112-2/
  * https://ubuntu.com/security/notices/USN-6138-1/
  * https://ubuntu.com/security/notices/USN-6139-1/

0.2.0 (2023-05-24)
==================

- Add support for non-LTS devel release, which is currently mantic.

- Update Python dependencies, especially `Cryptography`, see CVE-2023-0286 and
  CVE-2023-23931.

- Fix Snap build issues for lpci on platforms which do not offer pre-built
  wheels for Cryptography.

0.1.2 (2023-05-02)
==================

- Rebuild the Snap package to include updated system packages
  https://ubuntu.com/security/notices/USN-6050-1/.

- Add ``dev0`` suffix documentation.

0.1.1 (2023-04-21)
==================
- Fix the yaml formatting in the snap deprecated format warning.

- Fix ``policy-rc.d`` issue preventing services
  from running into the container.

- Add a ``root`` flag.

0.1.0 (2023-04-18)
==================

- Add a ``release`` command.

- Rename project to ``lpci``.

- Add a ``--debug-shell`` flag.

- Add a ``recipe_folder`` parameter to specify
  the recipe itself, or the recipe search path
  using conda-build-plugin.

0.0.52 (2023-04-06)
===================
- Fix regression from adding support to snap keys
  passed as strings. For these keys confinement classic
  must be True by default to ensure backward compatibility.

0.0.51 (2023-04-05)
===================
- Add support for snap's channel and confinement level.
  See https://snapcraft.io/docs/channels and
  https://snapcraft.io/docs/snap-confinement.

0.0.50 (2023-03-20)
===================
- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5960-1.

0.0.49 (2023-03-10)
===================
- Fix regression from adding support for non-LTS releases. With the latest
  release of `craft-providers` we need to explicitly add a remote for images.

0.0.48 (2023-03-10)
===================

- Add support for non-LTS releases, that is currently lunar and kinetic.
  Please note that we use daily cloud images
  (https://cloud-images.ubuntu.com/daily/) for this purpose,
  so we cannot guarantee stability.

- Fix various ``mypy`` errors.

0.0.47 (2023-03-01)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5821-3/.


0.0.46 (2023-02-28)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5891-1/.

- Update dependencies.

- Fix deprecation warning in `lxd.launch` (changed API in `craft-providers`).

0.0.45 (2023-02-15)
===================

- Replace deprecated setuptools directive.
  See https://setuptools.pypa.io/en/latest/references/keywords.html#keyword-license-file.

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5871-1/.

0.0.44 (2023-02-09)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5849-1/.

0.0.43 (2023-01-24)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5817-1.

0.0.42 (2023-01-20)
===================

- Add experimental ``--gpu-nvidia`` option.

0.0.41 (2023-01-18)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5810-1/.

0.0.40 (2023-01-13)
===================

- Fix the leakage of package repositories from a job to the next.
- Add support for Python 3.11.
- Set sensible default values for some package repository fields.
- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5800-1.

0.0.39 (2023-01-06)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5788-1.

0.0.38 (2023-01-05)
===================

- Allow specifying PPAs using the shortform notation,
  e.g. `ppa:launchpad/ubuntu/ppa`.

- Automatically import the signing keys for PPAs specified using
  the short-form notation.

0.0.37 (2022-12-09)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5767-1.

0.0.36 (2022-12-08)
===================

- Sanitize the project name before cleaning.
- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5766-1/.

0.0.35 (2022-10-27)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5702-1/.

0.0.34 (2022-10-20)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5689-1.

0.0.33 (2022-10-19)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5686-1.

0.0.32 (2022-10-14)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5675-1.

0.0.31 (2022-09-12)
===================

- Move project directory from ``/root/lpcraft/project`` to
  ``/build/lpcraft/project``, making it more practical to drop privileges.

- Upgrade to craft-providers 1.4.2.

0.0.30 (2022-09-05)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5587-1/.

0.0.29 (2022-08-24)
===================

- Fix `lpcraft run --clean` when more than one job is run for the same series
  and architecture.

0.0.28 (2022-08-19)
===================

- Upgrade dependencies to their latest versions, most notably upgrading
  ``craft-cli`` from version `0.6.0` to `1.2.0`.

0.0.27 (2022-08-19)
===================

- Improve exception message for handling input when there are multiple jobs.

0.0.26 (2022-08-12)
===================

- Enable providing additional repositories via CLI.

0.0.25 (2022-08-09)
===================

- Add input properties, allowing jobs to use artifacts built by previous
  pipeline stages.

- Fix handling of ``license`` in the case where a job has an ``output`` key
  but no ``properties`` key under that.

- Deprecate ``--apt-replace-repositories``, introduce
  ``--replace-package-repositories``.

0.0.24 (2022-08-05)
===================

- Enable adding license information via the `.launchpad.yaml` configuration
  file.

0.0.23 (2022-08-03)
===================

- Rearrange output directory structure to improve support for matrix jobs
  and to prepare for passing input artifacts to jobs.

0.0.22 (2022-08-01)
===================

- Upgrade to craft-providers 1.3.1, improving snap installation logic.

0.0.21 (2022-07-19)
===================

- Add Golang plugin.

0.0.20 (2022-07-15)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5519-1.

0.0.19 (2022-07-11)
===================

- Add new CLI option to provide secrets via a YAML-based configuration file.

- Allow overriding APT's security checks via `PackageRepository.trusted`.


0.0.18 (2022-07-04)
===================

- Use the ``craft-cli`` command dispatcher.

- Hide the internal ``run-one`` command from ``--help`` output.

- Add new configuration option to provide additional package repositories.

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5495-1/.

0.0.17 (2022-06-17)
===================

- Add support for running jobs on Ubuntu 22.04 (jammy).

0.0.16 (2022-06-16)
===================

- Rewrite the release documentation.

- Add CLI support for plugin settings via "--plugin-setting".

- Add support for custom Conda channels.

0.0.15 (2022-06-01)
===================

- Allow ``run-before`` and ``run-after`` in ``.launchpad.yaml`` config.

- Add ``lpcraft_execute_before_run`` and ``lpcraft_execute_after_run`` hooks.

- Add support for pydantic configuration on plugin classes.

- Allow interpolation of the  ``run`` commands.

- Add Miniconda plugin.

0.0.14 (2022-05-18)
===================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5424-1.

0.0.13 (2022-05-12)
===================

- Always update apt cache index before installing a package.

0.0.12 (2022-05-12)
===================

- Update requirements.

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5412-1.

0.0.11 (2022-04-29)
===================

- Add new optional and repeatable argument ``--apt-replace-repositories`` which
  overwrites ``/etc/apt/sources.list``.

- Add minimal CLI interface documentation.

- Add new optional and repeatable argument ``--set-env`` which allows passing
  in environment variables.

0.0.10  (2022-04-27)
====================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5376-3.

0.0.9   (2022-04-19)
====================

- Allow ``output.paths`` to reference the parent directory of the build
  tree, in order to make life easier for build systems such as
  ``dpkg-buildpackage`` that write output files to their parent directory.

- Fix handling of the ``--output-directory`` option to the ``run-one``
  command.

0.0.8   (2022-04-13)
====================

- Rebuild the Snap package to include updated system packages.
  See https://ubuntu.com/security/notices/USN-5376-1.

0.0.7   (2022-04-08)
====================

- tox plugin: Work around https://github.com/tox-dev/tox/issues/2372 by
  telling ``tox`` to pass through lower-case ``http_proxy`` and
  ``https_proxy`` environment variables.

0.0.6   (2022-04-05)
====================

- Sphinx: Turn warnings into errors.

- pre-commit: Update the ``black`` hook to fix an incompatibility with
  ``click==8.1.0``.

- pre-commit: Add the ``pydocstyle`` hook to lint the docstrings.

- tox: The ``pip-compile`` env now upgrades the project's dependencies.

- Require the configuration file to be present under the project directory.

0.0.5   (2022-03-30)
====================

- Add the tox usage details to CONTRIBUTING.rst

- Add a ``clean`` command to allow cleaning a project's managed environments.
  Also add a ``--clean`` flag to the ``run`` and ``run-one`` commands
  to automatically clean the managed environments created during a run.

0.0.4   (2022-03-03)
====================

- Add note that containers will not be deleted automatically.

- Show error message when there are no matching output files,
  see https://bugs.launchpad.net/lpcraft/+bug/1962774

0.0.3   (2022-02-23)
====================

- Do not hide system package installation errors.

0.0.2   (2022-02-23)
====================

- Rebuild Snap package to include updated system packages,
  see https://ubuntu.com/security/notices/USN-5301-1


0.0.1   (2022-01-24)
====================

- Initial release.
