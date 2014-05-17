"""
Run Dispersy in standalone mode.
"""
import logging.config
import optparse  # deprecated since python 2.7
import os
import signal

from twisted.internet import reactor
from twisted.python.log import addObserver

from ..dispersy import Dispersy
from ..endpoint import StandaloneEndpoint
from ..logger import get_logger

# use logger.conf if it exists
if os.path.exists("logger.conf"):
    # will raise an exception when logger.conf is malformed
    logging.config.fileConfig("logger.conf")
    
# fallback to basic configuration when needed
logging.basicConfig(format="%(asctime)-15s [%(levelname)s] %(message)s")

logger = get_logger(__name__)


def load_community(dispersy, opt):
    try:
        module, classname = opt.community.strip().rsplit(".", 1)
        cls = getattr(__import__(module, fromlist=[classname]), classname)
    
    except Exception as exception:
        logger.exception("%s", exception)
        raise SystemExit(str(exception), "Invalid --script", opt.script)

    try:
        kargs = {}
        if opt.kargs:
            for karg in opt.kargs.split(","):
                if "=" in karg:
                    key, value = karg.split("=", 1)
                    kargs[key.strip()] = value.strip()
    except:
        raise SystemExit("Invalid --kargs", opt.kargs)

    dispersy.define_auto_load(cls, dispersy.get_new_member(), (), kargs, load=True)

def main_real():
    # define options
    command_line_parser = optparse.OptionParser()
    command_line_parser.add_option("--profiler", action="store_true", help="Attach cProfile on the Dispersy thread", default=False)
    command_line_parser.add_option("--memory-dump", action="store_true", help="Run meliae to dump the memory periodically", default=False)
    command_line_parser.add_option("--databasefile", action="store", help="Use an alternate databasefile", default=u"dispersy.db")
    command_line_parser.add_option("--workingdir", action="store", type="string", help="Use an alternate workingdir", default=u".")
    command_line_parser.add_option("--debugstatistics", action="store_true", help="turn on debug statistics", default=False)
    command_line_parser.add_option("--ip", action="store", type="string", default="0.0.0.0", help="Bind Dispersy to a specific ip-address")
    command_line_parser.add_option("--port", action="store", type="int", help="Bind Dispersy to a specific UDP port", default=12345)
    command_line_parser.add_option("--community", action="store", type="string", help="Specify the community to be auto loaded, e.g. module.module.class", default="")
    command_line_parser.add_option("--kargs", action="store", type="string", help="Pass these arguments to the community, e.g. 'x=1,y=2'")
    command_line_parser.add_option("--strict", action="store_true", help="Exit on any exception", default=False)

    # parse command-line arguments
    opt, args = command_line_parser.parse_args()
    if not opt.script:
        command_line_parser.print_help()
        exit(1)

    if opt.strict:
        from ..util import unhandled_error_observer
        addObserver(unhandled_error_observer)

    # setup
    dispersy = Dispersy(StandaloneEndpoint(opt.port, opt.ip), unicode(opt.workingdir), unicode(opt.databasefile))
    dispersy.statistics.enable_debug_statistics(opt.debugstatistics)

    def signal_handler(sig, frame):
        logger.warning("Received signal '%s' in %s (shutting down)", sig, frame)
        dispersy.stop()
        reactor.stop()
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # start
    if not dispersy.start():
        raise RuntimeError("Unable to start Dispersy")

    reactor.exitCode = 0
    reactor.callWhenRunning(0, load_community, dispersy, opt)
    
    # start the reactor
    reactor.run()
    exit(reactor.exitCode)