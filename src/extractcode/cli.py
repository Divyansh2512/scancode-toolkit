#
# Copyright (c) 2018 nexB Inc. and others. All rights reserved.
# http://nexb.com and https://github.com/nexB/scancode-toolkit/
# The ScanCode software is licensed under the Apache License version 2.0.
# Data generated with ScanCode require an acknowledgment.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# When you publish or redistribute any data created with ScanCode or any ScanCode
# derivative work, you must accompany this data with the following acknowledgment:
#
#  Generated with ScanCode and provided on an "AS IS" BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, either express or implied. No content created from
#  ScanCode should be considered or used as legal advice. Consult an Attorney
#  for any legal advice.
#  ScanCode is a free software code scanning tool from nexB Inc. and others.
#  Visit https://github.com/nexB/scancode-toolkit/ for support and download.

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

from functools import partial
from os import path

import click
click.disable_unicode_literals_warning = True

from commoncode import cliutils
from commoncode import compat
from commoncode import fileutils
from commoncode import filetype
from commoncode.text import toascii

from extractcode.api import extract_archives


__version__ = '2020.09.21'


echo_stderr = partial(click.secho, err=True)


def print_version(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    echo_stderr('ExtractCode version ' + __version__)
    ctx.exit()

info_text = '''
ExtractCode is a mostly universal archive and compressed files extractor, with 
a particular focus on code archives.
Visit https://github.com/nexB/scancode-toolkit/ for support and download.

'''

notice_path = path.join(path.abspath(path.dirname(__file__)), 'NOTICE')
notice_text = open(notice_path).read()

delimiter = '\n\n\n'
[notice_text, extra_notice_text] = notice_text.split(delimiter, 1)
extra_notice_text = delimiter + extra_notice_text

delimiter = '\n\n  '
[notice_text, acknowledgment_text] = notice_text.split(delimiter, 1)
acknowledgment_text = delimiter + acknowledgment_text

notice = acknowledgment_text.strip().replace('  ', '')


def print_about(ctx, param, value):
    """
    Click callback to print a notice.
    """
    if not value or ctx.resilient_parsing:
        return
    click.echo(info_text + notice_text + acknowledgment_text + extra_notice_text)
    ctx.exit()


epilog_text = '''\b\bExamples:

(Note for Windows: use '\\' backslash instead of '/' slash for paths.)

\b
Extract all archives found in the 'samples' directory tree:

    extractcode samples

Note: If an archive contains other archives, all contained archives will be
extracted recursively. Extraction is done directly in the 'samples' directory,
side-by-side with each archive. Files are extracted in a directory named after
the archive with an '-extract' suffix added to its name, created side-by-side
with the corresponding archive file.

\b
Extract a single archive. Files are extracted in the directory
'samples/arch/zlib.tar.gz-extract/':

    extractcode samples/arch/zlib.tar.gz
'''


class ExtractCommand(cliutils.BaseCommand):
    short_usage_help = '''
Try 'extractcode --help' for help on options and arguments.'''


@click.command(name='extractcode', epilog=epilog_text, cls=ExtractCommand)
@click.pass_context

@click.argument('input', metavar='<input>', type=click.Path(exists=True, readable=True, path_type=fileutils.PATH_TYPE))

@click.option('--verbose', is_flag=True, default=False, help='Print verbose file-by-file progress messages.')
@click.option('--quiet', is_flag=True, default=False, help='Do not print any summary or progress message.')
@click.option('--shallow', is_flag=True, default=False, help='Do not extract recursively nested archives (e.g. not archives in archives).')
@click.option('--replace-originals', is_flag=True, default=False, help='Replace extracted archives by the extracted content.')
@click.option('--ignore', default=[], multiple=True, help='Ignore files/directories following a glob-pattern.')

@click.help_option('-h', '--help')
@click.option('--about', is_flag=True, is_eager=True, callback=print_about, help='Show information about ExtractCode and licensing and exit.')
@click.option('--version', is_flag=True, is_eager=True, callback=print_version, help='Show the version and exit.')
def extractcode(ctx, input, verbose, quiet, shallow, replace_originals, ignore, *args, **kwargs):  # NOQA
    """extract archives and compressed files found in the <input> file or directory tree.

    Archives found inside an extracted archive are extracted recursively.
    Extraction for each archive is done in-place in a new directory named 
    '<archive file name>-extract' created side-by-side with an archive.
    """

    abs_location = fileutils.as_posixpath(path.abspath(path.expanduser(input)))

    def extract_event(item):
        """
        Display an extract event.
        """
        if quiet:
            return ''
        if not item:
            return ''
        source = item.source
        if not isinstance(source, compat.unicode):
            source = toascii(source, translit=True).decode('utf-8', 'replace')
        if verbose:
            if item.done:
                return ''
            line = source and get_relative_path(path=source, len_base_path=len_base_path, base_is_dir=base_is_dir) or ''
        else:
            line = source and fileutils.file_name(source) or ''
        if not isinstance(line, compat.unicode):
            line = toascii(line, translit=True).decode('utf-8', 'replace')
        return 'Extracting: %(line)s' % locals()

    def display_extract_summary():
        """
        Display a summary of warnings and errors if any.
        """
        has_warnings = False
        has_errors = False
        summary = []
        for xev in extract_result_with_errors:
            has_errors = has_errors or bool(xev.errors)
            has_warnings = has_warnings or bool(xev.warnings)
            source = fileutils.as_posixpath(xev.source)
            if not isinstance(source, compat.unicode):
                source = toascii(source, translit=True).decode('utf-8', 'replace')
                source = get_relative_path(path=source, len_base_path=len_base_path, base_is_dir=base_is_dir)
            for e in xev.errors:
                echo_stderr('ERROR extracting: %(source)s: %(e)s' % locals(), fg='red')
            for warn in xev.warnings:
                echo_stderr('WARNING extracting: %(source)s: %(warn)s' % locals(), fg='yellow')

        summary_color = 'green'
        if has_warnings:
            summary_color = 'yellow'
        if has_errors:
            summary_color = 'red'

        echo_stderr('Extracting done.', fg=summary_color, reset=True)

    # use for relative paths computation
    len_base_path = len(abs_location)
    base_is_dir = filetype.is_dir(abs_location)

    extract_result_with_errors = []
    unique_extract_events_with_errors = set()
    has_extract_errors = False
    
    extractibles = extract_archives(
        abs_location, recurse=not shallow, replace_originals=replace_originals, ignore_pattern=ignore)

    if not quiet:
        echo_stderr('Extracting archives...', fg='green')
        with cliutils.progressmanager(extractibles,
            item_show_func=extract_event, verbose=verbose) as extraction_events:

            for xev in extraction_events:
                if xev.done and (xev.warnings or xev.errors):
                    has_extract_errors = has_extract_errors or xev.errors
                    if repr(xev) not in unique_extract_events_with_errors:
                        extract_result_with_errors.append(xev)
                        unique_extract_events_with_errors.add(repr(xev))
        display_extract_summary()
    else:
        for xev in extractibles:
            if xev.done and (xev.warnings or xev.errors):
                has_extract_errors = has_extract_errors or xev.errors

    rc = 1 if has_extract_errors else 0
    ctx.exit(rc)


def get_relative_path(path, len_base_path, base_is_dir):
    """
    Return a posix relative path from the posix 'path' relative to a
    base path of `len_base_path` length where the base is a directory if
    `base_is_dir` True or a file otherwise.
    """
    path = fileutils.fsdecode(path)
    if base_is_dir:
        rel_path = path[len_base_path:]
    else:
        rel_path = fileutils.file_name(path)

    return rel_path.lstrip('/')