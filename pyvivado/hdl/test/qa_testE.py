import os
import logging
import random
import shutil

import pytest
import testfixtures

from pyvivado import test_utils, test_info, config, base_project

# Load module into registry
from pyvivado.hdl.test import testE

logger = logging.getLogger(__name__)


class TestTestE(test_utils.TestCase):

    def default_test(self):
        test_testE(
            sim_type=test_info.default_sim_type,
            pause=False,
        )

combinations = []
for sim_type in test_info.test_sim_types:
    combinations.append((sim_type))


@pytest.mark.parametrize('sim_type', combinations)
def test_testE(sim_type, pause=False):
    directory = os.path.join(config.testdir, 'proj_testE')
    # Delete the directory since this test is testing project creation and
    # updating.
    if os.path.exists(directory):
        shutil.rmtree(directory)

    class OnlyTest():

        def make_input_data(self):
            n_data = 20
            input_data = [{'i': random.randint(0, 1)} for i in range(n_data)]
            return input_data

        def check_output_data(self, input_data, output_data):
            for ind, outd in zip(input_data, output_data):
                assert(ind['i'] == outd['o'])

    params = {'factory_name': 'TestE'}
    tests = [OnlyTest()]

    def simulate_and_test(overwrite_ok):
        test_utils.simulate_and_test(
            reset_input={'i': 0},
            params=params,
            directory=directory,
            tests=tests,
            sim_type=sim_type,
            pause=pause,
            overwrite_ok=overwrite_ok,
        )
    # Run the test.
    simulate_and_test(overwrite_ok=False)
    # Now change the builder test_switch so that the file contents are
    # changed, but the file name is the same.
    testE.TestEBuilder.test_switch = 'COPYB'
    with testfixtures.ShouldRaise(base_project.OverwriteForbiddenException()):
        simulate_and_test(overwrite_ok=False)
    simulate_and_test(overwrite_ok=True)
    testE.TestEBuilder.test_switch = 'RAWA'
    with testfixtures.ShouldRaise(base_project.OverwriteForbiddenException()):
        simulate_and_test(overwrite_ok=False)
    simulate_and_test(overwrite_ok=True)
    testE.TestEBuilder.test_switch = 'RAWB'
    with testfixtures.ShouldRaise(base_project.OverwriteForbiddenException()):
        simulate_and_test(overwrite_ok=False)
    simulate_and_test(overwrite_ok=True)


if __name__ == '__main__':
    config.setup_logging(logging.INFO)
    test_utils.run_test(TestTestE)
