#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    Rules for commit messages, branch names and everything:

    - All(!) commits to master branch must originate from pull-requests.
    - All pull-requests must be squash-merged or explicitly merged without rebase.
    - All pull-requests to master must have at least one label prefixed with `pr-`.
    - Labels that require pull-request to be backported must be red colored (#ff0000).
    - Stable branch name must be of form `YY.NUMBER`.
    - All stable branches must be forked directly from the master branch and never be merged back,
      or merged with any other branches based on the master branch (including master branch itself).

    Output of this script:

    - Commits without references from pull-requests.
    - Pull-requests to master without proper labels.

'''

from . import local, query

import argparse
import sys

CHECK_MARK = '🗸'
CROSS_MARK = '🗙'
AUTHOR_MARK = '⚠'


parser = argparse.ArgumentParser(description='Helper for the ClickHouse Release machinery')
parser.add_argument('--repo', '-r', type=str, default='', metavar='PATH',
    help='path to the root of the ClickHouse repository')
parser.add_argument('--remote', type=str, default='origin',
    help='remote name of the "yandex/ClickHouse" upstream')
parser.add_argument('-n', type=int, default=3, dest='number',
    help='number of last stable branches to consider')
parser.add_argument('--token', type=str, required=True,
    help='token for Github access')

args = parser.parse_args()

github = query.Query(args.token)
repo = local.Local(args.repo, args.remote, github.get_default_branch())

stables = repo.get_stables()[-args.number:]
if not stables:
    sys.exit('No stable branches found!')
else:
    print('Found stable branches:')
    for stable in stables:
        print(f'{CHECK_MARK} {stable[0]} forked from {stable[1]}')

first_commit = stables[0][1]
pull_requests = github.get_pull_requests(first_commit)
good_commits = set(oid[0] for oid in pull_requests.values())

bad_commits = [] # collect and print them in the end
from_commit = repo.get_head_commit()
for i in reversed(range(len(stables))):
    for commit in repo.iterate(from_commit, stables[i][1]):
        if str(commit) not in good_commits and commit.author.name != 'robot-clickhouse':
            bad_commits.append(commit)

    from_commit = stables[i][1]

bad_pull_requests = [] # collect and print if not empty
for num, value in pull_requests.items():
    label_found = False

    for label in value[1]:
        if label.startswith('pr-'):
            label_found = True
            break

    if not label_found:
        bad_pull_requests.append(num)

if bad_pull_requests:
    print('\nPull-requests without description label:', file=sys.stderr)
    for bad in reversed(sorted(bad_pull_requests)):
        print(f'{CROSS_MARK} {bad}')

# FIXME: compatibility logic, until the modification of master is not prohibited.
if bad_commits:
    print('\nCommits not referenced by any pull-request:', file=sys.stderr)

    bad_authors = set()
    for bad in bad_commits:
        print(f'{CROSS_MARK} {bad}', file=sys.stderr)
        bad_authors.add(bad.author)

    print('\nTell these authors not to push without pull-request and not to merge with rebase:')
    for author in sorted(bad_authors, key=lambda x : x.name):
        print(f'{AUTHOR_MARK} {author}')
