Configuration file syntax
=========================

The default and preferred file name is ``.launchpad.yaml`` (with the leading
dot to keep it discreetly out of the way).

The following documentation makes reference to various behaviours of
Launchpad.  At the time of writing these have been designed but not yet
implemented.

.. _identifiers:

Identifiers
-----------

Several configuration file keys accept *identifiers*: these must begin with
an ASCII lower-case letter or number, must be at least two characters long,
and may only contain ASCII lower-case letters or numbers, ``+``, ``.``,
``_``, or ``-``.

Top-level configuration
-----------------------

``pipeline`` (required)
     List of stages; each stage is either a job name or a list of job names.
     If a stage is a list of job names, then those jobs are executed in
     parallel.  Stages are executed in series, and subsequent stages only
     execute if previous stages succeeded.

     Job names are :ref:`identifiers <identifiers>`.

``jobs`` (required)
     Mapping of job names (:ref:`identifiers <identifiers>`) to job
     definitions.

``license`` (optional)
     The :ref:`license <license-properties>` info for the given repository can
     be configured either via an
     `spdx identifier <https://spdx.org/licenses/>`_
     or a relative path to the license file.

Job definitions
---------------

``series`` (required)
     The name of the Ubuntu series used to run the job.

     Series names are :ref:`identifiers <identifiers>`.

``architectures`` (required)
     An architecture or list of architectures on which to run the job.  If a
     list, this multiplies the job into one copy per architecture.

     Architecture names are :ref:`identifiers <identifiers>`.

``packages`` (optional)
    Packages to install using ``apt`` as dependencies of this job.

``package-repositories`` (optional)
    Repositories which will be added to the already existing ones in
    `/etc/apt/sources.list`.
    Also see the :ref:`package-repositories` section below.

``snaps`` (optional)
    Snaps to install as dependencies of this job.

``environment`` (optional)
    A mapping of environment variable names to values, to be set while
    running the job.

``plugin`` (optional)
    A plugin which will be used for this job. See :doc:`../plugins`

``run-before`` (optional)
    A string (possibly multi-line) containing shell commands to run for this
    job prior to the main ``run`` section.

``run`` (optional)
    A string (possibly multi-line) containing shell commands to run for this
    job.

``run-after`` (optional)
    A string (possibly multi-line) containing shell commands to run for this
    job after the main ``run`` section.

``output`` (optional)
    See the :ref:`output-properties` section below.

``input`` (optional)
    See the :ref:`input-properties` section below.

``matrix`` (optional)
    A list of mappings, each of which is a partial job definition.  The
    final list of concrete jobs to run for this job name is constructed by
    taking a copy of the job definition for each item in ``matrix``,
    removing the ``matrix`` key itself, and updating it with the contents of
    each item in turn.

.. note::

    Plugins can define :ref:`plugin_configuration_keys`.

.. _output-properties:

Output properties
-----------------

``paths`` (optional)
    A list of `Path.glob
    <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_
    patterns; any files matching these patterns at the end of a successful
    build will be gathered by the build manager and attached to the build in
    Launchpad.  Paths may not escape the parent directory of the build tree.
    (The parent directory is allowed in order to make life easier for build
    systems such as ``dpkg-buildpackage`` that write output files to their
    parent directory.)

``distribute`` (optional)
    If ``artifactory``, then these artifacts may be distributed via
    Artifactory.

    Other valid values for ``distribute`` may be added in future.

``channels`` (optional)
    A list of initial channels to which these artifacts should be published
    (e.g. ``[edge]``).

``properties`` (optional)
    An arbitrary key/value mapping.  For Artifactory publication, these are
    attached as artifact properties; appropriate values depend on the
    package type.  Example properties include the human-readable version of
    the artifact.

``dynamic-properties`` (optional)
    A path (which may not escape the build tree), read using `python-dotenv
    <https://pypi.org/project/python-dotenv/>`_ and supplementing
    ``properties`` with the result.

``expires`` (optional)
    The requested minimum lifetime of the artifact in Launchpad.  Only
    relevant if ``distribute`` is not set or the artifact has not been
    successfully uploaded; an artifact that has been successfully uploaded
    is immediately eligible for garbage-collection from Launchpad, since it
    now exists elsewhere.

    This value is parsed using `pydantic's standard timedelta parsing
    <https://pydantic-docs.helpmanual.io/usage/types/#datetime-types>`_,
    restricted to non-negative timedeltas.

.. _input-properties:

Input properties
----------------

Input makes artifacts from previous pipeline stages available.  This only
works if those artifacts were saved using the ``--output-directory`` option
to ``lpcraft run``.

``lpcraft`` copies artifact data to the ``files`` subdirectory of the
designated target directory, and writes a ``properties`` file in the
designated target directory with JSON-encoded properties of the copied
artifacts.  (This mirrors the output file structure created by ``lpcraft run
--output-directory``.)

``job-name``
    The name of a previously-executed job whose artifacts should be made
    available.

``target-directory``
    A path, relative to the build tree of a project, identifying a directory
    to which the artifacts of the chosen job will be copied; the directory
    will be created if necessary.  Paths may not escape the build tree.

.. _package-repositories:

Package-repositories properties
-------------------------------

The properties are inspired by the properties of `Snapcraft
<https://snapcraft.io/docs/package-repositories>`_.
Only a subset of them is currently implemented. More
properties can be implemented on demand.

A ``PPA`` or a ``deb`` repository can be added using the below properties.

Adding a PPA
^^^^^^^^^^^^

``type`` (required)
    Specifies the type of package-repository.
    Currently only ``apt`` is supported.

``formats`` (required)
    Specifies the format of the package-repository.
    Supported values: ``deb`` and ``deb-src``.

``suites`` (required)
    Specifies the suite of the package-repository.
    One or several of ``bionic``, ``focal``, ``jammy``.

``ppa`` (required)
    Specifies the PPA to be used as the package repository in the short form,
    e.g. ``launchpad/ppa``, ``launchpad/debian/ppa``.

``trusted`` (optional)
    Set this to ``true`` to override APT's security checks, ie accept sources
    which do not pass authentication checks. ``false`` does the opposite.
    By default APT decides whether a source is considered trusted. This third
    option cannot be set explicitly.

Example:

.. code:: yaml

   package-repositories:
       - type: apt
         formats: [deb, deb-src]
         suites: [focal]
         ppa: launchpad/ubuntu/ppa
         trusted: false

Adding a deb repository
^^^^^^^^^^^^^^^^^^^^^^^

``type`` (required)
    Specifies the type of package-repository.
    Currently only ``apt`` is supported.

``formats`` (required)
    Specifies the format of the package-repository.
    Supported values: ``deb`` and ``deb-src``.

``suites`` (required)
    Specifies the suite of the package-repository.
    One or several of ``bionic``, ``focal``, ``jammy``.

``components`` (required)
    Specifies the component of the package-repository,
    One or several of ``main``, ``restricted``, ``universe``, ``multiverse``.

``url`` (required)
    Specifies the URL of the package-repository,
    e.g. ``http://ppa.launchpad.net/snappy-dev/snapcraft-daily/ubuntu``.
    The URL is rendered using `Jinja2 <https://pypi.org/project/Jinja2/>`_.
    This can be used to supply authentication details via the *secrets*
    command line option.

``trusted`` (optional)
    Set this to ``true`` to override APT's security checks, ie accept sources
    which do not pass authentication checks. ``false`` does the opposite.
    By default APT decides whether a source is considered trusted. This third
    option cannot be set explicitly.

Example:

.. code:: yaml

   package-repositories:
       - type: apt
         formats: [deb, deb-src]
         components: [main]
         suites: [focal]
         url: https://canonical.example.org/ubuntu
         trusted: false

.. _license-properties:

License properties
------------------

Please note that either `spdx` or `path` is required.

``spdx`` (optional)
     A string representing a license,
     see `spdx identifier <https://spdx.org/licenses/>`_.

``path`` (optional)
    A string with the relative path to the license file.
