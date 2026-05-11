#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>

#include "common.h"

int main(int argc, char *argv[]) {
  char gcc_bin_dir[PATH_MAX];
  resolve_gcc_bin_dir(gcc_bin_dir, sizeof(gcc_bin_dir));
  prepend_to_env_path(gcc_bin_dir);

  change_to_self_dir();
  mkdir_p(DEBUG_BUILD_DIR);

  const char *make_argv[] = {
      "make", "-f", "Makefile.debug", "DIR=" DEBUG_BUILD_DIR, NULL,
  };
  pid_t make_process = spawn(make_argv);
  if (wait_pid(make_process) != 0)
    error_exit("make failed");

  const char *gdbserver_argv[] = {
      "gdbserver",
      "localhost:1234",
      DEBUG_BUILD_DIR "/breakpoint",
      NULL,
  };
  pid_t gdbserver_process = spawn(gdbserver_argv);

  const char *gdb_argv[] = {
      "gdb",
      "--batch",
      "--command=gdb-command.txt",
      NULL,
  };
  pid_t gdb_process = spawn(gdb_argv);

  if (wait_pid(gdbserver_process) != 0)
    error_exit("gdbserver failed");

  if (wait_pid(gdb_process) != 0)
    error_exit("gdb failed");

  printf("[test-make-gdb] done\n");
  return 0;
}
