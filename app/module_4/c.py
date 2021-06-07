from module_common import *
from module_common.utils import printer

log = logging.getLogger(__name__)
printer("test")


def some_func():
    from module_common.utils import printer
    printer("testing")
