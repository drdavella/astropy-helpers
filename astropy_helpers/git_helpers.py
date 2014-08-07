# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""
Utilities for retrieving revision information from a project's git repository.
"""

# Do not remove the following comment; it is used by
# astropy_helpers.version_helpers to determine the beginning of the code in
# this module

# BEGIN

import locale
import os
import subprocess
import warnings


def update_git_devstr(version, path=None):
    """
    Updates the git revision string if and only if the path is being imported
    directly from a git working copy.  This ensures that the revision number in
    the version string is accurate.
    """

    try:
        # Quick way to determine if we're in git or not - returns '' if not
        devstr = get_git_devstr(sha=True, show_warning=False, path=path)
    except OSError:
        return version

    if not devstr:
        # Probably not in git so just pass silently
        return version

    if 'dev' in version:  # update to the current git revision
        version_base = version.split('.dev', 1)[0]
        devstr = get_git_devstr(sha=False, show_warning=False, path=path)

        return version_base + '.dev' + devstr
    else:
        #otherwise it's already the true/release version
        return version


def get_git_devstr(sha=False, show_warning=True, path=None):
    """
    Determines the number of revisions in this repository.

    Parameters
    ----------
    sha : bool
        If True, the full SHA1 hash will be returned. Otherwise, the total
        count of commits in the repository will be used as a "revision
        number".

    show_warning : bool
        If True, issue a warning if git returns an error code, otherwise errors
        pass silently.

    path : str or None
        If a string, specifies the directory to look in to find the git
        repository.  If `None`, the current working directory is used.
        If given a filename it uses the directory containing that file.

    Returns
    -------
    devversion : str
        Either a string with the revsion number (if `sha` is False), the
        SHA1 hash of the current commit (if `sha` is True), or an empty string
        if git version info could not be identified.

    """

    if path is None:
        path = os.getcwd()

    if not os.path.isdir(path):
        path = os.path.abspath(os.path.dirname(path))

    if not os.path.exists(os.path.join(path, '.git')):
        return ''

    if sha:
        # Faster for getting just the hash of HEAD
        cmd = ['rev-parse', 'HEAD']
    else:
        cmd = ['rev-list', '--count', 'HEAD']

    def run_git(cmd):
        try:
            p = subprocess.Popen(['git'] + cmd, cwd=path,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE)
            stdout, stderr = p.communicate()
        except OSError as e:
            if show_warning:
                warnings.warn('Error running git: ' + str(e))
            return (None, '', '')

        if p.returncode == 128:
            if show_warning:
                warnings.warn('No git repository present at {0!r}! Using '
                              'default dev version.'.format(path))
            return (p.returncode, '', '')
        elif p.returncode != 0:
            try:
                stderr_encoding = locale.getdefaultlocale()[1] or 'utf-8'
            except ValueError:
                stderr_encoding = 'utf-8'

            try:
                stderr_text = stderr.decode(stderr_encoding)
            except UnicodeDecodeError:
                # Final fallback
                stderr_text = stderr.decode('latin1')

            if show_warning:
                warnings.warn('Git failed while determining revision '
                              'count: {0}'.format(stderr_text))
            return (p.returncode, stdout, stderr)

        return p.returncode, stdout, stderr

    returncode, stdout, stderr = run_git(cmd)

    if not sha and returncode == 129:
        # git returns 129 if a command option failed to parse; in
        # particualr this could happen in git versions older than 1.7.2
        # where the --count option is not supported
        # Also use --abbrev-commit and --abbrev=0 to display the minimum
        # number of characters needed per-commit (rather than the full hash)
        cmd = ['rev-list', '--abbrev-commit', '--abbrev=0', 'HEAD']
        returncode, stdout, stderr = run_git(cmd)
        # Fall back on the old method of getting all revisions and counting
        # the lines
        if returncode == 0:
            return str(stdout.count(b'\n'))
        else:
            return ''
    elif sha:
        return stdout.decode('utf-8')[:40]
    else:
        return stdout.decode('utf-8').strip()
