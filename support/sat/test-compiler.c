#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>

#include "common.h"

int main(int argc, char *argv[]) {
  char gcc_bin_dir[PATH_MAX];
  resolve_gcc_bin_dir(gcc_bin_dir, sizeof(gcc_bin_dir));
  prepend_to_env_path(gcc_bin_dir);

  setenv("XMAKE_ROOT", "y", 1);

  change_to_self_dir();

  const char *xmake_config_argv[] = {
      "xmake",
      "config",
      "--verbose",
      "--plat=linux",
      "--arch=" XMAKE_ARCH,
      "--builddir=build",
      NULL,
  };
  pid_t xmake_config_process = spawn(xmake_config_argv);
  if (wait_pid(xmake_config_process) != 0)
    error_exit("xmake config failed");

  const char *xmake_build_argv[] = {
      "xmake",
      "build",
      "--verbose",
      NULL,
  };
  pid_t xmake_build_process = spawn(xmake_build_argv);
  if (wait_pid(xmake_build_process) != 0)
    error_exit("xmake build failed");

  const char *xmake_test_argv[] = {
      "xmake",
      "test",
      "--verbose",
      NULL,
  };
  pid_t xmake_test_process = spawn(xmake_test_argv);
  if (wait_pid(xmake_test_process) != 0)
    error_exit("xmake test failed");

  printf("[test-compiler] done\n");
  return 0;
}
