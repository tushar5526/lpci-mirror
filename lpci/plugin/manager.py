from typing import Dict, Optional

import pluggy

from lpci.config import Job
from lpci.plugin import NAME, hookspecs
from lpci.plugin.lib import InternalPlugins
from lpci.plugins import PLUGINS


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
