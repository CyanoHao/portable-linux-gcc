#pragma once

#include <limits.h>
#include <stdbool.h>
#include <sys/types.h>

void change_to_self_dir(void);
void error_exit(const char *msg);
void mkdir_p(const char *dir);
void prepend_to_env_path(const char *path);
int resolve_gcc_bin_dir(char *dir, int size);
int resolve_gcc_root_dir(char *dir, int size);
int resolve_self_dir(char *dir, int size);
pid_t spawn(const char *const argv[]);
int wait_pid(pid_t pid);
