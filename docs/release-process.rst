Release process
===============

The lpcraft snap is automatically built for all supported architectures and
released to the ``edge`` channel in the snap store using a `Launchpad recipe
<https://launchpad.net/~launchpad/lpcraft/+snap/lpcraft>`_.  Builds run
shortly after pushes to the ``main`` Git branch; members of the Launchpad
team can use the "Request builds" button on that recipe if they need updated
builds urgently.

Most users, as well as default CI builds in Launchpad, should use the
``stable`` channel rather than the auto-built ``edge`` channel.  People with
publishing access to the snap in the store can promote revisions to
``stable`` (ask Colin Watson for access if you need it).  The easiest way to
do this across all architectures is to use the store's `Releases page
<https://snapcraft.io/lpcraft/releases>`_: click on the cog icon next to
"latest/edge" and select "Promote to: latest/stable".

Version numbers in snaps are for human consumption (the revision is assigned
by the store and is what matters to ``snapd``), and there's nothing to stop
multiple revisions of a snap having the same version number, though of
course it's less confusing if substantially different revisions have
substantially different version numbers as well.  Use `semver
<https://semver.org/>`_, and update ``NEWS.rst`` when making significant
user-visible changes.  Make sure there's a git tag for the old version
number before you bump to a new version number.

We don't yet have a defined QA process for making new releases to
``stable``, although it's a good idea to smoke-test that the snap isn't
obviously broken.  Use ``snap refresh --edge lpcraft`` to ensure that you're
running the latest revision from the ``edge`` channel in the store, and then
do whatever testing you need to do; for example, you might run lpcraft's own
tests using ``lpcraft -v``.

We don't yet use channels other than ``stable`` and ``edge``, though there's
no particular reason not to do so if they become useful.
