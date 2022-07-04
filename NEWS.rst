===============
Version history
===============

0.0.18
======

- Use the ``craft-cli`` command dispatcher.

- Hide the internal ``run-one`` command from ``--help`` output.

- Add new configuration option to provide additional package repositories.

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
