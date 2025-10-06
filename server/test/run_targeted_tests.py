import importlib
import sys
import traceback

sys.path.insert(0, r'C:/Users/dulha/GitHub/Seasonal_Travel_Recommender/server')

def run_followup():
    try:
        mod = importlib.import_module('test.followup_agent_test')
        t = mod.FollowupAgentTest()
        t.setUp()
        t.test_traveler_parsing()
        print('followup_agent_test.test_traveler_parsing: PASSED')
    except Exception:
        print('followup_agent_test.test_traveler_parsing: FAILED')
        traceback.print_exc()


def run_enddate():
    try:
        mod2 = importlib.import_module('test.test_enddate_inference')
        # Try to call a couple of expected test functions if present
        ran = False
        if hasattr(mod2, 'test_infer_end_date_from_duration'):
            try:
                mod2.test_infer_end_date_from_duration()
                print('test_enddate_inference.test_infer_end_date_from_duration: PASSED')
                ran = True
            except Exception:
                print('test_enddate_inference.test_infer_end_date_from_duration: FAILED')
                traceback.print_exc()
                ran = True
        if not ran:
            print('test_enddate_inference: No named test function to run directly; skipping')
    except Exception:
        print('test_enddate_inference: FAILED to import')
        traceback.print_exc()


if __name__ == '__main__':
    run_followup()
    run_enddate()
