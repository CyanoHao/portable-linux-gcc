from packaging.version import Version
import subprocess

from module.fetch import validate_and_download, check_and_extract, patch, patch_done
from module.path import ProjectPaths
from module.profile import ArchProfile

def _binutils(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/binutils/{paths.src_arx.binutils.name}'
  validate_and_download(paths.src_arx.binutils, url)
  if download_only:
    return

  if check_and_extract(paths.src_dir.binutils, paths.src_arx.binutils):
    # Disable shared libbfd
    patch(paths.src_dir.binutils, paths.patch_dir / 'binutils/disable-shared-libbfd.patch')

    patch_done(paths.src_dir.binutils)

def _expat(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  v = Version(ver.expat)
  tag = f'R_{v.major}_{v.minor}_{v.micro}'
  url = f'https://github.com/libexpat/libexpat/releases/download/{tag}/{paths.src_arx.expat.name}'
  validate_and_download(paths.src_arx.expat, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.expat, paths.src_arx.expat)
  patch_done(paths.src_dir.expat)

def _gcc(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/gcc/gcc-{ver.gcc}/{paths.src_arx.gcc.name}'
  validate_and_download(paths.src_arx.gcc, url)
  if download_only:
    return

  if check_and_extract(paths.src_dir.gcc, paths.src_arx.gcc):
    v_glibc = Version(ver.glibc_target)

    # Default to static (PIE)
    if v_glibc >= Version('2.27'):
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc/default-to-static-pie.patch')
    else:
      patch(paths.src_dir.gcc, paths.patch_dir / 'gcc/default-to-static.patch')

    # Ignore system library
    patch(paths.src_dir.gcc, paths.patch_dir / 'gcc/ignore-system-library.patch')

    # Use system style tooldir
    # The system package manager insttall binutils with `tooldir=$prefix`.
    # However, GCC tries to locate the tools in $prefix/$triplet and then falls back to PATH.
    # It will fail without PATH, or even worse, calls unexpected tools from other toolchain.
    # We adjust the strategy to make it work without PATH.
    patch(paths.src_dir.gcc, paths.patch_dir / 'gcc/use-system-style-tooldir.patch')

    # x86_64 use `lib` instead of `lib64`
    filepath = paths.src_dir.gcc / 'gcc/config/i386/t-linux64'
    content = open(filepath).readlines()
    with open(filepath, 'w') as f:
      for line in content:
        if 'm64=' in line:
          f.write(line.replace('lib64', 'lib'))
        else:
          f.write(line)

    # aarch64 use `lib` instead of `lib64`
    filepath = paths.src_dir.gcc / 'gcc/config/aarch64/t-aarch64-linux'
    content = open(filepath).readlines()
    with open(filepath, 'w') as f:
      for line in content:
        if 'mabi.lp64=' in line:
          f.write(line.replace('lib64', 'lib'))
        else:
          f.write(line)

    patch_done(paths.src_dir.gcc)

def _gdb(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/gdb/{paths.src_arx.gdb.name}'
  validate_and_download(paths.src_arx.gdb, url)
  if download_only:
    return

  if check_and_extract(paths.src_dir.gdb, paths.src_arx.gdb):
    v_glibc = Version(ver.glibc_host)

    # Respect glibc's definition of `__inline``
    if v_glibc < Version('2.6'):
      patch(paths.src_dir.gdb, paths.patch_dir / 'gdb/respect-glibc-inline.patch')

    patch_done(paths.src_dir.gdb)

def _glibc_host(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/glibc/{paths.src_arx.glibc_host.name}'
  validate_and_download(paths.src_arx.glibc_host, url)
  if download_only:
    return

  if check_and_extract(paths.src_dir.glibc_host, paths.src_arx.glibc_host):
    v = Version(ver.glibc_host)

    # Fix RISC-V asm relocation
    if v >= Version('2.35'):
      pass
    elif v >= Version('2.29'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-riscv-asm-relocation_2.29.patch')
    elif v >= Version('2.27'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-riscv-asm-relocation_2.27.patch')

    # Fix AMD64 TLS mov i64 to m64
    # In libc-start, the stack guard is set from kernel's auxiliary vector AT_RANDOM
    # (introduced in 2.6.29), and if targeting kernel < 2.6.29, then tries /dev/urandom,
    # and finally falls back to a fixed value:
    #   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0a, 0xff
    # The 64-bit immediate causes an error in the assembler:
    #   movq 0xff0a000000000000, %fs:offset
    if v >= Version('2.34'):
      pass
    elif v >= Version('2.20'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.20.patch')
    elif v >= Version('2.17'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.17.patch')
    elif v >= Version('2.16'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.16.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.3.patch')

    # Fix RISC-V Linux header
    if Version('2.27') <= v < Version('2.29'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-riscv-linux-header.patch')

    # Fix NSS multiple definition
    if Version('2.27') <= v < Version('2.28'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-nss-multiple-definition.patch')

    # Fix AArch64 asm relocation
    if v >= Version('2.27'):
      pass
    elif v >= Version('2.26'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.26.patch')
    elif v >= Version('2.25'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.25.patch')
    elif v >= Version('2.21'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.21.patch')
    elif v >= Version('2.20'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.20.patch')
    elif v >= Version('2.18'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.18.patch')
    elif v >= Version('2.17'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-aarch64-asm-relocation_2.17.patch')

    # Disable sunrpc
    # glibc wrongly implements rpc host tools as glibc-only
    # since they finally removed it, we disable it for old versions
    if v >= Version('2.26'):
      pass
    elif v >= Version('2.25'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/disable-sunrpc_2.25.patch')
    elif v >= Version('2.16'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/disable-sunrpc_2.16.patch')

    # Fix SSP check
    if v >= Version('2.25'):
      pass
    elif v >= Version('2.19'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-ssp-check_2.19.patch')
    elif v >= Version('2.16'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-ssp-check_2.16.patch')

    # Fix compiler check
    if v >= Version('2.23'):
      pass
    elif v >= Version('2.19'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-compiler-check_2.19.patch')
    elif v >= Version('2.6'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-compiler-check_2.6.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-compiler-check_2.3.patch')

    # Fix version check
    if v >= Version('2.21'):
      pass
    elif v >= Version('2.19'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.19.patch')
    elif v >= Version('2.18'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.18.patch')
    elif v >= Version('2.16'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.16.patch')
    elif v >= Version('2.11'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.11.patch')
    elif v >= Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.4.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-version-check_2.3.patch')

    # Remove PIC consistency check
    if v < Version('2.21'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/remove-pic-consistency-check.patch')

    # Fix test
    if v < Version('2.17'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-test.patch')

    # Fix implicit declaration
    if Version('2.8') <= v < Version('2.16'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-implicit-declare.patch')

    # Fix asm identifier
    # old glibc uses `__i686` in asm code, which is later defined in GCC
    # upstream modifies it to `__x86` for GCC 4.7+ in 2.16
    if v < Version('2.16'):
      subprocess.run([
        'find', paths.src_dir.glibc_host,
        '-type', 'f',
        '(',
          '-name', '*setjmp.S', '-o',
          '-name', 'mem*.S', '-o',
          '-name', 'pthread_*.S', '-o',
          '-name', 'sem_*.S', '-o',
          '-name', 'str*.S', '-o',
          '-name', 'sysdep.h',
        ')',
        '-exec', 'sed', '-i', 's/__i686.get_pc_thunk/__x86.get_pc_thunk/g', '{}', ';',
      ])

    # Fix Makefile
    if v >= Version('2.15'):
      pass
    elif v >= Version('2.11'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-makefile_2.11.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-makefile_2.3.patch')

    # Backport constant
    if v >= Version('2.15'):
      pass
    elif v >= Version('2.12'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.12.patch')
    elif v >= Version('2.11'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.11.patch')
    elif v >= Version('2.10'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.10.patch')
    elif v >= Version('2.8'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.8.patch')
    elif v >= Version('2.7'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.7.patch')
    elif v >= Version('2.6'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.6.patch')
    elif v >= Version('2.5'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.5.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-constant_2.3.patch')

    # Fix .cfi instruction
    if v < Version('2.11.3'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-cfi-instruction.patch')

    # Backport endian
    if v >= Version('2.9'):
      pass
    elif v >= Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-endian_2.4.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-endian_2.3.patch')

    # Fix fnstsw operand type
    if v < Version('2.8'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-fnstsw-operand-type.patch')

    # Fix inline semantic
    if v >= Version('2.6'):
      pass
    elif v >= Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-inline-semantic_2.4.patch')
    else:
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-inline-semantic_2.3.patch')

    # Fix TLS multiple definition
    if v < Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-tls-multiple-definition.patch')

    # Backport libc.so auto link ld.so
    # fix undefined reference '__tls_get_addr@@GLIBC_2.3' (in ld.so)
    if v < Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/backport-libc-auto-link-ld.patch')

    # Fix memcmp misplaced end
    if v < Version('2.4'):
      patch(paths.src_dir.glibc_host, paths.patch_dir / 'glibc/fix-memcmp-misplaced-end.patch')

    patch_done(paths.src_dir.glibc_host)

def _glibc_target(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/glibc/{paths.src_arx.glibc_target.name}'
  validate_and_download(paths.src_arx.glibc_target, url)
  if download_only:
    return

  if check_and_extract(paths.src_dir.glibc_target, paths.src_arx.glibc_target):
    v = Version(ver.glibc_target)

    # Fix AMD64 TLS mov i64 to m64
    if v >= Version('2.34'):
      pass
    elif v >= Version('2.20'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.20.patch')
    else:
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-amd64-tls-mov-i64-to-m64_2.17.patch')

    # Fix RISC-V Linux header
    if Version('2.27') <= v < Version('2.29'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-riscv-linux-header.patch')

    # Fix NSS multiple definition
    if Version('2.27') <= v < Version('2.28'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-nss-multiple-definition.patch')

    # Disable sunrpc
    if v >= Version('2.26'):
      pass
    elif v >= Version('2.25'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/disable-sunrpc_2.25.patch')
    else:
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/disable-sunrpc_2.16.patch')

    # Fix SSP check
    if v >= Version('2.25'):
      pass
    elif v >= Version('2.19'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-ssp-check_2.19.patch')
    elif v >= Version('2.16'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-ssp-check_2.16.patch')

    # Fix compiler check
    if v < Version('2.23'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-compiler-check_2.19.patch')

    # Fix default PIE
    if v >= Version('2.22'):
      pass
    elif v >= Version('2.20'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-default-pie_2.20.patch')
    else:
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-default-pie_2.19.patch')

    # Fix version check
    if v < Version('2.21'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/fix-version-check_2.19.patch')

    # Remove PIC consistency check
    if v < Version('2.21'):
      patch(paths.src_dir.glibc_target, paths.patch_dir / 'glibc/remove-pic-consistency-check.patch')

    patch_done(paths.src_dir.glibc_target)

def _gmp(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/gmp/{paths.src_arx.gmp.name}'
  validate_and_download(paths.src_arx.gmp, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.gmp, paths.src_arx.gmp)
  patch_done(paths.src_dir.gmp)

def _linux(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  v = Version(ver.linux)
  url = f'https://cdn.kernel.org/pub/linux/kernel/v{v.major}.x/{paths.src_arx.linux.name}'
  validate_and_download(paths.src_arx.linux, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.linux, paths.src_arx.linux)
  patch_done(paths.src_dir.linux)

def _make_host(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/make/{paths.src_arx.make_host.name}'
  validate_and_download(paths.src_arx.make_host, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.make_host, paths.src_arx.make_host)
  patch_done(paths.src_dir.make_host)

def _make_target(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/make/{paths.src_arx.make_target.name}'
  validate_and_download(paths.src_arx.make_target, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.make_target, paths.src_arx.make_target)
  patch_done(paths.src_dir.make_target)

def _mpc(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/mpc/{paths.src_arx.mpc.name}'
  validate_and_download(paths.src_arx.mpc, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.mpc, paths.src_arx.mpc)
  patch_done(paths.src_dir.mpc)

def _mpdecimal(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://www.bytereef.org/software/mpdecimal/releases/{paths.src_arx.mpdecimal.name}'
  validate_and_download(paths.src_arx.mpdecimal, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.mpdecimal, paths.src_arx.mpdecimal)
  patch_done(paths.src_dir.mpdecimal)

def _mpfr(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://ftpmirror.gnu.org/gnu/mpfr/{paths.src_arx.mpfr.name}'
  validate_and_download(paths.src_arx.mpfr, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.mpfr, paths.src_arx.mpfr)
  patch_done(paths.src_dir.mpfr)

def _python(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://www.python.org/ftp/python/{ver.python}/{paths.src_arx.python.name}'
  validate_and_download(paths.src_arx.python, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.python, paths.src_arx.python)
  patch_done(paths.src_dir.python)

def _xmake(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  release_name = paths.src_arx.xmake.name.replace('xmake-', 'xmake-v')
  url = f'https://github.com/xmake-io/xmake/releases/download/v{ver.xmake}/{release_name}'
  validate_and_download(paths.src_arx.xmake, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.xmake, paths.src_arx.xmake)
  patch_done(paths.src_dir.xmake)

def _zlib_net(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  url = f'https://github.com/madler/zlib/releases/download/v{ver.zlib_net}/{paths.src_arx.zlib_net.name}'
  validate_and_download(paths.src_arx.zlib_net, url)
  if download_only:
    return

  check_and_extract(paths.src_dir.zlib_net, paths.src_arx.zlib_net)
  patch_done(paths.src_dir.zlib_net)

def prepare_source(ver: ArchProfile, paths: ProjectPaths, download_only: bool):
  _binutils(ver, paths, download_only)
  _expat(ver, paths, download_only)
  _gcc(ver, paths, download_only)
  _gdb(ver, paths, download_only)
  _glibc_host(ver, paths, download_only)
  _glibc_target(ver, paths, download_only)
  _gmp(ver, paths, download_only)
  _linux(ver, paths, download_only)
  _make_host(ver, paths, download_only)
  _make_target(ver, paths, download_only)
  _mpc(ver, paths, download_only)
  _mpdecimal(ver, paths, download_only)
  _mpfr(ver, paths, download_only)
  _python(ver, paths, download_only)
  _xmake(ver, paths, download_only)
  _zlib_net(ver, paths, download_only)
