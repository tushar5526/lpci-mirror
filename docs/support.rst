Support
=======

Getting help
------------

In case you need help, do not hesitate to reach out to us:

    https://answers.launchpad.net/lpci

If you work at Canonical, you can also visit the ~Launchpad channel on
Mattermost.


Bugs and feature requests
-------------------------

If you encounter a bug or you would like to have a new feature implemented,
please report them at https://bugs.launchpad.net/lpci.


Known issues
------------

Apart from the currently open
`bug reports <https://bugs.launchpad.net/lpci>`_,
there are the following known issues for which there is no known solution:

- In order to keep the source tree clean,
  lpci mirrors the contents of the project into the lxd container
  (``/build/lpci/project/``).

  This may have unexpected side effects when your current work tree is not
  clean.

  This may also be a reason that the result you get when you run ``lpci``
  on your machine and on CI may diverge.

  In order to ensure that you can use ``lpci`` to test code that has not yet
  been committed,
  we do not currently intend to change this behaviour.
  However, you can simulate the behaviour of a CI run by making a fresh clone
  of your branch and running ``lpci`` there.
