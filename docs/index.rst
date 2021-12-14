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

    $ lpcraft run --output out
    Running the job
    $ cat out/test/focal/amd64/files/output
    hello world


.. toctree::
    :maxdepth: 2

    self
    configuration
    CONTRIBUTING
