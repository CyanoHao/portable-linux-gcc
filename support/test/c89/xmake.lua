target("c89/hello")
  add_files("hello.c")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
