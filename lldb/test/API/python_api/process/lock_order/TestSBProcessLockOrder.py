import lldb
import threading
from lldbsuite.test.lldbtest import *
from lldbsuite.test import lldbutil


class SBProcessLockOrderTestCase(TestBase):
    NO_DEBUG_INFO_TESTCASE = True

    def test_sbprocess_order_matches_continue_command_order(self):
        """
        Test that functions (such as GetNumThreads and GetThreadAtIndex) that
        are supposed to be safe to call concurrently with state-affecting
        commands (such as "continue") indeed do not lead to a deadlock.

        The problem is that some SB API calls take both the API lock and the
        run lock, and to avoid deadlocks, the locks must always be taken in the
        same order. For example, debugger.HandleCommand("continue") takes the
        API lock and passes control to the implementation of the "continue"
        command which then takes the run lock, so the order is:
        API lock -> run lock.
        At the same time, some methods of the SBProcess class used to take the
        run lock first and then the API lock, so an attempt to call such a
        method concurrently to the "continue" command would lead to a deadlock.
        """

        self.build()
        (target, process, _, _) = lldbutil.run_to_source_breakpoint(
            self, "break here", lldb.SBFileSpec("main.c")
        )

        keep_reading = True

        def concurrent_reader():
            while keep_reading:
                process.GetNumThreads()
                process.GetThreadAtIndex(0)

        thread = threading.Thread(target=concurrent_reader)
        thread.start()

        debugger = target.GetDebugger()
        old_async = debugger.GetAsync()
        debugger.SetAsync(False)

        while process.GetState() != lldb.eStateExited:
            debugger.HandleCommand("continue")

        debugger.SetAsync(old_async)

        keep_reading = False
        thread.join()
