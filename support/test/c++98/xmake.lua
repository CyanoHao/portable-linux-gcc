target("c++98/hello")
  add_files("hello.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
