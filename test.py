#!/usr/bin/python3

import argparse
import logging
import os
from pathlib import Path
import platform
from pprint import pprint
import shutil
import subprocess
import sys
from traceback import print_exc
from typing import Any, Dict, List

from module.args import parse_args
from module.path import ProjectPaths
from module.profile import ARCHES, ArchProfile
from module.util import ensure

def clean(config: argparse.Namespace, paths: ProjectPaths):
  if paths.test_dir.exists():
    shutil.rmtree(paths.test_dir)

def prepare_dirs(paths: ProjectPaths):
  shutil.copytree(
    paths.test_src_dir,
    paths.test_dir,
    ignore = shutil.ignore_patterns(
      '.cache',
      '.vscode',
      '.xmake',
      'build',
    ),
  )

def extract(path: Path, arx: Path):
  subprocess.run([
    'bsdtar',
    '-C', path,
    '-xf', arx,
    '--no-same-owner',
  ], check = True)

def prepare_test_binary(ver: ArchProfile, paths: ProjectPaths):
  extract(paths.test_dir, paths.linux_pkg)
  extract(paths.test_dir, paths.xmake_pkg)

def test_linux_compiler(ver: ArchProfile, paths: ProjectPaths, verbose: List[str]):
  rel_linux_dir = paths.test_linux_dir.relative_to(paths.test_dir)
  xmake = paths.test_linux_dir / 'bin/xmake'
  xmake_arch = ver.target.split('-')[0]
  subprocess.check_call([
    xmake, 'f', *verbose,
    '-p', 'linux', '-a', xmake_arch,
    f'--sdk={rel_linux_dir}',
  ], cwd = paths.test_dir)
  subprocess.check_call([xmake, 'b', *verbose], cwd = paths.test_dir)
  subprocess.check_call([xmake, 'test', *verbose], cwd = paths.test_dir)

def main():
  config = parse_args()

  if config.verbose >= 2:
    logging.basicConfig(level = logging.DEBUG)
    xmake_verbose = ['-vD']
  elif config.verbose >= 1:
    logging.basicConfig(level = logging.INFO)
    xmake_verbose = ['-v']
  else:
    logging.basicConfig(level = logging.ERROR)
    xmake_verbose = []

  logging.info("testing GCC %s", config.arch)

  ver = ARCHES[config.arch]
  paths = ProjectPaths(config, ver)

  clean(config, paths)

  prepare_dirs(paths)

  prepare_test_binary(ver, paths)

  test_report: Dict[str, Any] = {
    'fail': False,
  }

  os.environ['XMAKE_ROOT'] = 'y'

  try:
    test_linux_compiler(ver, paths, xmake_verbose)
    test_report['linux-compiler'] = "okay"
  except Exception as e:
    test_report['fail'] = True
    test_report['linux-compiler'] = repr(e)

  print("============================== TEST REPORT ==============================")
  pprint(test_report)

  if test_report['fail']:
    sys.exit(1)

if __name__ == '__main__':
  main()
