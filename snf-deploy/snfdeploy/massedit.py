#!/usr/bin/env python
# encoding='cp1252'

"""A python bulk editor class to apply the same code to many files."""

# Copyright (c) 2012 Jerome Lecomte
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


__version__ = '0.61'  # UPDATE setup.py when changing version.
__author__ = 'Jerome Lecomte'
__license__ = 'MIT'


import os
import sys
import logging
import argparse
import difflib
# Most manip will involve re so we include it here for convenience.
import re  # pylint: disable=W0611
import fnmatch


logger = logging.getLogger(__name__)


class EditorError(RuntimeError):
    """Error raised by the Editor class."""
    pass


class Editor(object):
    """Processes input file or input line.

    Named arguments:
    code -- code expression to process the input with.
    """

    def __init__(self, **kwds):
        self.code_objs = dict()
        self._codes = []
        self.dry_run = None
        if 'module' in kwds:
            self.import_module(kwds['module'])
        if 'code' in kwds:
            self.append_code_expr(kwds['code'])
        if 'dry_run' in kwds:
            self.dry_run = kwds['dry_run']

    def __edit_line(self, line, code, code_obj):  # pylint: disable=R0201
        """Edit a line with one code object built in the ctor."""
        try:
            result = eval(code_obj, globals(), locals())
        except TypeError as ex:
            message = "failed to execute {0}: {1}".format(code, ex)
            logger.warning(message)
            raise EditorError(message)
        if not result:
            raise EditorError("cannot process line '{0}' with {1}".format(
                              line, code))
        elif isinstance(result, list) or isinstance(result, tuple):
            line = ' '.join([str(res_element) for res_element in result])
        else:
            line = str(result)
        return line

    def edit_line(self, line):
        """Edits a single line using the code expression."""
        for code, code_obj in self.code_objs.items():
            line = self.__edit_line(line, code, code_obj)
        return line

    def edit_file(self, file_name):
        """Edit file in place, returns a list of modifications (unified diff).

        Arguments:
        file_name -- The name of the file.
        dry_run -- only return differences, but do not edit the file.
        """
        with open(file_name, "r") as from_file:
            from_lines = from_file.readlines()
            to_lines = [self.edit_line(line) for line in from_lines]
            diffs = difflib.unified_diff(from_lines, to_lines,
                                         fromfile=file_name, tofile='<new>')
        if not self.dry_run:
            bak_file_name = file_name + ".bak"
            if os.path.exists(bak_file_name):
                raise EditorError("{0} already exists".format(bak_file_name))
            try:
                os.rename(file_name, bak_file_name)
                with open(file_name, "w") as new_file:
                    new_file.writelines(to_lines)
                os.unlink(bak_file_name)
            except:
                os.rename(bak_file_name, file_name)
                raise
        return list(diffs)

    def append_code_expr(self, code):
        """Compiles argument and adds it to the list of code objects."""
        assert(isinstance(code, str))  # expect a string.
        logger.debug("compiling code {0}...".format(code))
        try:
            code_obj = compile(code, '<string>', 'eval')
            self.code_objs[code] = code_obj
        except SyntaxError as syntax_err:
            logger.error("cannot compile {0}: {1}".format(
                code, syntax_err))
            raise
        logger.debug("compiled code {0}".format(code))

    def set_code_expr(self, codes):
        """Convenience: sets all the code expressions at once."""
        self.code_objs = dict()
        self._codes = []
        for code in codes:
            self.append_code_expr(code)

    def import_module(self, module):  # pylint: disable=R0201
        """Imports module that are needed for the code expr to compile.

        Argument:
        module -- can be scalar string or a list of strings.
        """
        if isinstance(module, list):
            all_modules = module
        else:
            all_modules = [module]
        for mod in all_modules:
            globals()[mod] = __import__(mod.strip())


def parse_command_line(argv):
    """Parses command line argument. See -h option

    argv -- arguments on the command line including the caller file.
    """
    example = """
    example: {0} -e "re.sub('failIf', 'assertFalse', line)" *.py
    """
    example = example.format(os.path.basename(argv[0]))
    if sys.version_info[0] < 3:
        parser = argparse.ArgumentParser(description="Python mass editor",
                                         version=__version__,
                                         epilog=example)
    else:
        parser = argparse.ArgumentParser(description="Python mass editor",
                                         epilog=example)
        parser.add_argument("-v", "--version", action="version",
                            version="%(prog)s {}".format(__version__))
    parser.add_argument("-w", "--write", dest="dry_run",
                        action="store_false", default=True,
                        help="modify target file(s) in place. "
                        "Shows diff otherwise.")
    parser.add_argument("-V", "--verbose", dest="verbose_count",
                        action="count", default=0,
                        help="increases log verbosity (can be specified "
                        "multiple times)")
    parser.add_argument('-e', "--expression", dest="expressions", nargs=1,
                        help="Python expressions to be applied on all files. "
                        "Use the line variable to reference the current line.")
    parser.add_argument("-s", "--start", dest="start_dir",
                        help="Starting directory in which to look for the "
                        "files. If there is one pattern only and it includes "
                        "a directory, the start dir will be that directory "
                        "and the max depth level will be set to 1.")
    parser.add_argument('-m', "--max-depth-level", type=int, dest="max_depth",
                        help="Maximum depth when walking subdirectories.")
    parser.add_argument('-o', '--output', metavar="output",
                        type=argparse.FileType('w'), default=sys.stdout,
                        help="redirect output to a file")
    parser.add_argument('patterns', metavar="pattern", nargs='+',
                        help="file patterns to process.")
    arguments = parser.parse_args(argv[1:])
    # Sets log level to WARN going more verbose for each new -V.
    logger.setLevel(max(3 - arguments.verbose_count, 0) * 10)
    return arguments


def edit_files(patterns, expressions,  # pylint: disable=R0913, R0914
               start_dir=None, max_depth=1, dry_run=True,
               output=sys.stdout):
    """Edits the files that match patterns with python expressions. Each
    expression is run (using eval()) line by line on each input file.

    Keyword Arguments:
    max_depth -- maximum recursion level when looking for file matches.
    start_dir -- directory where to start the file search.
    dry_run -- only display differences if True. Save modified file otherwise.
    output -- handle where the output should be redirected.
    """
    # Makes for a better diagnostic because str are also iterable.
    assert not isinstance(patterns, str), "patterns should be a list"
    assert not isinstance(expressions, str), "expressions should be a list"

    # Shortcut: if there is only one pattern, make sure we process just that.
    if len(patterns) == 1 and not start_dir:
        pattern = patterns[0]
        directory = os.path.dirname(pattern)
        if directory:
            patterns = [os.path.basename(pattern)]
            start_dir = directory
            max_depth = 1

    processed_paths = []
    editor = Editor(dry_run=dry_run)
    if expressions:
        editor.set_code_expr(expressions)
    if not start_dir:
        start_dir = os.getcwd()
    for root, dirs, files in os.walk(start_dir):  # pylint: disable=W0612
        if max_depth is not None:
            relpath = os.path.relpath(root, start=start_dir)
            depth = len(relpath.split(os.sep))
            if depth > max_depth:
                continue
        names = []
        for pattern in patterns:
            names += fnmatch.filter(files, pattern)
        for name in names:
            path = os.path.join(root, name)
            processed_paths.append(os.path.abspath(path))
            diffs = editor.edit_file(path)
            if dry_run:
                output.write("".join(diffs))
    if output != sys.stdout:
        output.close()
    return processed_paths


def command_line(argv):
    """Instantiate an editor and process arguments.

    Optional argument:
    processed_paths -- paths processed are appended to the list.
    """
    arguments = parse_command_line(argv)
    return edit_files(arguments.patterns, arguments.expressions,
                      start_dir=arguments.start_dir,
                      max_depth=arguments.max_depth,
                      dry_run=arguments.dry_run,
                      output=arguments.output)


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    try:
        command_line(sys.argv)
    finally:
        logging.shutdown()
