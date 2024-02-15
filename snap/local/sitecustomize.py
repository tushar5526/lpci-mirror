import os
import site

snap_name = os.getenv("SNAP_NAME")
snap_dir = os.getenv("SNAP")

# Add the custom site directories only when executing in the context
# of the `lpci` snap and its snap directory exists.
if snap_name == "lpci" and snap_dir:
    site.ENABLE_USER_SITE = False
    site.addsitedir(os.path.join(snap_dir, "lib"))
    site.addsitedir(os.path.join(snap_dir, "usr/lib/python3/dist-packages"))
