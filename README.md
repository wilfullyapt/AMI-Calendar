# AMI Calendar
**This calendar is a plugin for the [Artifical Modular Intelligence](https://github.com/wilfullyapt/ArtificialModularIntelligence) project**
*This repo is in development alongside the AMI project. Changes expected.*

As this is an init commit to the repo, here are the considerations for plugins for the AMI system:
- If there are additional libraries used by plugins, we want that is a basic `requirements.txt` file
- The AMI system uses `git tag` to know the which version of the plugin is being used. Version is used for debuging and as of right now, required per the code.
- The `__init__.py` file should be the exposure point for the plugin objects. `get_headspace()`, `get_blueprint()`, and `get_gui()`.
- The `__init__.py` can optionally include a `get_router()` that returns a string defining functionality to the LLM.

This repo is not to this point yet, but is necessary for testing currently.
