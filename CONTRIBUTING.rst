Developing
==========

Prerequisites
-------------

* Python 3.8+
* `tox <https://tox.wiki/en/latest/>`_
* `pyenv <https://github.com/pyenv/pyenv>`_, if you want to use and test against
  multiple versions of Python

Usage
-----

Install the ``lpcraft`` project in editable mode inside a virtualenv environment named ``venv``.

  .. code:: bash

    $ tox --devenv venv
    $ venv/bin/lpcraft --help  # Alternatively, you can activate the virtualenv environment.

List the ``tox`` environments available for this project.

  .. code:: bash

    $ tox -l
    lint
    mypy
    py38
    py39
    py310

Run the project's tests.

  .. code:: bash

    $ tox -e py38  #  Replace with the installed Python version, if 3.8 is unavailable.

Since ``tox`` uses ``pytest`` under the hood to run the tests, arguments can be passed to pytest.

  .. code:: bash

    $ tox -e py38 -- lpcraft/commands/tests/test_run.py
    $ tox -e py38 -- -k test_missing_config_file
    $ tox -e py39 -- --lf

Run the tests with coverage.

  .. code:: bash

    $ tox -e coverage

Run the linter.

  .. code:: bash

    $ tox -e lint

Alternatively, you can run ``pre-commit install`` to install the git pre-commit hooks,
which run the linter.

Run the ``mypy`` static type checker.

  .. code:: bash

    $ tox -e mypy

Update the requirements and regenerate ``requirements.txt``.

  .. code:: bash

    $ <modify requirements.in>
    $ tox -e pip-compile

If any of the ``tox`` environments use a version of Python that is not installed, edit
``tox.ini`` and replace the value for the ``basepython`` key under that environment.

To update the `project's documentation
<https://lpcraft.readthedocs.io/en/latest/>`_, you need to trigger a manual
build on the project's dashboard on https://readthedocs.org.

Getting help
------------

If you find bugs in this package, you can report them here:

    https://launchpad.net/lpcraft
