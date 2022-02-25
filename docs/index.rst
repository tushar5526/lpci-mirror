.. lpcraft documentation master file, created by
   sphinx-quickstart on Tue Dec  7 12:44:23 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

lpcraft
=======

``lpcraft`` is a runner for continuous integration jobs in Launchpad.  It is
intended mainly for use in Launchpad builders, but can also be installed and
used locally on branches with a ``.launchpad.yaml`` file.

This project owes a considerable amount to `snapcraft
<https://github.com/snapcore/snapcraft>`_ and `charmcraft
<https://github.com/canonical/charmcraft>`_: the provider support for
container management is based substantially on ``charmcraft``, while much of
the CLI design is based on both those tools.

The development is in a very early stage.

Example configuration
---------------------

.. code:: bash

    $ cat .launchpad.yaml
    pipeline:
    - test

    jobs:
        test:
            series: focal
            architectures: amd64
            run: echo hello world >output
            output:
                paths: [output]

    $ lpcraft run --output-directory out
    Running the job
    $ cat out/test/focal/amd64/files/output
    hello world


.. note::

    `lpcraft` does not delete the container it creates.

    Also, `lpcraft` currently does not expose a command to do this manually.

    In order to delete all `lpcraft` related containers,
    you need to run the following command:

    .. code-block:: bash

        lxc --project lpcraft list -f csv -c n | xargs lxc delete -f


.. toctree::
    :maxdepth: 2

    self
    configuration
    plugins
    CONTRIBUTING
    release-process
    NEWS
