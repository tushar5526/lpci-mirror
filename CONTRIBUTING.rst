Developing
==========

Prerequisites
-------------

* Python 3.8+
* `tox <https://tox.wiki/en/latest/>`_

Usage
-----

Install the ``lpci`` project in editable mode inside a virtualenv environment named ``venv``.

  .. code:: bash

    $ tox --devenv venv
    $ venv/bin/lpci --help  # Alternatively, you can activate the virtualenv environment.

List the ``tox`` environments available for this project.

  .. code:: bash

    $ tox -lv
    default environments:
    lint     -> run linters
    mypy     -> run static type checker
    py38     -> run test suite
    py39     -> run test suite
    py310    -> run test suite
    py311    -> run test suite
    coverage -> generate coverage report

Run the project's tests.

  .. code:: bash

    $ tox -e py38  #  You can replace ``py38`` with another Python version.

Since ``tox`` uses `pytest <https://docs.pytest.org/>`_ under the hood to run
the tests, arguments can be passed to ``pytest``.

  .. code:: bash

    $ tox -e py38 -- lpci/commands/tests/test_run.py
    $ tox -e py38 -- -k test_missing_config_file
    $ tox -e py39 -- --lf

Run the tests with coverage.

  .. code:: bash

    $ tox -e coverage

Run the linters.

  .. code:: bash

    $ tox -e lint

We also support running linters via `pre-commit <https://pre-commit.com/>`_.
If you want ``pre-commit`` to run automatically on ``git commit``,
you need to run ``pre-commit install`` once.

Run the ``mypy`` static type checker.

  .. code:: bash

    $ tox -e mypy

Update the requirements and regenerate ``requirements.txt``.

  .. code:: bash

    $ <modify requirements.in>
    $ tox -e pip-compile

Build the documentation locally.

  .. code:: bash

    $ tox -e docs

.. note::

    In order to update the `project's documentation
    <https://lpci.readthedocs.io/en/latest/>`_ online,
    after having pushed your changes to the repository, you need to trigger a
    manual build on the project's dashboard on https://readthedocs.org.
