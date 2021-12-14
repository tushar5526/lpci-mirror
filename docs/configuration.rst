Configuration file syntax
=========================

The default and preferred file name is ``.launchpad.yaml`` (with the leading
dot to keep it discreetly out of the way).

The following documentation makes reference to various behaviours of
Launchpad.  At the time of writing these have been designed but not yet
implemented.

Top-level configuration
-----------------------

``pipeline`` (required)
     List of stages; each stage is either a job name or a list of job names.
     If a stage is a list of job names, then those jobs are executed in
     parallel.  Stages are executed in series, and subsequent stages only
     execute if previous stages succeeded.

``jobs`` (required)
     Mapping of job names to job definitions.

Job definitions
---------------

``series`` (required)
     The name of the Ubuntu series used to run the job.

``architectures`` (required)
     An architecture or list of architectures on which to run the job.  If a
     list, this multiplies the job into one copy per architecture.

``packages`` (optional)
    Packages to install using ``apt`` as dependencies of this job.

``snaps`` (optional)
    Snaps to install as dependencies of this job.

``environment`` (optional)
    A mapping of environment variable names to values, to be set while
    running the job.

``run`` (optional)
    A string (possibly multi-line) containing shell commands to run for this
    job.

``output`` (optional)
    See the :ref:`output-properties` section below.

``matrix`` (optional)
    A list of mappings, each of which is a partial job definition.  The
    final list of concrete jobs to run for this job name is constructed by
    taking a copy of the job definition for each item in ``matrix``,
    removing the ``matrix`` key itself, and updating it with the contents of
    each item in turn.

.. _output-properties:

Output properties
-----------------

``paths`` (optional)
    A list of `Path.glob
    <https://docs.python.org/3/library/pathlib.html#pathlib.Path.glob>`_
    patterns; any files matching these patterns at the end of a successful
    build will be gathered by the build manager and attached to the build in
    Launchpad.  Paths may not escape the build tree.

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
