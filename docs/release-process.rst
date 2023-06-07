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
  a `Launchpad recipe
  <https://launchpad.net/~launchpad/lpci/+snap/lpci>`_
  automatically builds and publishes Snap packages to the ``edge`` channel

- once the Snaps have been published,
  update your local Snap installation

      .. code:: bash

        snap refresh --edge lpci

- in order to make sure nothing is broken, run

      .. code:: bash

         lpci -v

- go to the `Releases page <https://snapcraft.io/lpci/releases>`_
  of the Snap store to promote the release from ``edge`` to ``stable``

    - click on the cog icon next to ``latest/edge``
    - select ``Promote/close``
    - click on ``Promote to: latest/stable``
    - finally, hit the ``Save`` button in the top right corner to apply the changes

Some additional information
***************************
- It is best practice to use ``dev0`` version's suffix defining a new
  development version into ``setup.cfg`` after a release,
  so when building that version for testing, it does not show the old version number.
  Once we want to release, we remove the suffix, to indicate that
  this is no longer a development version.

- members of the Launchpad team can use the ``Request builds`` button
  on that recipe if they need updated builds urgently

- lpci currently only makes use of ``stable`` and ``edge``,
  though this may change in future if necessary

- most users, as well as default CI builds in Launchpad,
  should use the stable channel rather than the auto-built ``edge`` channel

Rebuilding for security fixes
*****************************

We often receive a notification from the Snap Store about the ``lpci`` snap being
built with packages from the Ubuntu archive that have since received security
updates.

To address this, we have to rebuild the snap from the `Launchpad recipe
<https://launchpad.net/~launchpad/lpci/+snap/lpci>`_ page by requesting new builds. Use
the default options that are pre-selected when doing this.

Once the builds have been completed and published to the Snap Store, follow the steps
in the ``How to create a new release`` section above, starting from the 3rd step about
refreshing the snap from the ``edge`` channel, to test and publish the updated snap
package.
