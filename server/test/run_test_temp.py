import importlib.util
spec = importlib.util.spec_from_file_location('test_mod','server/test/test_enddate_inference.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Running test...')
try:
    mod.test_end_date_inferred_from_duration_and_start()
    print('TEST PASSED')
except AssertionError as e:
    print('TEST FAILED', e)
except Exception as e:
    print('TEST ERROR', e)
