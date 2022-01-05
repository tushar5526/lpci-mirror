from typing import Any, Callable, Type, TypeVar

PLUGINS = dict()  #: Collection of builtin plugins


TypeT = TypeVar("TypeT", bound=Type[Any])


def register(name: str) -> Callable[[TypeT], TypeT]:
    # this function registers all decorated plugin classes
    # the result looks like:
    #
    # PLUGINS = {'tox': <class 'lpcraft.plugins.plugins.ToxPlugin'>}
    def inner(cls: TypeT) -> TypeT:
        PLUGINS[name] = cls
        return cls

    return inner


# for registration all modules which contain plugins need to be imported
# the imports must be at the bottom of the module to avoid circular imports
from lpcraft.plugins import plugins  # noqa: F401, E402
