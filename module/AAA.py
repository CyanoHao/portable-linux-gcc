import argparse
import os
import shutil
from packaging.version import Version
import subprocess

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import ArchProfile
from module.util import overlayfs_ro
from module.util import cflags_A, configure, ensure, make_default, make_destdir_install

def _gmp(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gmp / 'build-AAA'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    f'--host={config.build}',
    f'--build={config.build}',
    '--disable-assembly',
    '--enable-static',
    '--disable-shared',
    *cflags_A(),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.gmp)

def _mpfr(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpfr / 'build-AAA'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.mpfr)

def _mpc(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',
  ]):
    build_dir = paths.src_dir.mpc / 'build-AAA'
    ensure(build_dir)
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--host={config.build}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.mpc)

def _zlib_net(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.zlib_net / 'build-AAA'
  ensure(build_dir)
  configure(build_dir, [
    '--prefix=/usr/local',
    '--static',
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.zlib)

def build_AAA_library(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmp(ver, paths, config)
  _mpfr(ver, paths, config)
  _mpc(ver, paths, config)
  _zlib_net(ver, paths, config)

def _gmake(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.make_host / 'build-AAA'
  ensure(build_dir)

  configure(build_dir, [
    '--prefix=/usr/local',
    f'--build={config.build}',
    '--disable-nls',
    *cflags_A(),
  ])
  make_default(build_dir, config.jobs)
  make_destdir_install(build_dir, paths.layer_AAA.make)

  gmake = paths.layer_AAA.make / 'usr/local/bin/gmake'
  if gmake.is_symlink():
    gmake.unlink()
  os.symlink('make', gmake)

def _python(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.zlib / 'usr/local',
  ]):
    build_dir = paths.src_dir.python / 'build-AAA'
    ensure(build_dir)
    configure(build_dir, [
      f'--prefix=/usr/local',
      # static
      '--disable-shared',
      'MODULE_BUILDTYPE=static',
      # features
      '--disable-test-modules',
      # packages
      '--without-static-libpython',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAA.python)

def build_AAA_tool(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _gmake(ver, paths, config)
  _python(ver, paths, config)
