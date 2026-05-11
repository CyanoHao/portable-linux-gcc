import argparse
import os
from packaging.version import Version
import shutil
import subprocess
from typing import List

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import ArchProfile
from module.util import add_objects_to_static_lib, common_cross_layers, ensure, fix_limits_h, overlayfs_ro
from module.util import cflags_A, cflags_B, configure, make_custom, make_default, make_destdir_install

def _binutils(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.binutils / f'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=/usr/local',
      f'--target={ver.target}',
      f'--build={config.build}',
      # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-gprofng',
      '--disable-install-libbfd',
      '--disable-multilib',
      '--disable-nls',
      '--disable-werror',
      # packages
      '--with-system-zlib',
      *cflags_A(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.binutils)

def _linux_headers(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  KARCH_MAP = {
    'aarch64': 'arm64',
    'i686': 'x86',
    'loong64': 'loongarch',
    'riscv64': 'riscv',
    'x86_64': 'x86',
  }

  prefix = paths.layer_AAB.linux / f'usr/local/{ver.target}'

  make_custom(paths.src_dir.linux, [
    'headers_install',
    f'ARCH={KARCH_MAP[ver.arch]}',
    f'INSTALL_HDR_PATH={prefix}',
  ], config.jobs)

def _gcc_newlib(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  v_glibc = Version(ver.glibc_host)
  build_dir = paths.src_dir.gcc / f'build-bootstrap'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpc / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',
    paths.layer_AAA.zlib / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.linux / 'usr/local',
  ]):
    config_flags: List[str] = []

    if ver.fpmath:
      config_flags.append(f'--with-fpmath={ver.fpmath}')
    if ver.march:
      config_flags.append(f'--with-arch={ver.march}')

    configure(build_dir, [
      '--prefix=/usr/local',
      '--libexecdir=/usr/local/lib',
      f'--target={ver.target}',
      f'--build={config.build}',
      # static only - there's no libc yet
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-host-pie',
      '--enable-languages=c',
      '--disable-libatomic',
      '--disable-libgomp',
      '--disable-libmpx',
      '--disable-libquadmath',
      '--disable-libsanitizer',
      '--disable-libstdcxx-pch',
      '--disable-libssp',
      '--disable-lto',
      '--disable-multilib',
      '--disable-nls',
      '--disable-threads',
      # packages
      '--with-gcc-major-version-only',
      f'--with-glibc-version={v_glibc.major}.{v_glibc.minor}',
      '--without-libcc1',
      '--with-newlib',
      '--with-system-zlib',
      *config_flags,
      *cflags_A(),
      *cflags_B('_FOR_TARGET',
        c_extra = ['-fPIC']
      ),
    ])

    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.gcc_newlib)

  libgcc_eh = paths.layer_AAB.gcc_newlib / f'usr/local/lib/gcc/{ver.target}/{v.major}/libgcc_eh.a'
  if libgcc_eh.is_symlink():
    libgcc_eh.unlink()
  os.symlink('libgcc.a', libgcc_eh)

def _glibc_host(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc_host)
  build_dir = paths.src_dir.glibc_host / f'build-AAB'
  ensure(build_dir)

  build_triplet: str = config.build
  config_flags: List[str] = []
  c_extra: List[str] = []

  # workaround target compiler detection
  if v < Version('2.23'):
    config_flags.append('libc_cv_forced_unwind=yes')
  if v < Version('2.16'):
    config_flags.extend(['libc_cv_c_cleanup=yes'])

  # old glibc does not recognize `x86_64-alpine-linux-musl`
  if v < Version('2.17'):
    build_triplet = build_triplet.replace('-musl', '-uclibc')

  if v < Version('2.6'):
    c_extra.append('-fgnu89-inline')

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_AAA.make / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.gcc_newlib / 'usr/local',
    paths.layer_AAB.linux / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={build_triplet}',
      # host use shared glibc
      '--enable-shared',
      '--disable-static',
      # features
      '--enable-add-ons=yes',
      '--disable-build-nscd',
      '--disable-fortify-source',
      f'--enable-kernel={ver.enable_kernel}',
      '--disable-multi-arch',
      '--disable-nscd',
      '--disable-timezone-tools',
      '--disable-werror',
      *config_flags,
      *cflags_B(c_extra = c_extra),
      # disable C++ to avoid -lgcc_s in test links-dso-program
      # which is not supported by static compiler
      'CXX=false',
    ])

    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.glibc_host)

  # workaround GCC checking for inhibit_libc
  prefix = paths.layer_AAB.glibc_host / f'usr/local/{ver.target}'
  ensure(prefix / 'sys-include')
  shutil.copy(prefix / 'include/stdio.h', prefix / 'sys-include/stdio.h')

  # SSP support symbols are introduced in glibc 2.4
  # build gcc libssp and add required objects to libc_nonshared.a
  if v < Version('2.4'):
    ssp_build_dir = paths.src_dir.gcc / 'libssp/build-AAB'
    ensure(ssp_build_dir)

    with overlayfs_ro('/usr/local', [
      paths.layer_AAB.binutils / 'usr/local',
      paths.layer_AAB.gcc_newlib / 'usr/local',
      paths.layer_AAB.glibc_host / 'usr/local',
      paths.layer_AAB.linux / 'usr/local',
    ]):
      configure(ssp_build_dir, [
        '--prefix=',
        f'--target={ver.target}',
        f'--host={ver.target}',
        f'--build={config.build}',
        '--enable-shared',
        '--enable-static',
        '--disable-multilib',
        *cflags_B(common_extra = ['-fPIC']),
      ])
      make_default(ssp_build_dir, config.jobs)

      add_objects_to_static_lib(
        f'{ver.target}-ar',
        paths.layer_AAB.glibc_host / f'usr/local/{ver.target}/lib/libc_nonshared.a',
        (
          f
          for f in ssp_build_dir.glob('*.o')
          if not f.name.startswith('libssp_nonshared_la-')
        ),
      )

def _gcc(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  v_glibc = Version(ver.glibc_host)
  build_dir = paths.src_dir.gcc / f'build-AAB'
  ensure(build_dir)

  limits_h = paths.layer_AAB.gcc / f'usr/local/lib/gcc/{ver.target}/{v.major}/include/limits.h'

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.gmp / 'usr/local',
    paths.layer_AAA.mpc / 'usr/local',
    paths.layer_AAA.mpfr / 'usr/local',
    paths.layer_AAA.zlib / 'usr/local',

    paths.layer_AAB.binutils / 'usr/local',
    paths.layer_AAB.glibc_host / 'usr/local',
    paths.layer_AAB.linux / 'usr/local',
  ]):
    config_flags: List[str] = []

    if ver.fpmath:
      config_flags.append(f'--with-fpmath={ver.fpmath}')
    if ver.march:
      config_flags.append(f'--with-arch={ver.march}')

    configure(build_dir, [
      '--prefix=/usr/local',
      '--libexecdir=/usr/local/lib',
      f'--target={ver.target}',
      f'--build={config.build}',
      # prefer static
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-default-pie',
      '--enable-default-ssp',
      '--enable-host-pie',
      '--enable-languages=c,c++',
      '--disable-libatomic',
      '--disable-libgomp',
      '--disable-libmpx',
      '--disable-libsanitizer',
      '--disable-libstdcxx-pch',
      '--disable-libssp',
      '--disable-multilib',
      '--disable-nls',
      # packages
      '--with-gcc-major-version-only',
      f'--with-glibc-version={v_glibc.major}.{v_glibc.minor}',
      '--without-libcc1',
      '--with-system-zlib',
      *config_flags,
      *cflags_A(),
      *cflags_B('_FOR_TARGET'),
    ])

    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.gcc)
    fix_limits_h(limits_h, paths.src_dir.gcc)

def _glibc_target(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc_target)
  build_dir = paths.src_dir.glibc_target / f'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_AAA.make / 'usr/local',

    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      # static-only is not supported
      '--enable-shared',
      '--enable-static',
      '--enable-static-nss',
      # features
      '--enable-add-ons=yes',
      '--disable-build-nscd',
      '--disable-fortify-source',
      f'--enable-kernel={ver.enable_kernel}',
      '--disable-multi-arch',
      '--disable-nscd',
      '--enable-stack-protector=strong',
      '--disable-timezone-tools',
      '--disable-werror',
      *cflags_B(),
      # disable C++ to avoid -lgcc_s in test links-dso-program
      # which is not supported by static compiler
      'CXX=false',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.glibc_target)

def build_AAB_compiler(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(ver, paths, config)
  _linux_headers(ver, paths, config)
  _gcc_newlib(ver, paths, config)
  _glibc_host(ver, paths, config)
  _gcc(ver, paths, config)
  _glibc_target(ver, paths, config)

def _expat(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    build_dir = paths.src_dir.expat / 'build-AAB'
    ensure(build_dir)
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.expat)

def _gmp(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gmp / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--disable-assembly',
      '--enable-static',
      '--disable-shared',
      *cflags_B(c_extra = ['-std=gnu11']),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.gmp)

def _mpdecimal(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpdecimal / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.mpdecimal)

def _mpfr(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpfr / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.gmp / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.mpfr)

def _mpc(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.mpc / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--enable-static',
      '--disable-shared',
      *cflags_B(),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.mpc)

def _zlib_net(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.zlib_net / 'build-AAB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      '--static',
    ])
    make_custom(build_dir, [
      f'CC={ver.target}-gcc',
      'all',
    ], config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.zlib)

def _python(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.python)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.python / 'usr/local',

    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.expat / 'usr/local',
    paths.layer_AAB.mpdecimal / 'usr/local',
    paths.layer_AAB.zlib / 'usr/local',
  ]):
    build_dir = paths.src_dir.python / 'build-AAB'
    ensure(build_dir)

    abi_ver = f'{v.major}.{v.minor}'
    build_python = f'/usr/local/bin/python{abi_ver}'

    configure(build_dir, [
      f'--prefix=/usr/local/{ver.target}',
      f'--host={ver.target}',
      f'--build={config.build}',
      # static
      '--disable-shared',
      'MODULE_BUILDTYPE=static',
      # features
      '--disable-test-modules',
      '--enable-ipv6',  # override getaddrinfo bug detection (fixed in glibc 2.1.2)
      # packages
      f'--with-build-python={build_python}',
      '--without-ensurepip',
      '--with-system-expat',
      '--with-system-libmpdec',
      *cflags_A(),
      'ac_cv_file__dev_ptc=no',
      'ac_cv_file__dev_ptmx=yes',
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_AAB.python)

    shutil.copy(paths.root_dir / 'support/gdb/gdb-python.sh', paths.layer_AAB.python / f'usr/local/{ver.target}/bin/gdb-python.sh')

    dest_lib_dir = paths.layer_AAB.python / f'usr/local/{ver.target}/lib'
    python_lib_dir = dest_lib_dir / f'python{abi_ver}'

    libpython_a = dest_lib_dir / f'libpython{abi_ver}.a'
    hacl_sha2_obj = build_dir / 'Modules/_hacl/Hacl_Hash_SHA2.o'
    add_objects_to_static_lib(f'{ver.target}-ar', libpython_a, [hacl_sha2_obj])

    py_target = 'i386-linux-gnu' if ver.arch == 'i686' else ver.target
    config_dir = python_lib_dir / f'config-{abi_ver}-{py_target}'
    shutil.rmtree(config_dir)

    subprocess.run([
      build_python, '-m', 'compileall',
      '-b',
      '-o', '2',
      '.',
    ], check = True, cwd = python_lib_dir)

def build_AAB_library(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _expat(ver, paths, config)
  _gmp(ver, paths, config)
  _mpdecimal(ver, paths, config)
  _mpfr(ver, paths, config)
  _mpc(ver, paths, config)
  _zlib_net(ver, paths, config)
  _python(ver, paths, config)
