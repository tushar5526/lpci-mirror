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

``lpcraft`` is mainly intended to be consumed as a snap.  Simply install with
``sudo snap install lpcraft --classic``.

You can also run ``lpcraft run`` from a directory containing ``.launchpad.yaml``.

To save the output from a job, use ``lpcraft run --output-directory
/path/to/output/directory``.
