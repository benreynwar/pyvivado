import unittest
import logging

from pyvivado import config

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    config.setup_logging(logging.WARNING)
    loader = unittest.TestLoader()
    testRunner = unittest.runner.TextTestRunner()
    test_suite = loader.discover('.', pattern='qa_*.py')
    testRunner.run(test_suite)
