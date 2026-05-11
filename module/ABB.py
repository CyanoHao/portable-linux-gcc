import argparse
import os
from packaging.version import Version
from pathlib import Path
import shutil
import subprocess
from typing import List

from module.debug import shell_here
from module.path import ProjectPaths
from module.profile import ArchProfile
from module.util import common_cross_layers, ensure, fix_limits_h, overlayfs_ro, remove_info_main_menu
from module.util import cflags_B, configure, make_custom, make_default, make_destdir_install

def build_ABB_test_driver(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  ensure(paths.layer_ABB.test_driver)

  gcc_dir = paths.sat_gcc_dir.relative_to(paths.sat_dir)
  xmake_arch = ver.target.split('-')[0]
  debug_build_dir = f'build/linux/{xmake_arch}/debug'

  flags = [
    '-std=c11', '-O2', '-s',
    f'-DGCC_DIR="{gcc_dir}"',
    f'-DXMAKE_ARCH="{xmake_arch}"',
    f'-DDEBUG_BUILD_DIR="{debug_build_dir}"',
  ]

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    gcc_exe = f'{ver.target}-gcc'

    src_dir = paths.root_dir / 'support' / 'sat'
    pkg_dir = paths.layer_ABB.test_driver
    common_c = src_dir / 'common.c'

    subprocess.run([
      gcc_exe,
      *flags,
      src_dir / 'test-compiler.c', common_c,
      '-o', pkg_dir / 'test-compiler',
    ], check = True)

    subprocess.run([
      gcc_exe,
      *flags,
      src_dir / 'test-make-gdb.c', common_c,
      '-o', pkg_dir / 'test-make-gdb',
    ], check = True)

def _binutils(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.binutils / f'build-ABB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--host={ver.target}',
      f'--target={ver.target}',
      f'--build={config.build}',
      # workaround: bfd plugin 'dep' should be built as shared object
      '--enable-shared',
      '--enable-static',
      # features
      '--disable-gprofng',
      '--disable-install-libbfd',
      '--disable-multilib',
      '--disable-nls',
      # packages
      '--with-system-zlib',
      *cflags_B(),
      f'AR={ver.target}-gcc-ar',
      f'RANLIB={ver.target}-gcc-ranlib',
    ])
    make_default(build_dir, config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_ABB.binutils}',
      # use native layout
      'tooldir=',
      'install',
    ], jobs = 1)

  remove_info_main_menu(paths.layer_ABB.binutils)

  license_dir = paths.layer_ABB.binutils / 'share/licenses/binutils'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.binutils / file, license_dir / file)

def _linux_headers(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.linux)
  KARCH_MAP = {
    'aarch64': 'arm64',
    'i686': 'x86',
    'loong64': 'loongarch',
    'riscv64': 'riscv',
    'x86_64': 'x86',
  }

  make_custom(paths.src_dir.linux, [
    'headers_install',
    f'ARCH={KARCH_MAP[ver.arch]}',
    f'INSTALL_HDR_PATH={paths.layer_ABB.linux}',
  ], config.jobs)

  license_dir = paths.layer_ABB.linux / 'share/licenses/linux'
  ensure(license_dir)
  shutil.copy(paths.src_dir.linux / 'COPYING', license_dir / 'COPYING')
  if v >= Version('4.17'):
    shutil.copy(paths.src_dir.linux / 'LICENSES/preferred/GPL-2.0', license_dir / 'GPL-2.0')
    shutil.copy(paths.src_dir.linux / 'LICENSES/exceptions/Linux-syscall-note', license_dir / 'Linux-syscall-note')

def _glibc(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.glibc_target)
  build_dir = paths.src_dir.glibc_target / f'build-ABB'
  ensure(build_dir)

  destdir = paths.layer_ABB.glibc

  with overlayfs_ro('/usr/local', [
    # glibc prior to 2.31 can not be built with make 4.4 (infinite recursion)
    # upstream accidentally fixed it, cherry-pick seems very hard
    # ref. https://github.com/crosstool-ng/crosstool-ng/issues/1932#issuecomment-1528139734
    paths.layer_AAA.make / 'usr/local',

    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--host={ver.target}',
      f'--build={config.build}',
      # static-only is not supported
      # here we build with dynamic library enabled ...
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
    make_destdir_install(build_dir, destdir)

  # ... and then move away the dynamic library,
  # for gcc target library link test...
  shared_lib_dir = paths.layer_ABB.glibc_shared / 'lib'
  ensure(shared_lib_dir)
  for file in destdir.glob('lib/*.so*'):
    shutil.move(file, shared_lib_dir / file.name)

  # ... and remove other stuff.
  remove_dirs = ['bin', 'etc', 'lib/audit', 'lib/gconv', 'libexec', 'sbin', 'share', 'var']
  for dir in remove_dirs:
    if (destdir / dir).exists():
      shutil.rmtree(destdir / dir)

  fake_libs = [
    destdir / 'lib/libm.a',
    paths.layer_ABB.glibc_shared / 'lib/libc.so',
    paths.layer_ABB.glibc_shared / 'lib/libm.so',
    paths.layer_ABB.glibc_shared / 'lib/libpthread.so',
  ]
  for fake_lib in fake_libs:
    try:
      linker_script = open(fake_lib, 'r').read()
      with open(fake_lib, 'w') as f:
        f.write(linker_script.replace('/lib/', './'))
    except UnicodeDecodeError:
      pass
    except FileNotFoundError:
      pass

  license_dir = paths.layer_ABB.glibc / 'share/licenses/glibc'
  ensure(license_dir)
  if v >= Version('2.43'):
    license_files = ['COPYING.LESSERv2', 'COPYINGv2', 'COPYINGv3', 'LICENSES']
  else:
    license_files = ['COPYING', 'COPYING.LIB', 'LICENSES']
  for file in license_files:
    shutil.copy(paths.src_dir.glibc_target / file, license_dir / file)

def _gcc_1(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gcc)
  build_dir = paths.src_dir.gcc / f'build-ABB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.mpc / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',
    paths.layer_AAB.zlib / 'usr/local',
  ]):
    config_flags: List[str] = []

    if ver.fpmath:
      config_flags.append(f'--with-fpmath={ver.fpmath}')
    if ver.march:
      config_flags.append(f'--with-arch={ver.march}')

    configure(build_dir, [
      '--prefix=',
      f'--libexecdir=/lib',
      f'--host={ver.target}',
      f'--target={ver.target}',
      f'--build={config.build}',
      # static build
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-bootstrap',
      '--enable-checking=release',
      '--enable-default-pie',
      '--enable-default-ssp',
      '--enable-host-pie',
      '--enable-languages=c,c++',
      '--disable-libmpx',
      '--disable-libstdcxx-pch',
      '--disable-libsanitizer',  # not work with static toolchain
      '--disable-libssp',
      '--disable-multilib',
      '--disable-nls',
      # packages
      '--with-gcc-major-version-only',
      '--without-libcc1',
      '--with-system-zlib',
      *config_flags,
      *cflags_B(),
      *cflags_B('_FOR_TARGET'),
    ])
    make_custom(build_dir, ['all-host'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_ABB.gcc}',
      'install-host',
    ], jobs = 1)

  limits_h = paths.layer_ABB.gcc / f'lib/gcc/{ver.target}/{v.major}/include/limits.h'
  fix_limits_h(limits_h, paths.src_dir.gcc)

  remove_info_main_menu(paths.layer_ABB.gcc)

  license_dir = paths.layer_ABB.gcc / 'share/licenses/gcc'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.RUNTIME', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gcc / file, license_dir / file)

def _gcc_2(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  build_dir = paths.src_dir.gcc / f'build-ABB'

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_target / 'usr/local',
    *common_cross_layers(paths),
  ]), overlayfs_ro(f'/{ver.target}/include', [
    # the build system expects target headers at `/$triplet/include`.
    # it's generally okay if that directory does not exists,
    # because cross toolchain is complete and provides all headers.

    # but when building libstdc++ std module,
    # gcc's <fenv.h> wrapper #include_next <fenv.h>,
    # and the compiler founds cross gcc's <fenv.h> wrapper,
    # and that file is omitted because of same include guard,
    # and thus the real <fenv.h> will never be included.
    f'/usr/local/{ver.target}/include',
  ]):
    make_custom(build_dir, ['all-target'], config.jobs)
    make_custom(build_dir, [
      f'DESTDIR={paths.layer_ABB.gcc_lib}',
      'install-target',
    ], jobs = 1)

def _gdb(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.gdb)
  v_gcc = Version(ver.gcc)
  v_python = Version(ver.python)
  build_dir = paths.src_dir.gdb / f'build-ABB'
  ensure(build_dir)

  with overlayfs_ro('/usr/local', [
    paths.layer_AAA.python / 'usr/local',

    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),

    paths.layer_AAB.expat / 'usr/local',
    paths.layer_AAB.gmp / 'usr/local',
    paths.layer_AAB.mpc / 'usr/local',
    paths.layer_AAB.mpdecimal / 'usr/local',
    paths.layer_AAB.mpfr / 'usr/local',
    paths.layer_AAB.python / 'usr/local',
    paths.layer_AAB.zlib / 'usr/local',
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--host={ver.target}',
      f'--target={ver.target}',
      f'--build={config.build}',
      # prefer static
      '--disable-inprocess-agent',
      '--disable-shared',
      '--enable-static',
      # features
      '--disable-install-libbfd',
      '--disable-nls',
      '--disable-sim',
      '--disable-tui',
      # packages
      '--with-gdbserver',
      f'--with-python=/usr/local/{ver.target}/bin/gdb-python.sh',
      '--with-system-gdbinit=/share/gdb/gdbinit',
      *cflags_B(
        c_extra = ['-std=gnu11'],
        ld_extra = ['-lrt'],
      ),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_ABB.gdb)

    gdbinit = paths.layer_ABB.gdb / 'share/gdb/gdbinit'
    ensure(paths.layer_ABB.gdb / 'lib')
    with open(gdbinit, 'w') as f:
      f.write('python\n')
      f.write('from libstdcxx.v6.printers import register_libstdcxx_printers\n')
      f.write('register_libstdcxx_printers(None)\n')
      f.write('end\n')

    # python standard library
    python_abi_ver = f'{v_python.major}.{v_python.minor}'
    shutil.copytree(
      f'/usr/local/{ver.target}/lib/python{python_abi_ver}',
      paths.layer_ABB.gdb / f'lib/python{python_abi_ver}',
      dirs_exist_ok = True,
      ignore = shutil.ignore_patterns(
        '__pycache__',
        '*.py',
      ),
    )

    # libstdc++ pretty printer
    gcc_python_dir = f'/usr/local/share/gcc-{v_gcc.major}/python'
    gdb_python_dir = paths.layer_ABB.gdb / 'share/gdb/python'
    build_python = f'/usr/local/bin/python{python_abi_ver}'
    shutil.copytree(gcc_python_dir, gdb_python_dir, dirs_exist_ok = True)
    subprocess.run([
      build_python, '-m', 'compileall',
      '-o', '0',
      '-o', '1',
      '-o', '2',
      '.',
    ], check = True, cwd = gdb_python_dir)

  remove_info_main_menu(paths.layer_ABB.gdb)

  binutils_collision_files = ['bfd.info', 'ctf-spec.info', 'sframe-spec.info']
  for info_file in binutils_collision_files:
    os.unlink(paths.layer_ABB.gdb / 'share/info' / info_file)

  license_dir = paths.layer_ABB.gdb / 'share/licenses/gdb'
  ensure(license_dir)
  for file in ['COPYING', 'COPYING3', 'COPYING.LIB', 'COPYING3.LIB']:
    shutil.copy(paths.src_dir.gdb / file, license_dir / file)

def _gmake(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v = Version(ver.make_target)
  v_gcc = Version(ver.gcc)
  build_dir = paths.src_dir.make_target / 'build-ABB'
  ensure(build_dir)

  c_extra: List[str] = []

  # GCC 15 defaults to C23, in which `foo()` means `foo(void)` instead of `foo(...)`.
  if v_gcc.major >= 15 and v < Version('4.5'):
    c_extra.append('-std=gnu11')

  with overlayfs_ro('/usr/local', [
    paths.layer_AAB.glibc_host / 'usr/local',
    *common_cross_layers(paths),
  ]):
    configure(build_dir, [
      '--prefix=',
      f'--host={ver.target}',
      f'--build={config.build}',
      '--disable-nls',
      *cflags_B(c_extra = c_extra),
    ])
    make_default(build_dir, config.jobs)
    make_destdir_install(build_dir, paths.layer_ABB.make)

  remove_info_main_menu(paths.layer_ABB.make)

  license_dir = paths.layer_ABB.make / 'share/licenses/make'
  ensure(license_dir)
  shutil.copy(paths.src_dir.make_target / 'COPYING', license_dir / 'COPYING')

def build_ABB_toolchain(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _binutils(ver, paths, config)
  _linux_headers(ver, paths, config)
  _glibc(ver, paths, config)
  _gcc_1(ver, paths, config)
  _gcc_2(ver, paths, config)
  _gdb(ver, paths, config)
  _gmake(ver, paths, config)

def _xmake(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  v_glibc = Version(ver.glibc_host)
  # glibc is too old to build xmake
  # accurate version unknown
  use_target_libc = v_glibc < Version('2.11')
  glibc_layer = paths.layer_AAB.glibc_target if use_target_libc else paths.layer_AAB.glibc_host

  with overlayfs_ro('/usr/local', [
    glibc_layer / 'usr/local',
    *common_cross_layers(paths),
  ]):
    subprocess.run([
      './configure',
      '--prefix=',
    ], cwd = paths.src_dir.xmake, check = True, env = {
      **os.environ,
      'AR': f'{ver.target}-ar',
      'AS': f'{ver.target}-gcc',
      'CC': f'{ver.target}-gcc',
      'LD': f'{ver.target}-g++',
      # if host glibc is too old, the target glibc is also
      # too old to `-static-pie` link (requires 2.27 or later)
      'LDFLAGS': '-static -lrt' if use_target_libc else '-lrt',
    })
    make_default(paths.src_dir.xmake, config.jobs)
    make_destdir_install(paths.src_dir.xmake, paths.layer_ABB.xmake)

  license_dir = paths.layer_ABB.xmake / 'share/licenses/xmake'
  ensure(license_dir)
  shutil.copy(paths.src_dir.xmake / 'LICENSE.md', license_dir / 'LICENSE.md')

def build_ABB_xmake(ver: ArchProfile, paths: ProjectPaths, config: argparse.Namespace):
  _xmake(ver, paths, config)
