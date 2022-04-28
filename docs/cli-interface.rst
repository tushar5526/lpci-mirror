=======================
lpcraft - CLI interface
=======================

Please note that this is only a small selection of the available commands and
options.

Please run ``lpcraft --help`` to see all commands.

lpcraft run
-----------

This command runs all jobs listed via pipelines from a configuration file.

**Example:**

``lpcraft run``

lpcraft run optional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``--apt-replace-repositories SOURCE_LINE``, e.g.
  ``lpcraft run --apt-replace-repositories "deb http://archive.ubuntu.com/ubuntu/ focal main restricted"``.
  Please note that the option is repeatable.

- ``--set-env KEY=VALUE``, e.g.
  ``lpcraft run --set-env="PIP_INDEX_URL=http://pypi.example.com/simple"``

lpcraft run-one
---------------

This command runs one specified job.

**Example:**

``lpcraft run-one test 0``

where ``test`` is the job name and ``0`` is the index of the job/matrix.

lpcraft run-one optional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``--apt-replace-repositories SOURCE_LINE``, e.g.
  ``lpcraft run-one --apt-replace-repositories "deb http://archive.ubuntu.com/ubuntu/ focal main restricted" test 0``.
  Please note that the option is repeatable.

- ``--set-env KEY=VALUE``, e.g.
  ``lpcraft run-one --set-env="PIP_INDEX_URL=http://pypi.example.com/simple" test 0``.
