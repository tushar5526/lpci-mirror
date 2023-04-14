=============
CLI interface
=============

Please note that this is only a small selection of the available commands and
options.

Please run ``lpci --help`` to see all commands.

lpci run
--------

This command runs all jobs listed via pipelines from a configuration file.

**Example:**

``lpci run``

lpci run optional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``--package-repository`` (provide an additional repository), e.g.
  ``lpci run --package-repository "deb http://archive.ubuntu.com/ubuntu/ focal main restricted"``
  This option is repeatable.

- ``--plugin-setting``, e.g.
  ``lpci run --plugin-setting="foo=bar"``

  This option is repeatable.

- ``--replace-package-repositories SOURCE_LINE``, e.g.
  ``lpci run --replace-package-repositories "deb http://archive.ubuntu.com/ubuntu/ focal main restricted"``

  This option is repeatable.


- ``--secrets``, e.g.
  ``lpci run --secrets="<path-to-configuration-file>"``

  The configuration file should look like...

  .. code::

    key: secret
    another_key: another_secret

- ``--set-env KEY=VALUE``, e.g.
  ``lpci run --set-env="PIP_INDEX_URL=http://pypi.example.com/simple"``

  This option is repeatable.

- ``--gpu-nvidia`` (experimental)

  This option requires an NVIDIA GPU on the host system; if passed on a
  system without such a GPU, container setup will fail.

lpci run-one
------------

This command runs one specified job.

**Example:**

``lpci run-one test 0``

where ``test`` is the job name and ``0`` is the index of the job/matrix.

lpci run-one optional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``--package-repository`` (provide an additional repository), e.g.
  ``lpci run-one --package-repository "deb http://archive.ubuntu.com/ubuntu/ focal main restricted" test 0``
  This option is repeatable.

- ``--plugin-setting``, e.g.
  ``lpci run-one --plugin-setting="foo=bar" test 0``

  This option is repeatable.

- ``--replace-package-repositories SOURCE_LINE``, e.g.
  ``lpci run-one --replace-package-repositories "deb http://archive.ubuntu.com/ubuntu/ focal main restricted" test 0``

  This option is repeatable.

- ``--secrets``, e.g.
  ``lpci run-one --secrets="<path-to-configuration-file>" test 0``

  The configuration file should look like...

  .. code::

    key: secret
    another_key: another_secret

- ``--set-env KEY=VALUE``, e.g.
  ``lpci run-one --set-env="PIP_INDEX_URL=http://pypi.example.com/simple" test 0``

  This option is repeatable.

lpci release
------------

This command releases a Launchpad build of a commit to a target archive
(which must be configured with a repository format that accepts packages of
the appropriate type).  It checks that the commit in question was
successfully built and has some attached files.

**Example:**

``lpci release ppa:ubuntu-security/soss/soss-python-stable-local focal edge``

lpci release optional arguments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``--launchpad INSTANCE`` to use a Launchpad instance other than
  production.

- ``--dry-run`` to just report what would be done rather than actually
  performing a release.

- ``--repository URL`` to specify the source Git repository URL (defaults to
  the upstream repository for the current branch, if on
  ``git.launchpad.net``).

- ``--commit ID`` to specify the source Git branch name, tag name, or commit
  ID (defaults to the tip commit found for the current branch in the
  upstream repository).
