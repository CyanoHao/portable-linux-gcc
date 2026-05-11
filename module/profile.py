from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ArchProfile:
  arch: str
  fpmath: Optional[str]
  march: Optional[str]
  target: str

  enable_kernel: str
  glibc_host: str
  glibc_target: str
  linux: str

  rev: str = '20260525'

  binutils: str = '2.46.0'
  expat: str = '2.7.5'
  gcc: str = '16.1.0'
  gdb: str = '17.1'
  gmp: str = '6.3.0'
  make_host: str = '4.2.1'
  make_target: str = '4.4.1'
  mpc: str = '1.4.1'
  mpdecimal: str = '4.0.1'
  mpfr: str = '4.2.2'
  # Python 3.14 depends on aligned_alloc (hacl blake2),
  # process_vm_readv (remote debug), etc.,
  # which are not available with very old glibc.
  python: str = '3.13.13'
  xmake: str = '3.0.8'
  zlib_net: str = '1.3.2'

ARCHES: Dict[str, ArchProfile] = {
  'x86_64': ArchProfile(
    arch = 'x86_64',
    fpmath = None,
    march = None,
    target = 'x86_64-linux-gnu',

    enable_kernel = '3.2',
    glibc_host = '2.13',  # Debian 7
    glibc_target = '2.43',
    linux = '6.18.29',
  ),
  'x86_64.v3': ArchProfile(
    arch = 'x86_64',
    fpmath = 'avx',
    march = 'x86-64-v3',
    target = 'x86_64-linux-gnu',

    enable_kernel = '3.2',
    glibc_host = '2.13',  # Debian 7
    glibc_target = '2.43',
    linux = '6.18.29',
  ),
  'aarch64': ArchProfile(
    arch = 'aarch64',
    fpmath = None,
    march = None,
    target = 'aarch64-linux-gnu',

    enable_kernel = '3.7',
    glibc_host = '2.17',
    glibc_target = '2.43',
    linux = '6.18.29',
  ),
  'riscv64': ArchProfile(
    arch = 'riscv64',
    fpmath = None,
    march = None,
    target = 'riscv64-linux-gnu',

    enable_kernel = '4.15',
    glibc_host = '2.27',
    glibc_target = '2.43',
    linux = '6.18.29',
  ),
  'loong64': ArchProfile(
    arch = 'loong64',
    fpmath = None,
    march = None,
    target = 'loongarch64-linux-gnu',

    enable_kernel = '5.19',
    glibc_host = '2.36',
    glibc_target = '2.43',
    linux = '6.18.29',
  ),

  'x86_64-2010': ArchProfile(
    arch = 'x86_64',
    fpmath = None,
    march = None,
    target = 'x86_64-linux-gnu',

    enable_kernel = '2.6.32',
    glibc_host = '2.11.3',  # Ubuntu 10.04
    glibc_target = '2.25',  # 2017-02-25, last release for Linux 2.6.32
    linux = '4.9.337',  # 2016-12-11
  ),
  'x86_64-2007': ArchProfile(
    arch = 'x86_64',
    fpmath = None,
    march = None,
    target = 'x86_64-linux-gnu',

    enable_kernel = '2.6.16',
    glibc_host = '2.3.6',  # Debian 4
    glibc_target = '2.19',  # 2014-02-07, last release for Linux 2.6.16
    linux = '3.12.74',  # 2013-11-03
  ),

  'i686': ArchProfile(
    arch = 'i686',
    fpmath = None,
    march = None,
    target = 'i686-linux-gnu',

    enable_kernel = '3.2',
    glibc_host = '2.13',  # Debian 7
    glibc_target = '2.43',
    linux = '6.18.29',
  ),
  'i686-2010': ArchProfile(
    arch = 'i686',
    fpmath = None,
    march = None,
    target = 'i686-linux-gnu',

    enable_kernel = '2.6.32',
    glibc_host = '2.11.3',  # Ubuntu 10.04
    glibc_target = '2.25',  # 2017-02-25, last release for Linux 2.6.32
    linux = '4.9.337',  # 2016-12-11 (4.9.y)
  ),
  'i686-2007': ArchProfile(
    arch = 'i686',
    fpmath = None,
    march = None,
    target = 'i686-linux-gnu',

    enable_kernel = '2.6.16',
    glibc_host = '2.3.6',  # Debian 4
    glibc_target = '2.19',  # 2014-02-07, last release for Linux 2.6.16
    linux = '3.12.74',  # 2013-11-03 (3.12.y)
  ),
}
