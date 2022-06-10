from typing import Dict, Optional

import pluggy

from lpcraft.config import Job
from lpcraft.plugin import NAME, hookspecs
from lpcraft.plugin.lib import InternalPlugins
from lpcraft.plugins import PLUGINS


def get_plugin_manager(
    job: Job, plugin_settings: Optional[Dict[str, str]] = None
) -> pluggy.PluginManager:
    pm = pluggy.PluginManager(NAME)
    pm.add_hookspecs(hookspecs)

    # register internal plugins
    pm.register(InternalPlugins(job))

    # register builtin plugins
    if job.plugin:
        pm.register(PLUGINS[job.plugin](job, plugin_settings))

    return pm
