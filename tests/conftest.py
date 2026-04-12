import os
import sys

if sys.version_info[0] == 2:
    import imp
else:
    import importlib.machinery
    import importlib.util

slackroll_file = os.path.join(os.path.dirname(__file__), "..", "slackroll")

if sys.version_info[0] == 2:
    imp.load_source("slackroll", slackroll_file)
else:
    loader = importlib.machinery.SourceFileLoader("slackroll", slackroll_file)
    spec = importlib.util.spec_from_loader("slackroll", loader)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["slackroll"] = module
    spec.loader.exec_module(module)
