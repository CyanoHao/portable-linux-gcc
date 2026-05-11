import argparse
from packaging.version import Version
from pathlib import Path
from typing import Callable, NamedTuple, Optional

from module.profile import ArchProfile

class SourcePaths(NamedTuple):
  binutils: Path
  expat: Path
  gcc: Path
  gdb: Path
  glibc_host: Path
  glibc_target: Path
  gmp: Path
  linux: Path
  make_host: Path
  make_target: Path
  mpc: Path
  mpdecimal: Path
  mpfr: Path
  python: Path
  xmake: Path
  zlib_net: Path

class LayerPathsAAA(NamedTuple):
  prefix: Path

  gmp: Path
  mpc: Path
  mpfr: Path
  zlib: Path

  make: Path
  python: Path

class LayerPathsAAB(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  gcc_newlib: Path
  glibc_host: Path
  glibc_target: Path
  linux: Path

  expat: Path
  gmp: Path
  mpc: Path
  mpdecimal: Path
  mpfr: Path
  python: Path
  zlib: Path

class LayerPathsABB(NamedTuple):
  prefix: Path

  binutils: Path
  gcc: Path
  gcc_lib: Path
  gdb: Path
  glibc: Path
  glibc_shared: Path
  linux: Path
  make: Path
  test_driver: Path

  xmake: Path

class ProjectPaths:
  root_dir: Path
  abi_name: str

  assets_dir: Path
  dist_dir: Path
  patch_dir: Path

  linux_pkg: Path
  cross_pkg: Path
  test_driver_pkg: Path
  xmake_pkg: Path

  # build phase

  build_dir: Path
  target_dir: Path
  layer_dir: Path
  pkg_dir: Path

  src_dir: SourcePaths
  src_arx: SourcePaths

  layer_AAA: LayerPathsAAA
  layer_AAB: LayerPathsAAB
  layer_ABB: LayerPathsABB

  # test phase

  test_dir: Path
  test_src_dir: Path

  test_linux_dir: Path

  # target test archive phase

  sat_dir: Path
  sat_gcc_dir: Path

  def __init__(
    self,
    config: argparse.Namespace,
    ver: ArchProfile,
  ):
    self.root_dir = Path.cwd()
    abi_name = f'gcc-{config.arch}'
    self.abi_name = abi_name

    self.assets_dir = self.root_dir / 'assets'
    self.dist_dir = self.root_dir / 'dist'
    self.patch_dir = self.root_dir / 'patch'

    self.linux_pkg = self.dist_dir / f'{abi_name}-r{ver.rev}.tar.zst'
    self.cross_pkg = self.dist_dir / f'x-{abi_name}-r{ver.rev}.tar.zst'
    self.test_driver_pkg = self.dist_dir / f'test-{abi_name}-r{ver.rev}.tar.zst'
    self.xmake_pkg = self.dist_dir / f'xmake-{abi_name}-r{ver.rev}.tar.zst'

    # build phase

    self.build_dir = Path(f'/tmp/build/{abi_name}')
    self.target_dir = Path(f'/tmp/target/{abi_name}')
    self.layer_dir = Path(f'/tmp/layer/{abi_name}')
    self.pkg_dir = Path(f'/tmp/pkg/{abi_name}')

    src_name = SourcePaths(
      binutils = Path(f'binutils-{ver.binutils}'),
      expat = Path(f'expat-{ver.expat}'),
      gcc = Path(f'gcc-{ver.gcc}'),
      gdb = Path(f'gdb-{ver.gdb}'),
      glibc_host = Path(f'glibc-{ver.glibc_host}'),
      glibc_target = Path(f'glibc-{ver.glibc_target}'),
      gmp = Path(f'gmp-{ver.gmp}'),
      linux = Path(f'linux-{ver.linux}'),
      make_host = Path(f'make-{ver.make_host}'),
      make_target = Path(f'make-{ver.make_target}'),
      mpc = Path(f'mpc-{ver.mpc}'),
      mpdecimal = Path(f'mpdecimal-{ver.mpdecimal}'),
      mpfr = Path(f'mpfr-{ver.mpfr}'),
      python = Path(f'Python-{ver.python}'),
      xmake = Path(f'xmake-{ver.xmake}'),
      zlib_net = Path(f'zlib-{ver.zlib_net}'),
    )

    self.src_dir = SourcePaths(
      binutils = self.build_dir / src_name.binutils,
      expat = self.build_dir / src_name.expat,
      gcc = self.build_dir / src_name.gcc,
      gdb = self.build_dir / src_name.gdb,
      glibc_host = self.build_dir / src_name.glibc_host,
      glibc_target = self.build_dir / src_name.glibc_target,
      gmp = self.build_dir / src_name.gmp,
      linux = self.build_dir / src_name.linux,
      make_host = self.build_dir / src_name.make_host,
      make_target = self.build_dir / src_name.make_target,
      mpc = self.build_dir / src_name.mpc,
      mpdecimal = self.build_dir / src_name.mpdecimal,
      mpfr = self.build_dir / src_name.mpfr,
      python = self.build_dir / src_name.python,
      xmake = self.build_dir / src_name.xmake,
      zlib_net = self.build_dir / src_name.zlib_net,
    )

    self.src_arx = SourcePaths(
      binutils = self.assets_dir / f'{src_name.binutils}.tar.zst',
      expat = self.assets_dir / f'{src_name.expat}.tar.xz',
      gcc = self.assets_dir / f'{src_name.gcc}.tar.xz',
      gdb = self.assets_dir / f'{src_name.gdb}.tar.xz',
      glibc_host = self.assets_dir / f'{src_name.glibc_host}.tar.xz'
        if Version(ver.glibc_host) >= Version('2.11')
        else self.assets_dir / f'{src_name.glibc_host}.tar.bz2',
      glibc_target = self.assets_dir / f'{src_name.glibc_target}.tar.xz',
      gmp = self.assets_dir / f'{src_name.gmp}.tar.zst',
      linux = self.assets_dir / f'{src_name.linux}.tar.xz',
      make_host = self.assets_dir / f'{src_name.make_host}.tar.bz2',
      make_target = self.assets_dir / f'{src_name.make_target}.tar.lz',
      mpc = self.assets_dir / f'{src_name.mpc}.tar.xz',
      mpdecimal = self.assets_dir / f'{src_name.mpdecimal}.tar.gz',
      mpfr = self.assets_dir / f'{src_name.mpfr}.tar.xz',
      python = self.assets_dir / f'{src_name.python}.tar.xz',
      xmake = self.assets_dir / f'{src_name.xmake}.tar.gz',
      zlib_net = self.assets_dir / f'{src_name.zlib_net}.tar.xz',
    )

    layer_AAA_prefix = self.layer_dir / 'AAA'
    self.layer_AAA = LayerPathsAAA(
      prefix = layer_AAA_prefix,

      gmp = layer_AAA_prefix / 'gmp',
      mpc = layer_AAA_prefix / 'mpc',
      mpfr = layer_AAA_prefix / 'mpfr',
      zlib = layer_AAA_prefix / 'zlib',

      make = layer_AAA_prefix / 'make',
      python = layer_AAA_prefix / 'python',
    )

    layer_AAB_prefix = self.layer_dir / 'AAB'
    self.layer_AAB = LayerPathsAAB(
      prefix = layer_AAB_prefix,

      binutils = layer_AAB_prefix / 'binutils',
      gcc = layer_AAB_prefix / 'gcc',
      gcc_newlib = layer_AAB_prefix / 'gcc-newlib',
      glibc_host = layer_AAB_prefix / 'glibc-host',
      glibc_target = layer_AAB_prefix / 'glibc-target',
      linux = layer_AAB_prefix / 'linux',

      expat = layer_AAB_prefix / 'expat',
      gmp = layer_AAB_prefix / 'gmp',
      mpc = layer_AAB_prefix / 'mpc',
      mpdecimal = layer_AAB_prefix / 'mpdecimal',
      mpfr = layer_AAB_prefix / 'mpfr',
      python = layer_AAB_prefix / 'python',
      zlib = layer_AAB_prefix / 'zlib',
    )

    layer_ABB_prefix = self.layer_dir / 'ABB'
    self.layer_ABB = LayerPathsABB(
      prefix = layer_ABB_prefix,

      binutils = layer_ABB_prefix / 'binutils',
      gcc = layer_ABB_prefix / 'gcc',
      gcc_lib = layer_ABB_prefix / 'gcc-lib',
      gdb = layer_ABB_prefix / 'gdb',
      glibc = layer_ABB_prefix / 'glibc',
      glibc_shared = layer_ABB_prefix / 'glibc-shared',
      linux = layer_ABB_prefix / 'linux',
      make = layer_ABB_prefix / 'make',
      test_driver = layer_ABB_prefix / 'test-driver',

      xmake = layer_ABB_prefix / 'xmake',
    )

    # test phase

    self.test_dir = Path(f'/tmp/test/{abi_name}')
    self.test_src_dir = self.root_dir / 'support' / 'test'

    self.test_linux_dir = self.test_dir / abi_name

    # target semi-automated testing archive phase

    self.sat_dir = self.root_dir / 'pkg' / f'sat-{config.arch}'
    self.sat_gcc_dir = self.sat_dir / abi_name
