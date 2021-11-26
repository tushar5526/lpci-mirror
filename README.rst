=======
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

Running
=======

``lpcraft`` is mainly intended to be consumed as a snap.  Use ``snapcraft``
to build the snap, which you can then install using ``snap install --classic
--dangerous lpcraft_<version>_<architecture>.snap``.  (Once ``lpcraft`` is
more complete and stable, it will be made available from the snap store.)

You can run ``lpcraft`` from a directory containing ``.launchpad.yaml``,
although it won't do very much useful yet.

Developing
==========

Run tests using ``tox``.

If you need to modify ``requirements.in``, run ``tox -e pip-compile``
afterwards.
