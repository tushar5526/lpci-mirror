Release process
===============

Prerequisites
*************
- In order to promote a Snap release from ``edge`` to ``stable``,
  you need publishing access, which you can get from Colin Watson.

How to create a new release
***************************

- create an MP with a release commit, with updated version number in
  ``setup.cfg`` and updated version number and release date in ``NEWS.rst``,
  following the `semver <https://semver.org/>`_ recommendations

- once the MP has been merged to the ``main`` branch,
  a `Launchpad recipe <https://launchpad.net/~launchpad/lpcraft/+snap/lpcraft>`_
  automatically builds and publishes Snap packages to the ``edge`` channel

- once the Snaps have been published,
  update your local Snap installation

      .. code:: bash

        snap refresh --edge lpcraft

- in order to make sure nothing is broken, run

      .. code:: bash

         lpcraft -v

- go to the `Releases page <https://snapcraft.io/lpcraft/releases>`_
  of the Snap store to promote the release from ``edge`` to ``stable``

    - click on the cog icon next to ``latest/edge``
    - select ``Promote/close``
    - click on ``Promote to: latest/stable``
    - finally, hit the ``Save`` button in the top right corner to apply the changes

Some additional information
***************************

- members of the Launchpad team can use the ``Request builds`` button
  on that recipe if they need updated builds urgently

- lpcraft currently only makes use of ``stable`` and ``edge``,
  though this may change in future if necessary

- most users, as well as default CI builds in Launchpad,
  should use the stable channel rather than the auto-built ``edge`` channel
