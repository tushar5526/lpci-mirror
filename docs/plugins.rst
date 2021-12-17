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
you need to define a plugin in ``lpcraft/plugins/<plugin>``.


.. comments

    XXX jugmac00 2021-12-17: render all available hooks via plugin
