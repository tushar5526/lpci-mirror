===============
Version history
===============

0.0.10  (unreleased)
====================

- nothing yet

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
