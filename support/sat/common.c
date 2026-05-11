#define _GNU_SOURCE
#include "common.h"

#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

void change_to_self_dir(void) {
  char dir[PATH_MAX];
  resolve_self_dir(dir, sizeof(dir));
  if (chdir(dir) != 0)
    error_exit("Failed to change to self directory");
}

void error_exit(const char *msg) {
  fprintf(stderr, "%s\n", msg);
  exit(EXIT_FAILURE);
}

void mkdir_p(const char *dir) {
  char tmp[PATH_MAX];
  snprintf(tmp, sizeof(tmp), "%s", dir);
  for (char *p = tmp + 1; *p; p++) {
    if (*p == '/') {
      *p = '\0';
      mkdir(tmp, 0755);
      *p = '/';
    }
  }
  mkdir(tmp, 0755);
}

void prepend_to_env_path(const char *path) {
  const char *old_path = getenv("PATH");
  char new_path[PATH_MAX * 4];
  if (old_path)
    snprintf(new_path, sizeof(new_path), "%s:%s", path, old_path);
  else
    snprintf(new_path, sizeof(new_path), "%s", path);
  setenv("PATH", new_path, 1);
}

int resolve_gcc_bin_dir(char *dir, int size) {
  int len = resolve_gcc_root_dir(dir, size);
  const char *rel = "/bin";
  int rel_len = 4;
  if (len + rel_len >= size)
    error_exit("Path too long");
  memcpy(dir + len, rel, rel_len + 1);
  return len + rel_len;
}

int resolve_gcc_root_dir(char *dir, int size) {
  const char *rel = "/" GCC_DIR;
  int rel_len = strlen(rel);
  int len = resolve_self_dir(dir, size);
  if (len + rel_len >= size)
    error_exit("Path too long");
  memcpy(dir + len, rel, rel_len + 1);
  return len + rel_len;
}

int resolve_self_dir(char *dir, int size) {
  ssize_t len = readlink("/proc/self/exe", dir, size - 1);
  if (len == -1)
    error_exit("Failed to get executable path");
  dir[len] = '\0';
  while (len > 0 && dir[len - 1] != '/')
    len--;
  dir[len] = '\0';
  return len;
}

pid_t spawn(const char *const argv[]) {
  pid_t pid = fork();
  if (pid == -1)
    error_exit("Failed to fork");
  if (pid == 0) {
    execvp(argv[0], (char *const *)argv);
    perror("execvp");
    _exit(127);
  }
  return pid;
}

int wait_pid(pid_t pid) {
  int status;
  if (waitpid(pid, &status, 0) == -1)
    error_exit("Failed to wait for process");
  if (WIFEXITED(status))
    return WEXITSTATUS(status);
  return 1;
}
