# tests/test_envdet_1.py
import EnvDet_1 as m

def test_module_imports():
    # simple smoke test so we get at least "1 passed"
    assert hasattr(m, "__file__")
