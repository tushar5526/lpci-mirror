Extending lpcraft
=================

lpcraft uses `pluggy <https://pluggy.readthedocs.io/>`_ to customize the
default behaviour. For example the following code snippet would extend the
packages which need to be installed into an environment by additional
requirements:

.. code-block:: python

    from lpcraft.plugin import hookimpl


    @hookimpl
    def lpcraft_install_packages():
        return ["tox"]

Plugin discovery
----------------

As currently only builtin plugins are supported,
you need to define a plugin in ``lpcraft/plugins/<plugin>``
and import the module in ``lpcraft/plugins/__init__.py``.

Plugin implementation
---------------------

Please consult the `pluggy <https://pluggy.readthedocs.io/>`_  documentation,
and have a look at the ``lpcraft/plugins`` directory for inspiration.

Name of the hook
****************

.. automodule:: lpcraft.plugin
   :members:
   :exclude-members: hookimpl

Implementation marker
*********************

.. autodata:: lpcraft.plugin.hookimpl
   :no-value:

Available hooks
***************

.. automodule:: lpcraft.plugin.hookspecs
   :members:

.. _plugin_configuration_keys:

Additional configuration keys
*****************************

Plugins can have their own configuration keys.

.. code-block:: python

    @register(name="miniconda")
    class MiniCondaPlugin(BasePlugin):
        class Config(BaseConfig):
            conda_packages: Optional[List[StrictStr]]
            conda_python: Optional[StrictStr]

The above code defines the ``MiniCondaPlugin`` with two additional configuration
keys.

These keys could be used in the ``.launchpad.yaml`` configuration file as
following:

.. code-block:: yaml

    jobs:
        myjob:
            plugin: miniconda
            conda-packages:
                - mamba
                - numpy=1.17
                - scipy
                - pip
            conda-python: 3.8
            run: |
                pip install --upgrade pytest
                python -m build .

Interpolation of run commands
*****************************

By default a ``run`` command in the configuration file overrides the command
defined by the plugin, if any, unless the plugin class sets
``INTERPOLATES_RUN_COMMANDS`` to ``True``, in which case the plugin can
interpolate the command, like in the following example:

.. code-block:: python

    class MiniCondaPlugin(BasePlugin):
        INTERPOLATES_RUN_COMMAND = True

        @hookimpl
        def lpcraft_execute_run(self) -> str:
            run = self.config.run or ""
            return textwrap.dedent(
                f"""\
                export PATH=$HOME/miniconda3/bin:$PATH
                source activate $CONDA_ENV
                {run}"""
            )

This applies to the ``run-before``, the ``run``,  and the ``run-after``
commands.


Builtin plugins
---------------

.. automodule:: lpcraft.plugins.plugins
   :members:

Using a builtin plugin
----------------------

In order to use a plugin,
it has to be specified via the ``plugin`` key in the job definition.

.. code-block:: yaml

    pipeline:
        - test

    jobs:
        test:
            series: focal
            architectures: amd64
            plugin: tox
